"""Import idempotency, reconciliation counts, and transfer restoration.

Revision ID: 1a4b_phase4
Revises: 877f154026dd
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "1a4b_phase4"
down_revision: str | None = "877f154026dd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("import_jobs", sa.Column("idempotency_key", sa.String(128)))
    op.add_column(
        "import_jobs", sa.Column("updated_count", sa.Integer(), server_default="0", nullable=False)
    )
    op.create_unique_constraint(
        "uq_import_jobs_idempotency_key", "import_jobs", ["user_id", "idempotency_key"]
    )
    op.drop_constraint("ck_import_jobs_nonnegative_counts", "import_jobs", type_="check")
    op.create_check_constraint(
        "ck_import_jobs_nonnegative_counts",
        "import_jobs",
        "total_rows >= 0 AND created_count >= 0 AND updated_count >= 0 "
        "AND duplicate_count >= 0 AND failed_count >= 0",
    )
    op.drop_constraint("ck_import_records_status", "import_records", type_="check")
    op.create_check_constraint(
        "ck_import_records_status",
        "import_records",
        "status IN ('created', 'updated', 'duplicate', 'failed')",
    )
    op.add_column("import_records", sa.Column("warning_code", sa.String(80)))
    op.create_index(
        "uq_transactions_import_external_id",
        "transactions",
        ["user_id", "account_id", "source_identifier", "external_transaction_id"],
        unique=True,
        postgresql_where=sa.text("external_transaction_id IS NOT NULL"),
    )
    op.add_column("transfer_links", sa.Column("source_previous", sa.JSON()))
    op.add_column("transfer_links", sa.Column("destination_previous", sa.JSON()))


def downgrade() -> None:
    op.drop_column("transfer_links", "destination_previous")
    op.drop_column("transfer_links", "source_previous")
    op.drop_index("uq_transactions_import_external_id", table_name="transactions")
    op.drop_column("import_records", "warning_code")
    op.drop_constraint("ck_import_records_status", "import_records", type_="check")
    op.create_check_constraint(
        "ck_import_records_status", "import_records", "status IN ('created', 'duplicate', 'failed')"
    )
    op.drop_constraint("ck_import_jobs_nonnegative_counts", "import_jobs", type_="check")
    op.create_check_constraint(
        "ck_import_jobs_nonnegative_counts",
        "import_jobs",
        "total_rows >= 0 AND created_count >= 0 AND duplicate_count >= 0 AND failed_count >= 0",
    )
    op.drop_constraint("uq_import_jobs_idempotency_key", "import_jobs", type_="unique")
    op.drop_column("import_jobs", "updated_count")
    op.drop_column("import_jobs", "idempotency_key")
