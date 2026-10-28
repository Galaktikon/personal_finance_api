from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.money import money_string, parse_money
from app.domain.transactions import TransactionKind, validate_transaction


class ImportRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transaction_date: date
    amount: str
    description: str = Field(min_length=1, max_length=2000)
    kind: Literal["income", "expense", "refund"]
    status: Literal["pending", "posted"] = "posted"
    currency: Literal["USD"] = "USD"
    merchant: str | None = Field(default=None, max_length=255)
    external_transaction_id: str | None = Field(default=None, max_length=255)
    category_id: UUID | None = None

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, value: str) -> str:
        return money_string(parse_money(value))

    @field_validator("description", "merchant", "external_transaction_id")
    @classmethod
    def trim_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.split())
        return normalized or None

    @model_validator(mode="after")
    def validate_sign(self) -> "ImportRow":
        validate_transaction(self.amount, TransactionKind(self.kind), self.currency)
        if not self.description:
            raise ValueError("description is required")
        return self


class ImportRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    row_number: int
    status: Literal["created", "updated", "duplicate", "failed"]
    transaction_id: UUID | None
    error_code: str | None
    warning_code: str | None


class ImportPreviewOut(BaseModel):
    total_rows: int
    created_count: int
    updated_count: int
    duplicate_count: int
    failed_count: int
    rows: list[ImportRecordOut]


class ImportJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_format: Literal["csv", "json"]
    status: Literal["processing", "completed", "failed"]
    started_at: datetime
    completed_at: datetime | None
    total_rows: int
    created_count: int
    updated_count: int
    duplicate_count: int
    failed_count: int


class ImportJobDetail(ImportJobOut):
    rows: list[ImportRecordOut]
