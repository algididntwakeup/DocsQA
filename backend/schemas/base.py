"""Base schema configuration for strict API contracts."""

from pydantic import BaseModel, ConfigDict


class ApiModel(BaseModel):
    """Reject unknown fields and support validation from ORM attributes."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)
