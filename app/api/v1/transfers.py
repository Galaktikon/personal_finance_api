from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.v1.common import commit_or_unprocessable
from app.db.session import get_session
from app.domain.transactions import TransactionKind
from app.domain.transfers import validate_transfer_pair
from app.models import Transaction, TransactionRevision, TransferLink, UserProfile
from app.repositories.finance import owned_transaction
from app.schemas.transfers import TransferMatch, TransferOut
from app.services.identity import get_current_user

router = APIRouter(prefix="/transfers", tags=["transfers"])
SessionDep = Annotated[Session, Depends(get_session)]
UserDep = Annotated[UserProfile, Depends(get_current_user)]

RESTORED_FIELDS = ("kind", "category_id", "category_source", "categorization_rule_id")


def snapshot(transaction: Transaction) -> dict[str, str | None]:
    return {
        field: None if (value := getattr(transaction, field)) is None else str(value)
        for field in RESTORED_FIELDS
    }


def revision(
    user_id: UUID,
    transaction: Transaction,
    previous: dict[str, str | None],
) -> TransactionRevision:
    return TransactionRevision(
        user_id=user_id,
        transaction_id=transaction.id,
        changed_fields=list(RESTORED_FIELDS),
        previous_values=previous,
        new_values=snapshot(transaction),
    )


def already_linked(session: Session, transaction_id: UUID) -> bool:
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


@router.post("/match", response_model=TransferOut, status_code=status.HTTP_201_CREATED)
def match_transfer(body: TransferMatch, session: SessionDep, user: UserDep) -> TransferLink:
    source = owned_transaction(session, user.id, body.source_transaction_id)
    destination = owned_transaction(session, user.id, body.destination_transaction_id)
    if already_linked(session, source.id) or already_linked(session, destination.id):
        raise HTTPException(status.HTTP_409_CONFLICT, "Transaction is already linked")
    if source.status != "posted" or destination.status != "posted":
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Transfers must be posted")
    if source.kind != "expense" or destination.kind not in {"income", "refund"}:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Invalid transfer directions")
    try:
        validate_transfer_pair(
            source.amount,
            destination.amount,
            TransactionKind.TRANSFER_OUT,
            TransactionKind.TRANSFER_IN,
            source.account_id,
            destination.account_id,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    source_before, destination_before = snapshot(source), snapshot(destination)
    for transaction, kind in (
        (source, TransactionKind.TRANSFER_OUT),
        (destination, TransactionKind.TRANSFER_IN),
    ):
        transaction.kind = kind.value
        transaction.category_id = None
        transaction.category_source = "uncategorized"
        transaction.categorization_rule_id = None
    session.flush()
    link = TransferLink(
        user_id=user.id,
        source_transaction_id=source.id,
        destination_transaction_id=destination.id,
        source_previous=source_before,
        destination_previous=destination_before,
    )
    session.add_all(
        [
            link,
            revision(user.id, source, source_before),
            revision(user.id, destination, destination_before),
        ]
    )
    commit_or_unprocessable(session)
    return link


@router.delete("/{transfer_id}", status_code=status.HTTP_204_NO_CONTENT)
def unmatch_transfer(transfer_id: UUID, session: SessionDep, user: UserDep) -> Response:
    link = session.scalar(
        select(TransferLink).where(TransferLink.id == transfer_id, TransferLink.user_id == user.id)
    )
    if link is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Transfer not found")
    if link.source_previous is None or link.destination_previous is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Transfer cannot be restored automatically")
    source = owned_transaction(session, user.id, link.source_transaction_id)
    destination = owned_transaction(session, user.id, link.destination_transaction_id)
    source_before, destination_before = snapshot(source), snapshot(destination)
    session.delete(link)
    session.flush()
    for transaction, prior in (
        (source, link.source_previous),
        (destination, link.destination_previous),
    ):
        for field in RESTORED_FIELDS:
            value = prior[field]
            setattr(
                transaction,
                field,
                UUID(value) if value is not None and field.endswith("_id") else value,
            )
    session.add_all(
        [
            revision(user.id, source, source_before),
            revision(user.id, destination, destination_before),
        ]
    )
    commit_or_unprocessable(session)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
