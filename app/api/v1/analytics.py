from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.domain.transactions import validate_date_range
from app.models import UserProfile
from app.repositories.finance import owned_account
from app.schemas.analytics import (
    CategoryBreakdownOut,
    MerchantBreakdownOut,
    MonthlyTrendOut,
    SummaryOut,
)
from app.services import analytics
from app.services.identity import get_current_user

router = APIRouter(prefix="/analytics", tags=["analytics"])
SessionDep = Annotated[Session, Depends(get_session)]
UserDep = Annotated[UserProfile, Depends(get_current_user)]
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]


def check_filters(
    session: Session,
    user_id: UUID,
    account_id: UUID | None,
    start_date: date | None,
    end_date: date | None,
) -> None:
    if account_id is not None:
        owned_account(session, user_id, account_id)
    if start_date is not None and end_date is not None:
        try:
            validate_date_range(start_date, end_date)
        except ValueError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc


@router.get("/summary", response_model=SummaryOut)
def get_summary(
    session: SessionDep,
    user: UserDep,
    account_id: UUID | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> SummaryOut:
    check_filters(session, user.id, account_id, start_date, end_date)
    return analytics.summary(session, user.id, account_id, start_date, end_date)


@router.get("/monthly-trends", response_model=list[MonthlyTrendOut])
def get_monthly_trends(
    session: SessionDep,
    user: UserDep,
    limit: Limit = 50,
    offset: Offset = 0,
    account_id: UUID | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[MonthlyTrendOut]:
    check_filters(session, user.id, account_id, start_date, end_date)
    return analytics.monthly_trends(
        session, user.id, account_id, start_date, end_date, limit, offset
    )


@router.get("/categories", response_model=list[CategoryBreakdownOut])
def get_categories(
    session: SessionDep,
    user: UserDep,
    limit: Limit = 50,
    offset: Offset = 0,
    account_id: UUID | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[CategoryBreakdownOut]:
    check_filters(session, user.id, account_id, start_date, end_date)
    return analytics.category_breakdown(
        session, user.id, account_id, start_date, end_date, limit, offset
    )


@router.get("/merchants", response_model=list[MerchantBreakdownOut])
def get_merchants(
    session: SessionDep,
    user: UserDep,
    limit: Limit = 50,
    offset: Offset = 0,
    account_id: UUID | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[MerchantBreakdownOut]:
    check_filters(session, user.id, account_id, start_date, end_date)
    return analytics.merchant_breakdown(
        session, user.id, account_id, start_date, end_date, limit, offset
    )
