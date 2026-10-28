from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import Row, case, func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.domain.money import money_string
from app.models import Category, Transaction
from app.schemas.analytics import (
    CategoryBreakdownOut,
    MerchantBreakdownOut,
    MonthlyTrendOut,
    SummaryOut,
)


def base_filters(
    user_id: UUID,
    account_id: UUID | None,
    start_date: date | None,
    end_date: date | None,
) -> tuple[ColumnElement[bool], ...]:
    filters: list[ColumnElement[bool]] = [
        Transaction.user_id == user_id,
        Transaction.status == "posted",
        Transaction.kind.in_(("income", "expense", "refund")),
    ]
    if account_id is not None:
        filters.append(Transaction.account_id == account_id)
    if start_date is not None:
        filters.append(Transaction.transaction_date >= start_date)
    if end_date is not None:
        filters.append(Transaction.transaction_date < end_date)
    return tuple(filters)


def money_aggregates() -> tuple[ColumnElement[Any], ...]:
    income = func.coalesce(
        func.sum(case((Transaction.kind == "income", Transaction.amount), else_=0)), 0
    ).label("gross_income")
    expenses = func.coalesce(
        func.sum(case((Transaction.kind == "expense", -Transaction.amount), else_=0)), 0
    ).label("gross_expenses")
    refunds = func.coalesce(
        func.sum(case((Transaction.kind == "refund", Transaction.amount), else_=0)), 0
    ).label("refunds")
    count = func.count(Transaction.id).label("transaction_count")
    return count, income, expenses, refunds


def values(row: Row[Any]) -> tuple[int, Decimal, Decimal, Decimal]:
    return (
        int(row.transaction_count),
        Decimal(row.gross_income),
        Decimal(row.gross_expenses),
        Decimal(row.refunds),
    )


def totals(
    count: int, income: Decimal, expenses: Decimal, refunds: Decimal
) -> dict[str, int | str]:
    return {
        "transaction_count": count,
        "gross_income": money_string(income),
        "gross_expenses": money_string(expenses),
        "refunds": money_string(refunds),
        "net_spending": money_string(expenses - refunds),
        "net_cash_flow": money_string(income - expenses + refunds),
    }


def summary(
    session: Session,
    user_id: UUID,
    account_id: UUID | None,
    start_date: date | None,
    end_date: date | None,
) -> SummaryOut:
    row = session.execute(
        select(*money_aggregates()).where(*base_filters(user_id, account_id, start_date, end_date))
    ).one()
    return SummaryOut(
        start_date=start_date,
        end_date=end_date,
        account_id=account_id,
        **totals(*values(row)),
    )


def monthly_trends(
    session: Session,
    user_id: UUID,
    account_id: UUID | None,
    start_date: date | None,
    end_date: date | None,
    limit: int,
    offset: int,
) -> list[MonthlyTrendOut]:
    year = func.extract("year", Transaction.transaction_date).label("year")
    month = func.extract("month", Transaction.transaction_date).label("month")
    rows = session.execute(
        select(year, month, *money_aggregates())
        .where(*base_filters(user_id, account_id, start_date, end_date))
        .group_by(year, month)
        .order_by(year, month)
        .limit(limit)
        .offset(offset)
    )
    return [
        MonthlyTrendOut(month=f"{int(row.year):04d}-{int(row.month):02d}", **totals(*values(row)))
        for row in rows
    ]


def spending_aggregates() -> tuple[ColumnElement[Any], ...]:
    expenses = func.coalesce(
        func.sum(case((Transaction.kind == "expense", -Transaction.amount), else_=0)), 0
    ).label("gross_expenses")
    refunds = func.coalesce(
        func.sum(case((Transaction.kind == "refund", Transaction.amount), else_=0)), 0
    ).label("refunds")
    return (
        func.count(Transaction.id).label("transaction_count"),
        expenses,
        refunds,
        (expenses - refunds).label("net_spending"),
    )


def category_breakdown(
    session: Session,
    user_id: UUID,
    account_id: UUID | None,
    start_date: date | None,
    end_date: date | None,
    limit: int,
    offset: int,
) -> list[CategoryBreakdownOut]:
    count, expenses, refunds, net = spending_aggregates()
    rows = session.execute(
        select(Category.id, Category.name, count, expenses, refunds, net)
        .select_from(Transaction)
        .outerjoin(Category, Category.id == Transaction.category_id)
        .where(
            *base_filters(user_id, account_id, start_date, end_date),
            Transaction.kind.in_(("expense", "refund")),
        )
        .group_by(Category.id, Category.name)
        .order_by(net.desc(), Category.name.asc().nulls_last(), Category.id)
        .limit(limit)
        .offset(offset)
    )
    return [
        CategoryBreakdownOut(
            category_id=row.id,
            category_name=row.name,
            transaction_count=row.transaction_count,
            gross_expenses=money_string(Decimal(row.gross_expenses)),
            refunds=money_string(Decimal(row.refunds)),
            net_spending=money_string(Decimal(row.net_spending)),
        )
        for row in rows
    ]


def merchant_breakdown(
    session: Session,
    user_id: UUID,
    account_id: UUID | None,
    start_date: date | None,
    end_date: date | None,
    limit: int,
    offset: int,
) -> list[MerchantBreakdownOut]:
    merchant = func.coalesce(
        func.nullif(Transaction.normalized_merchant, ""),
        func.nullif(
            func.regexp_replace(
                func.lower(func.trim(Transaction.merchant)), "[[:space:]]+", " ", "g"
            ),
            "",
        ),
    ).label("merchant")
    count, expenses, refunds, net = spending_aggregates()
    rows = session.execute(
        select(merchant, count, expenses, refunds, net)
        .where(
            *base_filters(user_id, account_id, start_date, end_date),
            Transaction.kind.in_(("expense", "refund")),
        )
        .group_by(merchant)
        .order_by(net.desc(), merchant.asc().nulls_last())
        .limit(limit)
        .offset(offset)
    )
    return [
        MerchantBreakdownOut(
            merchant=row.merchant,
            transaction_count=row.transaction_count,
            gross_expenses=money_string(Decimal(row.gross_expenses)),
            refunds=money_string(Decimal(row.refunds)),
            net_spending=money_string(Decimal(row.net_spending)),
        )
        for row in rows
    ]
