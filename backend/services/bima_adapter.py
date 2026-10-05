"""Strict adapter that turns raw BIMA directory payloads into local records.

The upstream BIMA contract is not verifiable from this repository, so the
adapter accepts the documented aliases below and rejects anything else with a
502 *before* any database write happens. Adjust the alias tuples here when the
real payload is confirmed; never loosen the router.
"""

from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from domain.enums import UserRole
from models.project import Project
from models.user import User
from services import bima_client

PROJECT_ID_FIELDS = ("bima_project_id", "id")
PROJECT_NAME_FIELDS = ("name", "project_name")
PROJECT_CODE_FIELDS = ("code", "project_code")
PROJECT_PLANT_FIELDS = ("plant_area", "plant")
PROJECT_MEMBER_FIELDS = ("member_ids", "members")
PROJECT_PIC_FIELDS = ("pic_id", "pic")

USER_ID_FIELDS = ("id", "bima_id")
USER_NAME_FIELDS = ("full_name", "name")

INVALID_USER_RECORD = "BIMA user directory contains an invalid record."
DUPLICATE_USER_IDS = "BIMA user directory contains duplicate user IDs."
INVALID_PROJECT_RECORD = "BIMA project directory contains an invalid record."
DUPLICATE_PROJECT_IDS = "BIMA project directory contains duplicate project IDs."
MISSING_MEMBERSHIP = "BIMA project membership is missing."
UNKNOWN_MEMBER = "BIMA project references an unknown user."


@dataclass(frozen=True)
class BimaUserRecord:
    """Normalized BIMA directory user limited to local identity fields."""

    bima_id: int
    email: str
    full_name: str
    role: UserRole
    department: str | None
    position: str | None


@dataclass(frozen=True)
class BimaProjectRecord:
    """Normalized BIMA project with its resolved membership IDs."""

    bima_project_id: int
    name: str
    code: str | None
    description: str | None
    plant_area: str | None
    status: str
    member_bima_ids: tuple[int, ...]


@dataclass(frozen=True)
class BimaMasterData:
    """Validated master data ready for a single transactional sync."""

    projects: tuple[BimaProjectRecord, ...]
    users: tuple[BimaUserRecord, ...]


def _bad_gateway(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail)


def _positive_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return None
    return value


def _first_text(row: dict[str, Any], fields: tuple[str, ...]) -> str | None:
    for field in fields:
        value = row.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _first_present(row: dict[str, Any], fields: tuple[str, ...]) -> tuple[str, Any] | None:
    for field in fields:
        if field in row:
            return field, row[field]
    return None


class BimaMasterDataAdapter:
    """Validate and normalize BIMA project and user directories."""

    def adapt(self, projects: list[dict[str, Any]], users: list[dict[str, Any]]) -> BimaMasterData:
        """Return validated master data, raising 502 on any contract violation."""
        user_records = self._adapt_users(users)
        project_records = self._adapt_projects(projects, user_records)
        referenced = {bima_id for record in project_records for bima_id in record.member_bima_ids}
        return BimaMasterData(
            projects=tuple(project_records),
            users=tuple(record for record in user_records if record.bima_id in referenced),
        )

    def _adapt_users(self, users: list[dict[str, Any]]) -> list[BimaUserRecord]:
        records: list[BimaUserRecord] = []
        seen: set[int] = set()
        for row in users:
            bima_id = _positive_int(_first_value(row, USER_ID_FIELDS))
            if bima_id is None:
                raise _bad_gateway(INVALID_USER_RECORD)
            email = row.get("email")
            if not isinstance(email, str) or not email.strip():
                raise _bad_gateway(INVALID_USER_RECORD)
            if _first_text(row, USER_NAME_FIELDS) is None:
                raise _bad_gateway(INVALID_USER_RECORD)
            if bima_id in seen:
                raise _bad_gateway(DUPLICATE_USER_IDS)
            seen.add(bima_id)
            profile = bima_client._profile({"data": {"valid": True, "user": row}})
            records.append(
                BimaUserRecord(
                    bima_id=bima_id,
                    email=str(profile["email"]),
                    full_name=str(profile["full_name"]),
                    role=profile["role"],
                    department=profile.get("department"),
                    position=profile.get("position"),
                )
            )
        records.sort(key=lambda record: record.bima_id)
        return records

    def _adapt_projects(
        self, projects: list[dict[str, Any]], users: list[BimaUserRecord]
    ) -> list[BimaProjectRecord]:
        known_user_ids = {record.bima_id for record in users}
        records: list[BimaProjectRecord] = []
        seen: set[int] = set()
        for row in projects:
            bima_project_id = _positive_int(_first_value(row, PROJECT_ID_FIELDS))
            name = _first_text(row, PROJECT_NAME_FIELDS)
            if bima_project_id is None or name is None:
                raise _bad_gateway(INVALID_PROJECT_RECORD)
            if bima_project_id in seen:
                raise _bad_gateway(DUPLICATE_PROJECT_IDS)
            seen.add(bima_project_id)

            member_fields = [field for field in PROJECT_MEMBER_FIELDS if field in row]
            if not member_fields:
                raise _bad_gateway(MISSING_MEMBERSHIP)
            if len(member_fields) != 1 or not isinstance(row[member_fields[0]], list):
                raise _bad_gateway(INVALID_PROJECT_RECORD)
            member_values = row[member_fields[0]]
            member_ids: set[int] = set()
            for value in member_values:
                member_id = _positive_int(value)
                if member_id is None:
                    raise _bad_gateway(INVALID_PROJECT_RECORD)
                member_ids.add(member_id)

            pic_field = _first_present(row, PROJECT_PIC_FIELDS)
            if pic_field is not None and pic_field[1] is not None:
                pic_id = _positive_int(pic_field[1])
                if pic_id is None:
                    raise _bad_gateway(INVALID_PROJECT_RECORD)
                member_ids.add(pic_id)

            if not member_ids <= known_user_ids:
                raise _bad_gateway(UNKNOWN_MEMBER)

            if len([field for field in PROJECT_PIC_FIELDS if field in row]) > 1:
                raise _bad_gateway(INVALID_PROJECT_RECORD)
            code = _first_text(row, PROJECT_CODE_FIELDS)
            plant_area = _first_text(row, PROJECT_PLANT_FIELDS)
            description = row.get("description")
            records.append(
                BimaProjectRecord(
                    bima_project_id=bima_project_id,
                    name=name,
                    code=code,
                    description=description if isinstance(description, str) else None,
                    plant_area=plant_area,
                    status=str(row.get("status") or "ACTIVE").upper(),
                    member_bima_ids=tuple(sorted(member_ids)),
                )
            )
        records.sort(key=lambda record: record.bima_project_id)
        return records


def _first_value(row: dict[str, Any], fields: tuple[str, ...]) -> Any:
    for field in fields:
        value = row.get(field)
        if value is not None:
            return value
    return None


async def sync_user_bima_projects(
    db: AsyncSession,
    current_user: User,
    bima_token: str,
) -> dict[str, int]:
    """Provision projects visible to this user in BIMA into their PRISM workspace.

    BIMA's authenticated project endpoint is already scoped to the caller's
    accessible projects. The caller is therefore added to each returned
    project's local membership without requiring a second user-directory call.
    """
    remote_projects = await bima_client.fetch_bima_projects(bima_token)
    try:
        result = await db.execute(select(Project).options(selectinload(Project.members)))
    except SQLAlchemyError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="BIMA projects could not be loaded into the PRISM workspace.",
        ) from exc
    local_projects = list(result.scalars().all())
    by_bima_id = {
        project.bima_project_id: project
        for project in local_projects
        if project.bima_project_id is not None
    }
    by_name: dict[str, list[Project]] = {}
    for project in local_projects:
        by_name.setdefault(project.name.casefold(), []).append(project)

    created = 0
    updated = 0
    try:
        for remote in remote_projects:
            name = _first_text(remote, PROJECT_NAME_FIELDS)
            if name is None:
                raise _bad_gateway(INVALID_PROJECT_RECORD)
            raw_id = _first_value(remote, PROJECT_ID_FIELDS)
            bima_project_id = _positive_int(raw_id)
            if bima_project_id is None and isinstance(raw_id, str) and raw_id.isdigit():
                parsed_id = int(raw_id)
                bima_project_id = parsed_id if parsed_id > 0 else None

            project = by_bima_id.get(bima_project_id) if bima_project_id is not None else None
            if project is None:
                # Adopt an existing locally-created folder by name when it has
                # no BIMA identity yet; never overwrite a different BIMA ID.
                project = next(
                    (
                        candidate
                        for candidate in by_name.get(name.casefold(), [])
                        if candidate.bima_project_id in {None, bima_project_id}
                    ),
                    None,
                )

            if project is None:
                project = Project(
                    name=name,
                    code=_first_text(remote, PROJECT_CODE_FIELDS),
                    status="ACTIVE",
                    created_by_id=current_user.id,
                    bima_project_id=bima_project_id,
                    members=[current_user],
                )
                db.add(project)
                local_projects.append(project)
                by_name.setdefault(name.casefold(), []).append(project)
                if bima_project_id is not None:
                    by_bima_id[bima_project_id] = project
                created += 1
                continue

            updated += 1
            old_name = project.name.casefold()
            project.name = name
            project.code = _first_text(remote, PROJECT_CODE_FIELDS) or project.code
            if project.bima_project_id is None and bima_project_id is not None:
                project.bima_project_id = bima_project_id
                by_bima_id[bima_project_id] = project
            if all(member.id != current_user.id for member in project.members):
                project.members.append(current_user)
            if old_name != name.casefold():
                by_name.setdefault(name.casefold(), []).append(project)

        await db.commit()
    except HTTPException:
        await db.rollback()
        raise
    except SQLAlchemyError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="BIMA project sync could not be applied; no changes were saved.",
        ) from exc

    return {"synced": len(remote_projects), "created": created, "updated": updated}
