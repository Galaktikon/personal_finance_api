import csv
import io
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from typing import Any, Literal
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import (
    Account,
    Category,
    ImportJob,
    ImportRecord,
    Transaction,
    TransactionRevision,
    TransferLink,
)
from app.schemas.imports import ImportPreviewOut, ImportRecordOut, ImportRow
from app.services.categorization import normalize_text, select_category

SourceFormat = Literal["csv", "json"]
ROW_FIELDS = frozenset(ImportRow.model_fields)
REQUIRED_FIELDS = frozenset({"transaction_date", "amount", "description", "kind"})


class ImportInputError(ValueError):
    """Invalid file shape or encoding; safe to show as a generic input error."""


@dataclass
class RowResult:
    row_number: int
    status: str
    transaction_id: UUID | None = None
    error_code: str | None = None
    warning_code: str | None = None
    fingerprint: str | None = None

    def public(self) -> ImportRecordOut:
        return ImportRecordOut(
            row_number=self.row_number,
            status=self.status,
            transaction_id=self.transaction_id,
            error_code=self.error_code,
            warning_code=self.warning_code,
        )


def request_digest(
    content: bytes, account_id: UUID, source_identifier: str, source_format: SourceFormat
) -> str:
    metadata = json.dumps(
        {
            "account_id": str(account_id),
            "source_identifier": source_identifier,
            "format": source_format,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return sha256(metadata + b"\0" + content).hexdigest()


def parse_file(content: bytes, source_format: SourceFormat, max_rows: int) -> list[dict[str, Any]]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ImportInputError("File must be UTF-8") from exc
    if source_format == "json":
        try:
            rows = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ImportInputError("Invalid JSON file") from exc
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise ImportInputError("JSON must be an array of transaction objects")
    else:
        try:
            reader = csv.DictReader(io.StringIO(text, newline=""), strict=True)
            headers = reader.fieldnames
            if (
                not headers
                or len(headers) != len(set(headers))
                or not REQUIRED_FIELDS <= set(headers)
            ):
                raise ImportInputError("CSV headers are missing, duplicated, or incomplete")
            if not set(headers) <= ROW_FIELDS:
                raise ImportInputError("CSV has unsupported columns")
            rows = []
            for raw in reader:
                if None in raw:
                    raise ImportInputError("CSV row has too many columns")
                rows.append({key: value for key, value in raw.items() if value != ""})
                if len(rows) > max_rows:
                    raise ImportInputError("File exceeds row limit")
        except csv.Error as exc:
            raise ImportInputError("Invalid CSV file") from exc
    if not rows:
        raise ImportInputError("File has no rows")
    if len(rows) > max_rows:
        raise ImportInputError("File exceeds row limit")
    return rows


def row_fingerprint(row: ImportRow, account_id: UUID, source_identifier: str) -> str:
    canonical = {
        "account_id": str(account_id),
        "source_identifier": source_identifier,
        "date": row.transaction_date.isoformat(),
        "amount": row.amount,
        "kind": row.kind,
        "status": row.status,
        "description": normalize_text(row.description),
        "merchant": normalize_text(row.merchant),
    }
    return sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate_category(session: Session, user_id: UUID, row: ImportRow) -> bool:
    if row.category_id is None:
        return True
    category = session.scalar(
        select(Category).where(
            Category.id == row.category_id,
            (Category.user_id == user_id) | (Category.user_id.is_(None)),
        )
    )
    expected = "income" if row.kind == "income" else "expense"
    return category is not None and category.is_active and category.kind == expected


def existing_transaction(
    session: Session,
    user_id: UUID,
    account_id: UUID,
    source_identifier: str,
    external_id: str,
) -> Transaction | None:
    return session.scalar(
        select(Transaction).where(
            Transaction.user_id == user_id,
            Transaction.account_id == account_id,
            Transaction.source_identifier == source_identifier,
            Transaction.external_transaction_id == external_id,
        )
    )


def is_linked(session: Session, transaction_id: UUID) -> bool:
    return (
        session.scalar(
            select(TransferLink.id).where(
                or_(
                    TransferLink.source_transaction_id == transaction_id,
                    TransferLink.destination_transaction_id == transaction_id,
                )
            )
        )
        is not None
    )


def categorize(
    session: Session, user_id: UUID, row: ImportRow
) -> tuple[UUID | None, UUID | None, str]:
    if row.category_id is not None:
        return row.category_id, None, "manual"
    return select_category(session, user_id, row.kind, row.description, row.merchant)


def snapshot(transaction: Transaction) -> dict[str, str | None]:
    fields = (
        "transaction_date",
        "amount",
        "description",
        "merchant",
        "status",
        "category_id",
        "category_source",
        "categorization_rule_id",
    )
    return {
        field: None if (value := getattr(transaction, field)) is None else str(value)
        for field in fields
    }


def process_rows(
    session: Session,
    user_id: UUID,
    account: Account,
    source_identifier: str,
    raw_rows: list[dict[str, Any]],
    job: ImportJob | None = None,
) -> ImportPreviewOut:
    results: list[RowResult] = []
    preview_ids: dict[str, tuple[str, str, UUID | None, bool]] = {}
    seen_fingerprints: set[str] = set()
    for row_number, raw in enumerate(raw_rows, 1):
        try:
            row = ImportRow.model_validate(raw)
        except ValidationError:
            result = RowResult(row_number, "failed", error_code="invalid_row")
            results.append(result)
            continue
        if not validate_category(session, user_id, row):
            results.append(RowResult(row_number, "failed", error_code="invalid_category"))
            continue
        fingerprint = row_fingerprint(row, account.id, source_identifier)
        warning: str | None = None
        if row.external_transaction_id is None:
            previous_fingerprint = session.scalar(
                select(ImportRecord.id)
                .where(
                    ImportRecord.user_id == user_id,
                    ImportRecord.fingerprint == fingerprint,
                    ImportRecord.status.in_(("created", "updated")),
                )
                .limit(1)
            )
            if fingerprint in seen_fingerprints or previous_fingerprint is not None:
                warning = "possible_duplicate"
            seen_fingerprints.add(fingerprint)

        existing: Transaction | None = None
        if row.external_transaction_id is not None:
            existing = existing_transaction(
                session, user_id, account.id, source_identifier, row.external_transaction_id
            )
        if job is None and row.external_transaction_id is not None:
            current = preview_ids.get(row.external_transaction_id)
            if current is not None:
                prior_status, prior_kind, transaction_id, linked = current
                can_update = (
                    prior_status == "pending"
                    and row.status == "posted"
                    and prior_kind == row.kind
                    and not linked
                )
                results.append(
                    RowResult(
                        row_number,
                        "updated" if can_update else "duplicate",
                        transaction_id,
                        fingerprint=fingerprint,
                    )
                )
                if can_update:
                    preview_ids[row.external_transaction_id] = (
                        "posted",
                        prior_kind,
                        transaction_id,
                        linked,
                    )
                continue
            linked = is_linked(session, existing.id) if existing is not None else False
            reconciled = (
                existing is not None
                and existing.status == "pending"
                and row.status == "posted"
                and existing.kind == row.kind
                and not linked
            )
            preview_ids[row.external_transaction_id] = (
                "posted" if reconciled else existing.status if existing is not None else row.status,
                existing.kind if existing is not None else row.kind,
                existing.id if existing is not None else None,
                linked,
            )

        if existing is not None:
            if (
                existing.status == "pending"
                and row.status == "posted"
                and existing.kind == row.kind
                and not is_linked(session, existing.id)
            ):
                result = RowResult(row_number, "updated", existing.id, fingerprint=fingerprint)
                if job is not None:
                    before = snapshot(existing)
                    existing.transaction_date = row.transaction_date
                    existing.amount = Decimal(row.amount)
                    existing.description = row.description
                    existing.normalized_description = normalize_text(row.description)
                    existing.merchant = row.merchant
                    existing.normalized_merchant = normalize_text(row.merchant) or None
                    existing.status = "posted"
                    if existing.category_source != "manual":
                        category_id, rule_id, category_source = categorize(session, user_id, row)
                        existing.category_id = category_id
                        existing.categorization_rule_id = rule_id
                        existing.category_source = category_source
                    session.flush()
                    session.add(
                        TransactionRevision(
                            user_id=user_id,
                            transaction_id=existing.id,
                            changed_fields=list(before),
                            previous_values=before,
                            new_values=snapshot(existing),
                        )
                    )
            else:
                result = RowResult(row_number, "duplicate", existing.id, fingerprint=fingerprint)
        else:
            result = RowResult(row_number, "created", warning_code=warning, fingerprint=fingerprint)
            if job is not None:
                category_id, rule_id, category_source = categorize(session, user_id, row)
                transaction = Transaction(
                    user_id=user_id,
                    account_id=account.id,
                    transaction_date=row.transaction_date,
                    amount=Decimal(row.amount),
                    currency=row.currency,
                    description=row.description,
                    normalized_description=normalize_text(row.description),
                    merchant=row.merchant,
                    normalized_merchant=normalize_text(row.merchant) or None,
                    kind=row.kind,
                    status=row.status,
                    category_id=category_id,
                    categorization_rule_id=rule_id,
                    category_source=category_source,
                    external_transaction_id=row.external_transaction_id,
                    source_identifier=source_identifier,
                )
                session.add(transaction)
                session.flush()
                result.transaction_id = transaction.id
        results.append(result)

    counts = {
        name: sum(result.status == name for result in results)
        for name in ("created", "updated", "duplicate", "failed")
    }
    if job is not None:
        job.status = "completed"
        job.completed_at = datetime.now(UTC)
        job.total_rows = len(raw_rows)
        job.created_count = counts["created"]
        job.updated_count = counts["updated"]
        job.duplicate_count = counts["duplicate"]
        job.failed_count = counts["failed"]
        for result in results:
            session.add(
                ImportRecord(
                    user_id=user_id,
                    import_job_id=job.id,
                    row_number=result.row_number,
                    status=result.status,
                    transaction_id=result.transaction_id,
                    error_code=result.error_code,
                    warning_code=result.warning_code,
                    fingerprint=result.fingerprint,
                )
            )
    return ImportPreviewOut(
        total_rows=len(raw_rows),
        created_count=counts["created"],
        updated_count=counts["updated"],
        duplicate_count=counts["duplicate"],
        failed_count=counts["failed"],
        rows=[result.public() for result in results],
    )
