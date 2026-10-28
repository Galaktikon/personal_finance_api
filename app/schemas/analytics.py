from datetime import date
from uuid import UUID

from pydantic import BaseModel


class SummaryOut(BaseModel):
    currency: str = "USD"
    start_date: date | None
    end_date: date | None
    account_id: UUID | None
    transaction_count: int
    gross_income: str
    gross_expenses: str
    refunds: str
    net_spending: str
    net_cash_flow: str


class MonthlyTrendOut(BaseModel):
    month: str
    transaction_count: int
    gross_income: str
    gross_expenses: str
    refunds: str
    net_spending: str
    net_cash_flow: str


class CategoryBreakdownOut(BaseModel):
    category_id: UUID | None
    category_name: str | None
    transaction_count: int
    gross_expenses: str
    refunds: str
    net_spending: str


class MerchantBreakdownOut(BaseModel):
    merchant: str | None
    transaction_count: int
    gross_expenses: str
    refunds: str
    net_spending: str
