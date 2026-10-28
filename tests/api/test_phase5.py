import base64
import os
import time
from collections.abc import Iterator
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from fastapi.testclient import TestClient
from jwt import PyJWKClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

from app.core import security
from app.core.config import get_settings
from app.db.session import get_session
from app.main import app

AUTH_URL = "https://phase5.example.test/neondb/auth"
ORIGIN = "https://phase5.example.test"


@dataclass
class Harness:
    client: TestClient
    key: Ed25519PrivateKey
    connection: Connection

    def headers(self, subject: str) -> dict[str, str]:
        now = int(time.time())
        claims = {
            "sub": subject,
            "iss": ORIGIN,
            "aud": ORIGIN,
            "iat": now,
            "exp": now + 900,
            "role": "authenticated",
        }
        token = jwt.encode(claims, self.key, algorithm="EdDSA", headers={"kid": "phase5"})
        return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def api5(monkeypatch: pytest.MonkeyPatch) -> Iterator[Harness]:
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL is not set")
    engine = create_engine(url)
    with engine.connect() as connection:
        outer = connection.begin()

        def test_session() -> Iterator[Session]:
            with Session(
                connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
            ) as session:
                yield session

        app.dependency_overrides[get_session] = test_session
        monkeypatch.setenv("NEON_AUTH_BASE_URL", AUTH_URL)
        get_settings.cache_clear()
        key = Ed25519PrivateKey.generate()
        public = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        jwk = {
            "kty": "OKP",
            "crv": "Ed25519",
            "alg": "EdDSA",
            "use": "sig",
            "kid": "phase5",
            "x": base64.urlsafe_b64encode(public).rstrip(b"=").decode(),
        }
        jwks = PyJWKClient(f"{AUTH_URL}/.well-known/jwks.json", cooldown_duration=0)
        monkeypatch.setattr(jwks, "fetch_data", lambda: {"keys": [jwk]})
        monkeypatch.setattr(security, "get_jwks_client", lambda _: jwks)
        try:
            with TestClient(app) as client:
                yield Harness(client, key, connection)
        finally:
            app.dependency_overrides.clear()
            get_settings.cache_clear()
            outer.rollback()
    engine.dispose()


def account(api: Harness, subject: str, name: str, kind: str = "checking") -> str:
    response = api.client.post(
        "/api/v1/accounts", headers=api.headers(subject), json={"name": name, "type": kind}
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def category(api: Harness, subject: str, name: str) -> str:
    response = api.client.post(
        "/api/v1/categories",
        headers=api.headers(subject),
        json={"name": name, "kind": "expense"},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def transaction(
    api: Harness,
    subject: str,
    account_id: str,
    day: str,
    amount: str,
    kind: str,
    **extra: Any,
) -> str:
    response = api.client.post(
        "/api/v1/transactions",
        headers=api.headers(subject),
        json={
            "account_id": account_id,
            "transaction_date": day,
            "amount": amount,
            "kind": kind,
            "description": "Synthetic phase 5 transaction",
            **extra,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


@pytest.fixture
def ledger(api5: Harness) -> dict[str, str]:
    checking = account(api5, "alice", "Checking")
    card = account(api5, "alice", "Card", "credit_card")
    bob = account(api5, "bob", "Bob")
    food = category(api5, "alice", "Food")
    travel = category(api5, "alice", "Travel")

    transaction(api5, "alice", checking, "2024-02-28", "2000.00", "income")
    transaction(
        api5,
        "alice",
        checking,
        "2024-02-29",
        "-100.25",
        "expense",
        category_id=food,
        merchant="MARKET",
    )
    transaction(
        api5,
        "alice",
        card,
        "2024-02-29",
        "-50.00",
        "expense",
        category_id=travel,
        merchant="Train",
    )
    transaction(
        api5,
        "alice",
        checking,
        "2024-02-29",
        "20.00",
        "refund",
        category_id=food,
        merchant="market",
    )
    transaction(api5, "alice", checking, "2024-03-01", "-10.00", "expense")
    transaction(
        api5,
        "alice",
        checking,
        "2024-03-15",
        "80.00",
        "refund",
        category_id=food,
        merchant="Market",
    )
    transaction(api5, "alice", checking, "2024-03-20", "500.00", "income")
    transaction(api5, "alice", checking, "2024-03-21", "-25.00", "expense", status="pending")
    voided = transaction(api5, "alice", checking, "2024-03-22", "-40.00", "expense")
    assert (
        api5.client.delete(
            f"/api/v1/transactions/{voided}", headers=api5.headers("alice")
        ).status_code
        == 204
    )
    payment = transaction(api5, "alice", checking, "2024-03-25", "-200.00", "expense")
    receipt = transaction(api5, "alice", card, "2024-03-25", "200.00", "income")
    matched = api5.client.post(
        "/api/v1/transfers/match",
        headers=api5.headers("alice"),
        json={"source_transaction_id": payment, "destination_transaction_id": receipt},
    )
    assert matched.status_code == 201, matched.text
    transaction(api5, "bob", bob, "2024-02-29", "-999.00", "expense", merchant="MARKET")
    return {"checking": checking, "card": card, "bob": bob, "food": food, "travel": travel}


def get(api: Harness, subject: str, endpoint: str, **params: Any):
    return api.client.get(
        f"/api/v1/analytics/{endpoint}", headers=api.headers(subject), params=params
    )


def test_summary_reconciles_independent_totals(api5: Harness, ledger: dict[str, str]) -> None:
    response = get(api5, "alice", "summary")
    assert response.status_code == 200, response.text
    assert {
        key: response.json()[key]
        for key in (
            "transaction_count",
            "gross_income",
            "gross_expenses",
            "refunds",
            "net_spending",
            "net_cash_flow",
        )
    } == {
        "transaction_count": 7,
        "gross_income": "2500.00",
        "gross_expenses": "160.25",
        "refunds": "100.00",
        "net_spending": "60.25",
        "net_cash_flow": "2439.75",
    }
    feb = get(api5, "alice", "summary", start_date="2024-02-01", end_date="2024-03-01")
    assert feb.json()["transaction_count"] == 4
    assert feb.json()["net_spending"] == "130.25"
    assert feb.json()["net_cash_flow"] == "1869.75"
    march = get(api5, "alice", "summary", start_date="2024-03-01", end_date="2024-04-01")
    assert march.json()["net_spending"] == "-70.00"
    assert march.json()["net_cash_flow"] == "570.00"
    checking = get(api5, "alice", "summary", account_id=ledger["checking"])
    assert checking.json()["gross_expenses"] == "110.25"
    assert checking.json()["net_cash_flow"] == "2489.75"
    bob = get(api5, "bob", "summary")
    assert bob.json()["gross_expenses"] == "999.00"
    assert bob.json()["gross_income"] == "0.00"


def test_monthly_and_breakdowns(api5: Harness, ledger: dict[str, str]) -> None:
    months = get(api5, "alice", "monthly-trends")
    assert months.status_code == 200, months.text
    assert [(row["month"], row["net_spending"], row["net_cash_flow"]) for row in months.json()] == [
        ("2024-02", "130.25", "1869.75"),
        ("2024-03", "-70.00", "570.00"),
    ]
    assert [
        row["month"] for row in get(api5, "alice", "monthly-trends", limit=1, offset=1).json()
    ] == ["2024-03"]
    categories = get(api5, "alice", "categories")
    assert categories.status_code == 200, categories.text
    by_category = {row["category_id"]: row for row in categories.json()}
    assert by_category[ledger["food"]]["gross_expenses"] == "100.25"
    assert by_category[ledger["food"]]["refunds"] == "100.00"
    assert by_category[ledger["food"]]["net_spending"] == "0.25"
    assert by_category[ledger["travel"]]["net_spending"] == "50.00"
    assert by_category[None]["net_spending"] == "10.00"
    assert sum(Decimal(row["net_spending"]) for row in categories.json()) == Decimal("60.25")
    feb_categories = get(
        api5, "alice", "categories", start_date="2024-02-01", end_date="2024-03-01"
    ).json()
    assert sum(Decimal(row["net_spending"]) for row in feb_categories) == Decimal("130.25")

    merchants = get(api5, "alice", "merchants")
    assert merchants.status_code == 200, merchants.text
    by_merchant = {row["merchant"]: row for row in merchants.json()}
    assert by_merchant["market"]["net_spending"] == "0.25"
    assert by_merchant["train"]["net_spending"] == "50.00"
    assert by_merchant[None]["net_spending"] == "10.00"
    assert get(api5, "bob", "merchants").json()[0]["net_spending"] == "999.00"
    card_merchants = get(api5, "alice", "merchants", account_id=ledger["card"]).json()
    assert [(row["merchant"], row["net_spending"]) for row in card_merchants] == [
        ("train", "50.00")
    ]


def test_refund_only_category_keeps_negative_net(api5: Harness) -> None:
    aid = account(api5, "alice", "Checking")
    cid = category(api5, "alice", "Returns")
    transaction(api5, "alice", aid, "2024-02-29", "15.00", "refund", category_id=cid)
    assert get(api5, "alice", "summary").json()["net_spending"] == "-15.00"
    rows = get(api5, "alice", "categories").json()
    assert len(rows) == 1
    assert rows[0]["net_spending"] == "-15.00"
    assert rows[0]["refunds"] == "15.00"


def test_merchant_groups_case_and_repeated_whitespace(api5: Harness) -> None:
    aid = account(api5, "alice", "Checking")
    transaction(api5, "alice", aid, "2024-02-29", "-5.00", "expense", merchant="BIG  MARKET")
    transaction(api5, "alice", aid, "2024-02-29", "-6.00", "expense", merchant="big market")
    rows = get(api5, "alice", "merchants").json()
    assert len(rows) == 1
    assert rows[0]["merchant"] == "big market"
    assert rows[0]["net_spending"] == "11.00"


def test_empty_filters_and_authorization(api5: Harness, ledger: dict[str, str]) -> None:
    empty = get(api5, "alice", "summary", start_date="2025-01-01", end_date="2025-02-01")
    assert empty.status_code == 200
    assert empty.json()["transaction_count"] == 0
    assert empty.json()["net_cash_flow"] == "0.00"
    for endpoint in ("monthly-trends", "categories", "merchants"):
        assert (
            get(api5, "alice", endpoint, start_date="2025-01-01", end_date="2025-02-01").json()
            == []
        )
    assert get(api5, "alice", "summary", account_id=ledger["bob"]).status_code == 404
    assert (
        get(api5, "alice", "summary", start_date="2024-03-01", end_date="2024-03-01").status_code
        == 422
    )
    assert get(api5, "alice", "categories", limit=0).status_code == 422
    assert api5.client.get("/api/v1/analytics/summary").status_code == 401
