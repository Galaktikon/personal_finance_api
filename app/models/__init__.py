"""Import all models so Alembic sees complete metadata."""

from app.models.entities import (
    Account,
    CategorizationRule,
    Category,
    ImportJob,
    ImportRecord,
    Transaction,
    TransactionRevision,
    TransferLink,
    UserProfile,
)

__all__ = [
    "Account",
    "CategorizationRule",
    "Category",
    "ImportJob",
    "ImportRecord",
    "Transaction",
    "TransactionRevision",
    "TransferLink",
    "UserProfile",
]
