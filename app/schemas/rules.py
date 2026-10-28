from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictBody(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RuleCreate(StrictBody):
    name: str = Field(min_length=1, max_length=120)
    priority: int = Field(default=100, ge=0, le=10000)
    condition_type: Literal["contains", "equals"]
    condition_value: str = Field(min_length=1, max_length=255)
    category_id: UUID
    is_active: bool = True

    @field_validator("name", "condition_value")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("Value cannot be blank")
        return normalized


class RulePatch(StrictBody):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    priority: int | None = Field(default=None, ge=0, le=10000)
    condition_type: Literal["contains", "equals"] | None = None
    condition_value: str | None = Field(default=None, min_length=1, max_length=255)
    category_id: UUID | None = None
    is_active: bool | None = None

    @field_validator("name", "condition_value")
    @classmethod
    def normalize_required_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("Value cannot be blank")
        return normalized


class RuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    priority: int
    condition_type: str
    condition_value: str
    category_id: UUID
    is_active: bool
    is_system: bool = False
    created_at: datetime
    updated_at: datetime
