"""Best-effort Redis progress notifications with a database fallback."""

import asyncio
import logging
import time
from contextlib import suppress
from typing import Any, cast
from uuid import UUID

from redis import Redis
from redis.asyncio import Redis as AsyncRedis
from redis.asyncio.client import PubSub
from redis.exceptions import RedisError

from core.config import settings

logger = logging.getLogger(__name__)

_CHANNEL_PREFIX = "prism:document-progress:"
_PUBLISH_FAILURE_COOLDOWN_SECONDS = 5.0
_publisher: Redis | None = None
_publisher_disabled_until = 0.0


def document_progress_channel(document_id: UUID | str) -> str:
    return f"{_CHANNEL_PREFIX}{document_id}"


async def publish_document_progress(document_id: UUID | str) -> None:
    """Publish off-loop through Redis' thread-safe synchronous pool."""
    global _publisher, _publisher_disabled_until
    now = time.monotonic()
    if now < _publisher_disabled_until:
        return
    try:
        if _publisher is None:
            _publisher = Redis.from_url(
                settings.REDIS_URL,
                socket_connect_timeout=0.25,
                socket_timeout=0.25,
                decode_responses=True,
            )
        await asyncio.to_thread(
            _publisher.publish, document_progress_channel(document_id), "changed"
        )
    except (RedisError, OSError) as exc:
        logger.debug("Redis progress notification unavailable: %s", exc)
        _publisher_disabled_until = now + _PUBLISH_FAILURE_COOLDOWN_SECONDS
        if _publisher is not None:
            with suppress(RedisError, OSError):
                await asyncio.to_thread(_publisher.close)
        _publisher = None


async def open_document_progress_subscription(document_id: UUID | str) -> tuple[AsyncRedis, PubSub]:
    """Open one Redis pub/sub subscription for an SSE document stream."""
    client: AsyncRedis = AsyncRedis.from_url(
        settings.REDIS_URL,
        socket_connect_timeout=0.5,
        socket_timeout=2.5,
        decode_responses=True,
    )
    pubsub = client.pubsub()
    try:
        await pubsub.subscribe(document_progress_channel(document_id))
    except (RedisError, OSError):
        with suppress(Exception):
            await cast(Any, pubsub).aclose()
        with suppress(RedisError, OSError):
            await client.aclose()
        raise
    return client, pubsub
