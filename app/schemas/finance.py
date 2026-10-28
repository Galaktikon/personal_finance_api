from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.money import money_string, parse_money
from app.domain.transactions import TransactionKind, validate_transaction
from app.models import Transaction

AccountType = Literal["checking", "savings", "cash", "credit_card", "other"]
CategoryKind = Literal["income", "expense"]
TransactionType = Literal["income", "expense", "refund"]
TransactionState = Literal["pending", "posted", "voided"]


class StrictBody(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AccountCreate(StrictBody):
    name: str = Field(min_length=1, max_length=120)
    type: AccountType
    currency: Literal["USD"] = "USD"


class AccountPatch(StrictBody):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    is_active: bool | None = None


class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    type: AccountType
    currency: Literal["USD"]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CategoryCreate(StrictBody):
    name: str = Field(min_length=1, max_length=120)
    kind: CategoryKind
    parent_category_id: UUID | None = None


class CategoryPatch(StrictBody):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    parent_category_id: UUID | None = None
    is_active: bool | None = None


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    kind: CategoryKind
    parent_category_id: UUID | None
    is_active: bool
    is_system: bool = False
    created_at: datetime
    updated_at: datetime


class TransactionCreate(StrictBody):
    account_id: UUID
    transaction_date: date
    amount: str
    currency: Literal["USD"] = "USD"
    description: str = Field(min_length=1, max_length=2000)
    merchant: str | None = Field(default=None, max_length=255)
    kind: TransactionType
    status: Literal["pending", "posted"] = "posted"
    category_id: UUID | None = None

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, value: str) -> str:
        return money_string(parse_money(value))

    @model_validator(mode="after")
    def validate_sign(self) -> "TransactionCreate":
        validate_transaction(self.amount, TransactionKind(self.kind), self.currency)
        return self


class TransactionPatch(StrictBody):
    account_id: UUID | None = None
    transaction_date: date | None = None
    amount: str | None = None
    description: str | None = Field(default=None, min_length=1, max_length=2000)
    merchant: str | None = Field(default=None, max_length=255)
    kind: TransactionType | None = None
    status: TransactionState | None = None
    category_id: UUID | None = None

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, value: str | None) -> str | None:
        return money_string(parse_money(value)) if value is not None else None


class TransactionOut(BaseModel):
    id: UUID
    account_id: UUID
    transaction_date: date
    amount: str
    currency: Literal["USD"]
    description: str
    merchant: str | None
    kind: str
    status: TransactionState
    category_id: UUID | None
    category_source: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, entity: Transaction) -> "TransactionOut":
        return cls(
            id=entity.id,
            account_id=entity.account_id,
            transaction_date=entity.transaction_date,
            amount=money_string(Decimal(entity.amount)),
            currency="USD",
            description=entity.description,
            merchant=entity.merchant,
            kind=entity.kind,
            status=entity.status,
            category_id=entity.category_id,
            category_source=entity.category_source,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
