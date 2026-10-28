from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.common import commit_or_unprocessable
from app.db.session import get_session
from app.models import Account, UserProfile
from app.repositories.finance import owned_account
from app.schemas.finance import AccountCreate, AccountOut, AccountPatch
from app.services.identity import get_current_user

router = APIRouter(prefix="/accounts", tags=["accounts"])
SessionDep = Annotated[Session, Depends(get_session)]
UserDep = Annotated[UserProfile, Depends(get_current_user)]


@router.get("", response_model=list[AccountOut])
def list_accounts(
    session: SessionDep,
    user: UserDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    is_active: bool | None = None,
) -> list[Account]:
    query = select(Account).where(Account.user_id == user.id)
    if is_active is not None:
        query = query.where(Account.is_active == is_active)
    return list(
        session.scalars(query.order_by(Account.name, Account.id).limit(limit).offset(offset))
    )


@router.post("", response_model=AccountOut, status_code=status.HTTP_201_CREATED)
def create_account(body: AccountCreate, session: SessionDep, user: UserDep) -> Account:
    account = Account(user_id=user.id, **body.model_dump())
    session.add(account)
    commit_or_unprocessable(session)
    return account


@router.get("/{account_id}", response_model=AccountOut)
def get_account(account_id: UUID, session: SessionDep, user: UserDep) -> Account:
    return owned_account(session, user.id, account_id)


@router.patch("/{account_id}", response_model=AccountOut)
def update_account(
    account_id: UUID, body: AccountPatch, session: SessionDep, user: UserDep
) -> Account:
    account = owned_account(session, user.id, account_id)
    for key, value in body.model_dump(exclude_unset=True).items():
        if value is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"{key} cannot be null")
        setattr(account, key, value)
    commit_or_unprocessable(session)
    return account


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_account(account_id: UUID, session: SessionDep, user: UserDep) -> Response:
    account = owned_account(session, user.id, account_id)
    account.is_active = False
    commit_or_unprocessable(session)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
