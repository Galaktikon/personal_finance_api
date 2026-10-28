from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, validates

from app.db.base import Base
from app.domain.money import parse_money, require_usd
from app.domain.transactions import TransactionKind, validate_transaction


class Timestamped:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class UserProfile(Timestamped, Base):
    __tablename__ = "user_profiles"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    auth_subject_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)


class Account(Timestamped, Base):
    __tablename__ = "accounts"
    __table_args__ = (
        UniqueConstraint("user_id", "id", name="uq_accounts_owner_id"),
        CheckConstraint(
            "type IN ('checking', 'savings', 'cash', 'credit_card', 'other')",
            name="ck_accounts_type",
        ),
        CheckConstraint("currency = 'USD'", name="ck_accounts_currency_usd"),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("user_profiles.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    @validates("currency")
    def validate_currency(self, _: str, value: str) -> str:
        return require_usd(value)


class Category(Timestamped, Base):
    __tablename__ = "categories"
    __table_args__ = (
        CheckConstraint("kind IN ('income', 'expense')", name="ck_categories_kind"),
        CheckConstraint("id <> parent_category_id", name="ck_categories_not_self_parent"),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("user_profiles.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    parent_category_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("categories.id"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class CategorizationRule(Timestamped, Base):
    __tablename__ = "categorization_rules"
    __table_args__ = (
        CheckConstraint("condition_type IN ('contains', 'equals')", name="ck_rules_condition_type"),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("user_profiles.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    condition_type: Mapped[str] = mapped_column(String(20), nullable=False)
    condition_value: Mapped[str] = mapped_column(String(255), nullable=False)
    category_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("categories.id"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Transaction(Timestamped, Base):
    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint("user_id", "id", name="uq_transactions_owner_id"),
        ForeignKeyConstraint(
            ["user_id", "account_id"],
            ["accounts.user_id", "accounts.id"],
            name="fk_transactions_owned_account",
        ),
        CheckConstraint("currency = 'USD'", name="ck_transactions_currency_usd"),
        CheckConstraint(
            "kind IN ('income', 'expense', 'refund', 'transfer_out', 'transfer_in')",
            name="ck_transactions_kind",
        ),
        CheckConstraint("status IN ('pending', 'posted', 'voided')", name="ck_transactions_status"),
        CheckConstraint(
            "(kind IN ('income', 'refund', 'transfer_in') AND amount > 0) OR "
            "(kind IN ('expense', 'transfer_out') AND amount < 0)",
            name="ck_transactions_kind_amount_sign",
        ),
        CheckConstraint(
            "category_source IN ('uncategorized', 'manual', 'user_rule', 'system_rule')",
            name="ck_transactions_category_source",
        ),
        CheckConstraint(
            "(category_id IS NULL AND category_source = 'uncategorized' "
            "AND categorization_rule_id IS NULL) OR "
            "(category_id IS NOT NULL AND category_source <> 'uncategorized')",
            name="ck_transactions_category_presence",
        ),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("user_profiles.id"), nullable=False
    )
    account_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(19, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    description: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_description: Mapped[str | None] = mapped_column(Text)
    merchant: Mapped[str | None] = mapped_column(String(255))
    normalized_merchant: Mapped[str | None] = mapped_column(String(255))
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="posted")
    category_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("categories.id")
    )
    category_source: Mapped[str] = mapped_column(
        String(20), nullable=False, default="uncategorized"
    )
    categorization_rule_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("categorization_rules.id")
    )
    external_transaction_id: Mapped[str | None] = mapped_column(String(255))
    source_identifier: Mapped[str | None] = mapped_column(String(255))

    @validates("amount")
    def validate_amount(self, _: str, value: Decimal) -> Decimal:
        return parse_money(value)

    @validates("currency")
    def validate_currency(self, _: str, value: str) -> str:
        return require_usd(value)

    def validate_semantics(self) -> None:
        validate_transaction(self.amount, TransactionKind(self.kind), self.currency)


class ImportJob(Timestamped, Base):
    __tablename__ = "import_jobs"
    __table_args__ = (
        UniqueConstraint("user_id", "id", name="uq_import_jobs_owner_id"),
        CheckConstraint("source_format IN ('csv', 'json')", name="ck_import_jobs_format"),
        CheckConstraint(
            "status IN ('processing', 'completed', 'failed')", name="ck_import_jobs_status"
        ),
        CheckConstraint(
            "total_rows >= 0 AND created_count >= 0 AND duplicate_count >= 0 AND failed_count >= 0",
            name="ck_import_jobs_nonnegative_counts",
        ),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("user_profiles.id"), nullable=False
    )
    source_format: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    content_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_summary: Mapped[str | None] = mapped_column(Text)


class ImportRecord(Base):
    __tablename__ = "import_records"
    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id", "import_job_id"],
            ["import_jobs.user_id", "import_jobs.id"],
            name="fk_import_records_owned_job",
        ),
        ForeignKeyConstraint(
            ["user_id", "transaction_id"],
            ["transactions.user_id", "transactions.id"],
            name="fk_import_records_owned_transaction",
        ),
        UniqueConstraint("import_job_id", "row_number", name="uq_import_records_job_row"),
        CheckConstraint("row_number > 0", name="ck_import_records_row_positive"),
        CheckConstraint(
            "status IN ('created', 'duplicate', 'failed')", name="ck_import_records_status"
        ),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    import_job_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    transaction_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True))
    error_code: Mapped[str | None] = mapped_column(String(80))
    fingerprint: Mapped[str | None] = mapped_column(String(64))


class TransferLink(Timestamped, Base):
    __tablename__ = "transfer_links"
    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id", "source_transaction_id"],
            ["transactions.user_id", "transactions.id"],
            name="fk_transfer_links_owned_source",
        ),
        ForeignKeyConstraint(
            ["user_id", "destination_transaction_id"],
            ["transactions.user_id", "transactions.id"],
            name="fk_transfer_links_owned_destination",
        ),
        UniqueConstraint("source_transaction_id", name="uq_transfer_links_source"),
        UniqueConstraint("destination_transaction_id", name="uq_transfer_links_destination"),
        CheckConstraint(
            "source_transaction_id <> destination_transaction_id",
            name="ck_transfer_links_distinct_transactions",
        ),
        CheckConstraint("status IN ('matched', 'reversed')", name="ck_transfer_links_status"),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("user_profiles.id"), nullable=False
    )
    source_transaction_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    destination_transaction_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="matched")


class TransactionRevision(Base):
    __tablename__ = "transaction_revisions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id", "transaction_id"],
            ["transactions.user_id", "transactions.id"],
            name="fk_transaction_revisions_owned_transaction",
        ),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    transaction_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    changed_fields: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    previous_values: Mapped[dict[str, str | None]] = mapped_column(JSON, nullable=False)
    new_values: Mapped[dict[str, str | None]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
