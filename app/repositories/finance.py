from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Account, Category, Transaction


def owned_account(session: Session, user_id: UUID, account_id: UUID) -> Account:
    account = session.scalar(
        select(Account).where(Account.id == account_id, Account.user_id == user_id)
    )
    if account is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Account not found")
    return account


def owned_transaction(session: Session, user_id: UUID, transaction_id: UUID) -> Transaction:
    transaction = session.scalar(
        select(Transaction).where(Transaction.id == transaction_id, Transaction.user_id == user_id)
    )
    if transaction is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Transaction not found")
    return transaction


def visible_category(session: Session, user_id: UUID, category_id: UUID) -> Category:
    category = session.scalar(
        select(Category).where(
            Category.id == category_id,
            (Category.user_id == user_id) | (Category.user_id.is_(None)),
        )
    )
    if category is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Category not found")
    return category


def owned_category(session: Session, user_id: UUID, category_id: UUID) -> Category:
    category = session.scalar(
        select(Category).where(Category.id == category_id, Category.user_id == user_id)
    )
    if category is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Category not found")
    return category
