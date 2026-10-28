"""Stateless CSV analysis for the public, no-login demo page."""

from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, File, UploadFile
from pydantic import BaseModel, ValidationError

from app.api.v1.imports import parsed_rows, read_upload
from app.domain.money import money_string
from app.schemas.imports import ImportRow

router = APIRouter(prefix="/demo", tags=["demo"])


class DemoRow(BaseModel):
    row_number: int
    status: Literal["accepted", "failed"]
    error_code: str | None = None
    kind: Literal["income", "expense", "refund"] | None = None
    amount: str | None = None
    posted: bool | None = None


class DemoResult(BaseModel):
    total_rows: int
    accepted_count: int
    failed_count: int
    posted_count: int
    pending_count: int
    gross_income: str
    gross_expenses: str
    refunds: str
    net_spending: str
    net_cash_flow: str
    rows: list[DemoRow]


@router.post("/process", response_model=DemoResult)
def process_demo_csv(file: Annotated[UploadFile, File()]) -> DemoResult:
    raw_rows = parsed_rows(read_upload(file, "csv"), "csv")
    rows: list[DemoRow] = []
    income = expenses = refunds = Decimal("0.00")
    posted_count = pending_count = 0

    for row_number, raw in enumerate(raw_rows, 1):
        try:
            row = ImportRow.model_validate(raw)
        except ValidationError:
            rows.append(DemoRow(row_number=row_number, status="failed", error_code="invalid_row"))
            continue
        if row.category_id is not None:
            rows.append(
                DemoRow(
                    row_number=row_number,
                    status="failed",
                    error_code="category_requires_account",
                )
            )
            continue
        posted = row.status == "posted"
        rows.append(
            DemoRow(
                row_number=row_number,
                status="accepted",
                kind=row.kind,
                amount=row.amount,
                posted=posted,
            )
        )
        if not posted:
            pending_count += 1
            continue
        posted_count += 1
        amount = Decimal(row.amount)
        if row.kind == "income":
            income += amount
        elif row.kind == "expense":
            expenses -= amount
        else:
            refunds += amount

    return DemoResult(
        total_rows=len(raw_rows),
        accepted_count=sum(row.status == "accepted" for row in rows),
        failed_count=sum(row.status == "failed" for row in rows),
        posted_count=posted_count,
        pending_count=pending_count,
        gross_income=money_string(income),
        gross_expenses=money_string(expenses),
        refunds=money_string(refunds),
        net_spending=money_string(expenses - refunds),
        net_cash_flow=money_string(income - expenses + refunds),
        rows=rows,
    )
