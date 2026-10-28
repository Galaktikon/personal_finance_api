from datetime import date
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.v1.common import commit_or_unprocessable
from app.db.session import get_session
from app.domain.transactions import (
    TransactionKind,
    TransactionStatus,
    validate_date_range,
    validate_transaction,
)
from app.models import Transaction, TransactionRevision, TransferLink, UserProfile
from app.repositories.finance import owned_account, owned_transaction, visible_category
from app.schemas.finance import TransactionCreate, TransactionOut, TransactionPatch
from app.services.identity import get_current_user

router = APIRouter(prefix="/transactions", tags=["transactions"])
SessionDep = Annotated[Session, Depends(get_session)]
UserDep = Annotated[UserProfile, Depends(get_current_user)]


def check_account(session: Session, user_id: UUID, account_id: UUID) -> None:
    account = owned_account(session, user_id, account_id)
    if not account.is_active:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Account is inactive")


def check_category(session: Session, user_id: UUID, category_id: UUID | None, kind: str) -> None:
    if category_id is None:
        return
    category = visible_category(session, user_id, category_id)
    expected_kind = "income" if kind == "income" else "expense"
    if not category.is_active or category.kind != expected_kind:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Invalid category for transaction"
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


def as_text(value: object) -> str | None:
    return None if value is None else str(value)


@router.get("", response_model=list[TransactionOut])
def list_transactions(
    session: SessionDep,
    user: UserDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    account_id: UUID | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    status_filter: Annotated[TransactionStatus | None, Query(alias="status")] = None,
    kind: TransactionKind | None = None,
    category_id: UUID | None = None,
    merchant: str | None = None,
) -> list[TransactionOut]:
    if start_date and end_date:
        try:
            validate_date_range(start_date, end_date)
        except ValueError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    query = select(Transaction).where(Transaction.user_id == user.id)
    if account_id is not None:
        query = query.where(Transaction.account_id == account_id)
    if start_date is not None:
        query = query.where(Transaction.transaction_date >= start_date)
    if end_date is not None:
        query = query.where(Transaction.transaction_date < end_date)
    if status_filter is not None:
        query = query.where(Transaction.status == status_filter.value)
    if kind is not None:
        query = query.where(Transaction.kind == kind.value)
    if category_id is not None:
        query = query.where(Transaction.category_id == category_id)
    if merchant is not None:
        query = query.where(Transaction.merchant.ilike(f"%{merchant}%"))
    rows = session.scalars(
        query.order_by(Transaction.transaction_date.desc(), Transaction.id)
        .limit(limit)
        .offset(offset)
    )
    return [TransactionOut.from_entity(row) for row in rows]


@router.post("", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
def create_transaction(
    body: TransactionCreate, session: SessionDep, user: UserDep
) -> TransactionOut:
    check_account(session, user.id, body.account_id)
    check_category(session, user.id, body.category_id, body.kind)
    transaction = Transaction(
        user_id=user.id,
        account_id=body.account_id,
        transaction_date=body.transaction_date,
        amount=Decimal(body.amount),
        currency=body.currency,
        description=body.description,
        merchant=body.merchant,
        kind=body.kind,
        status=body.status,
        category_id=body.category_id,
        category_source="manual" if body.category_id else "uncategorized",
    )
    session.add(transaction)
    commit_or_unprocessable(session)
    return TransactionOut.from_entity(transaction)


@router.get("/{transaction_id}", response_model=TransactionOut)
def get_transaction(transaction_id: UUID, session: SessionDep, user: UserDep) -> TransactionOut:
    return TransactionOut.from_entity(owned_transaction(session, user.id, transaction_id))


@router.patch("/{transaction_id}", response_model=TransactionOut)
def update_transaction(
    transaction_id: UUID, body: TransactionPatch, session: SessionDep, user: UserDep
) -> TransactionOut:
    transaction = owned_transaction(session, user.id, transaction_id)
    changes = body.model_dump(exclude_unset=True)
    if not changes:
        return TransactionOut.from_entity(transaction)
    if is_linked(session, transaction_id):
        raise HTTPException(status.HTTP_409_CONFLICT, "Unlink transfer before editing")
    for key, value in changes.items():
        if value is None and key not in {"merchant", "category_id"}:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"{key} cannot be null")
    next_kind = changes.get("kind", transaction.kind)
    next_amount = changes.get("amount", transaction.amount)
    try:
        validate_transaction(next_amount, TransactionKind(next_kind), transaction.currency)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    if "account_id" in changes:
        check_account(session, user.id, changes["account_id"])
    next_category = changes.get("category_id", transaction.category_id)
    check_category(session, user.id, next_category, next_kind)
    before = {key: as_text(getattr(transaction, key)) for key in changes}
    if "category_id" in changes:
        before["category_source"] = transaction.category_source
        before["categorization_rule_id"] = as_text(transaction.categorization_rule_id)
    for key, value in changes.items():
        setattr(transaction, key, Decimal(value) if key == "amount" else value)
    if "category_id" in changes:
        transaction.category_source = "manual" if transaction.category_id else "uncategorized"
        transaction.categorization_rule_id = None
    after = {key: as_text(getattr(transaction, key)) for key in before}
    revision = TransactionRevision(
        user_id=user.id,
        transaction_id=transaction.id,
        changed_fields=list(before),
        previous_values=before,
        new_values=after,
    )
    session.add(revision)
    commit_or_unprocessable(session)
    return TransactionOut.from_entity(transaction)


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def void_transaction(transaction_id: UUID, session: SessionDep, user: UserDep) -> Response:
    transaction = owned_transaction(session, user.id, transaction_id)
    if is_linked(session, transaction_id):
        raise HTTPException(status.HTTP_409_CONFLICT, "Unlink transfer before voiding")
    if transaction.status != TransactionStatus.VOIDED.value:
        previous_status = transaction.status
        transaction.status = TransactionStatus.VOIDED.value
        session.add(
            TransactionRevision(
                user_id=user.id,
                transaction_id=transaction.id,
                changed_fields=["status"],
                previous_values={"status": previous_status},
                new_values={"status": transaction.status},
            )
        )
        commit_or_unprocessable(session)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
