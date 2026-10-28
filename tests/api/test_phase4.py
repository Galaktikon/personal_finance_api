import base64
import csv
import io
import json
import os
import time
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from fastapi.testclient import TestClient
from jwt import PyJWKClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.engine import Connection
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.v1 import imports as import_routes
from app.api.v1 import transfers as transfer_routes
from app.core import security
from app.core.config import get_settings
from app.db.session import get_session
from app.main import app
from app.models import (
    CategorizationRule,
    Category,
    ImportJob,
    ImportRecord,
    Transaction,
    TransactionRevision,
    TransferLink,
)
from scripts.demo_synthetic import run_demo
from scripts.smoke_deployment import check_deployment

AUTH_URL = "https://phase4.example.test/neondb/auth"
ORIGIN = "https://phase4.example.test"


@dataclass
class Harness:
    client: TestClient
    key: Ed25519PrivateKey
    connection: Connection

    def headers(self, subject: str, idempotency_key: str | None = None) -> dict[str, str]:
        now = int(time.time())
        claims = {
            "sub": subject,
            "iss": ORIGIN,
            "aud": ORIGIN,
            "iat": now,
            "exp": now + 900,
            "role": "authenticated",
        }
        token = jwt.encode(claims, self.key, algorithm="EdDSA", headers={"kid": "phase4"})
        headers = {"Authorization": f"Bearer {token}"}
        if idempotency_key is not None:
            headers["Idempotency-Key"] = idempotency_key
        return headers


@pytest.fixture
def api4(monkeypatch: pytest.MonkeyPatch) -> Iterator[Harness]:
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
            "kid": "phase4",
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


def account(api: Harness, subject: str, name: str = "Checking", kind: str = "checking") -> str:
    response = api.client.post(
        "/api/v1/accounts", headers=api.headers(subject), json={"name": name, "type": kind}
    )
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


def category(api: Harness, subject: str, name: str = "Food") -> str:
    response = api.client.post(
        "/api/v1/categories",
        headers=api.headers(subject),
        json={"name": name, "kind": "expense"},
    )
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


def rule(api: Harness, subject: str, category_id: str, value: str = "market") -> str:
    response = api.client.post(
        "/api/v1/categorization-rules",
        headers=api.headers(subject),
        json={
            "name": "Market rule",
            "priority": 10,
            "condition_type": "contains",
            "condition_value": value,
            "category_id": category_id,
        },
    )
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


def upload(
    api: Harness,
    subject: str,
    account_id: str,
    rows: list[dict[str, Any]],
    key: str | None = None,
    preview: bool = False,
    fmt: str = "json",
):
    if fmt == "json":
        content = json.dumps(rows).encode()
        filename, mime = "synthetic.json", "application/json"
    else:
        buffer = io.StringIO()
        writer = csv.DictWriter(
            buffer,
            fieldnames=[
                "transaction_date",
                "amount",
                "description",
                "kind",
                "external_transaction_id",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
        content = buffer.getvalue().encode()
        filename, mime = "synthetic.csv", "text/csv"
    return api.client.post(
        "/api/v1/imports/preview" if preview else "/api/v1/imports",
        headers=api.headers(subject, key),
        data={
            "account_id": account_id,
            "source_identifier": "Synthetic Bank",
            "source_format": fmt,
        },
        files={"file": (filename, content, mime)},
    )


def expense(external_id: str | None = None, **overrides: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "transaction_date": "2024-02-29",
        "amount": "-12.50",
        "description": "Market purchase",
        "kind": "expense",
        "merchant": "MARKET",
    }
    if external_id is not None:
        row["external_transaction_id"] = external_id
    row.update(overrides)
    return row


def count(session: Session, model: Any) -> int:
    return int(session.scalar(select(func.count()).select_from(model)) or 0)


def test_preview_commit_partial_success_and_idempotency(api4: Harness) -> None:
    aid = account(api4, "alice")
    cid = category(api4, "alice")
    rid = rule(api4, "alice", cid)
    rows = [expense("ext-1"), expense(amount="-1.234"), expense(), expense()]
    preview = upload(api4, "alice", aid, rows, preview=True)
    assert preview.status_code == 200, preview.text
    assert (preview.json()["created_count"], preview.json()["failed_count"]) == (3, 1)
    assert preview.json()["rows"][3]["warning_code"] == "possible_duplicate"
    with Session(api4.connection, join_transaction_mode="create_savepoint") as session:
        assert count(session, ImportJob) == 0
        assert count(session, Transaction) == 0

    committed = upload(api4, "alice", aid, rows, key="first")
    assert committed.status_code == 201, committed.text
    data = committed.json()
    assert (data["created_count"], data["failed_count"], data["total_rows"]) == (3, 1, 4)
    assert data["rows"][1]["error_code"] == "invalid_row"
    assert data["rows"][1]["transaction_id"] is None
    with Session(api4.connection, join_transaction_mode="create_savepoint") as session:
        assert count(session, Transaction) == 3
        first = session.get(Transaction, data["rows"][0]["transaction_id"])
        assert first is not None
        assert str(first.category_id) == cid
        assert str(first.categorization_rule_id) == rid
        assert first.category_source == "user_rule"
    replay = upload(api4, "alice", aid, rows, key="first")
    assert replay.status_code == 200
    assert replay.json()["id"] == data["id"]
    assert upload(api4, "alice", aid, [expense("other")], key="first").status_code == 409
    assert (
        api4.client.get(f"/api/v1/imports/{data['id']}", headers=api4.headers("bob")).status_code
        == 404
    )
    assert api4.client.get("/api/v1/imports", headers=api4.headers("bob")).json() == []
    assert upload(api4, "bob", aid, rows, preview=True).status_code == 404

    repeated = upload(api4, "alice", aid, rows, key="second")
    assert repeated.status_code == 201
    assert (repeated.json()["created_count"], repeated.json()["duplicate_count"]) == (2, 1)
    assert repeated.json()["rows"][2]["warning_code"] == "possible_duplicate"


def test_csv_pending_reconciliation_preserves_manual_category(api4: Harness) -> None:
    aid = account(api4, "alice")
    cid = category(api4, "alice")
    pending = [
        {
            "transaction_date": "2024-02-29",
            "amount": "-10.00",
            "description": "Store",
            "kind": "expense",
            "external_transaction_id": "pending-1",
        }
    ]
    first = upload(api4, "alice", aid, pending, key="pending", fmt="csv")
    assert first.status_code == 201, first.text
    tx_id = first.json()["rows"][0]["transaction_id"]
    # The first file defaults to posted; use an explicit pending JSON row for reconciliation.
    second_pending = upload(
        api4, "alice", aid, [expense("pending-2", status="pending")], key="pending2"
    )
    assert second_pending.status_code == 201
    pending_id = second_pending.json()["rows"][0]["transaction_id"]
    patched = api4.client.patch(
        f"/api/v1/transactions/{pending_id}",
        headers=api4.headers("alice"),
        json={"category_id": cid},
    )
    assert patched.status_code == 200
    posted = upload(
        api4, "alice", aid, [expense("pending-2", status="posted", amount="-11.00")], key="posted"
    )
    assert posted.status_code == 201, posted.text
    assert posted.json()["updated_count"] == 1
    assert posted.json()["rows"][0]["transaction_id"] == pending_id
    detail = api4.client.get(f"/api/v1/transactions/{pending_id}", headers=api4.headers("alice"))
    assert detail.json()["status"] == "posted"
    assert detail.json()["amount"] == "-11.00"
    assert detail.json()["category_id"] == cid
    assert detail.json()["category_source"] == "manual"
    assert (
        upload(api4, "alice", aid, [expense("pending-2", status="pending")], key="regress").json()[
            "duplicate_count"
        ]
        == 1
    )
    assert tx_id != pending_id


def test_preview_reconciles_pending_and_posted_in_one_file(api4: Harness) -> None:
    aid = account(api4, "alice")
    rows = [
        expense("same-file", status="pending"),
        expense("same-file", status="posted", amount="-13.00"),
    ]
    preview = upload(api4, "alice", aid, rows, preview=True)
    assert preview.status_code == 200
    assert [row["status"] for row in preview.json()["rows"]] == ["created", "updated"]
    committed = upload(api4, "alice", aid, rows, key="same-file")
    assert committed.status_code == 201
    assert [row["status"] for row in committed.json()["rows"]] == ["created", "updated"]
    assert (
        committed.json()["rows"][0]["transaction_id"]
        == committed.json()["rows"][1]["transaction_id"]
    )


def test_rule_ownership_and_precedence(api4: Harness) -> None:
    aid = account(api4, "alice")
    own_category = category(api4, "alice")
    bob_category = category(api4, "bob", "Bob food")
    user_rule = rule(api4, "alice", own_category)
    bob_rule = rule(api4, "bob", bob_category)
    alice_rules = api4.client.get(
        "/api/v1/categorization-rules", headers=api4.headers("alice")
    ).json()
    assert user_rule in {item["id"] for item in alice_rules}
    assert bob_rule not in {item["id"] for item in alice_rules}
    with Session(
        api4.connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
    ) as session:
        system_category = Category(name="System food", kind="expense", user_id=None)
        session.add(system_category)
        session.flush()
        system_rule = CategorizationRule(
            name="System market",
            priority=0,
            condition_type="contains",
            condition_value="market",
            category_id=system_category.id,
            user_id=None,
        )
        session.add(system_rule)
        session.commit()
    first = upload(api4, "alice", aid, [expense("rule-1")], key="rule1")
    tx_id = first.json()["rows"][0]["transaction_id"]
    tx = api4.client.get(f"/api/v1/transactions/{tx_id}", headers=api4.headers("alice")).json()
    assert tx["category_id"] == own_category
    assert tx["category_source"] == "user_rule"
    assert (
        api4.client.post(
            "/api/v1/categorization-rules",
            headers=api4.headers("alice"),
            json={
                "name": "Forged",
                "condition_type": "contains",
                "condition_value": "market",
                "category_id": bob_category,
            },
        ).status_code
        == 404
    )
    invalid_category = upload(
        api4, "alice", aid, [expense("forged-category", category_id=bob_category)], key="forged"
    )
    assert invalid_category.status_code == 201
    assert invalid_category.json()["rows"][0]["error_code"] == "invalid_category"
    assert invalid_category.json()["created_count"] == 0
    assert (
        api4.client.post(
            "/api/v1/categorization-rules",
            headers=api4.headers("alice"),
            json={
                "name": "  ",
                "condition_type": "contains",
                "condition_value": "market",
                "category_id": own_category,
            },
        ).status_code
        == 422
    )
    assert (
        api4.client.patch(
            f"/api/v1/categorization-rules/{user_rule}",
            headers=api4.headers("bob"),
            json={"is_active": False},
        ).status_code
        == 404
    )
    assert (
        api4.client.delete(
            f"/api/v1/categorization-rules/{user_rule}", headers=api4.headers("alice")
        ).status_code
        == 204
    )
    second = upload(api4, "alice", aid, [expense("rule-2")], key="rule2")
    second_tx = api4.client.get(
        f"/api/v1/transactions/{second.json()['rows'][0]['transaction_id']}",
        headers=api4.headers("alice"),
    ).json()
    assert second_tx["category_id"] == str(system_category.id)
    assert second_tx["category_source"] == "system_rule"
    assert (
        api4.client.patch(
            f"/api/v1/categorization-rules/{system_rule.id}",
            headers=api4.headers("alice"),
            json={"is_active": False},
        ).status_code
        == 404
    )


def test_transfer_match_unmatch_and_isolation(api4: Harness) -> None:
    checking = account(api4, "alice")
    card = account(api4, "alice", "Card", "credit_card")
    other = account(api4, "bob", "Bob")
    food = category(api4, "alice")
    source = api4.client.post(
        "/api/v1/transactions",
        headers=api4.headers("alice"),
        json={
            "account_id": checking,
            "transaction_date": "2024-02-29",
            "amount": "-25.00",
            "description": "Card payment",
            "kind": "expense",
            "category_id": food,
        },
    ).json()["id"]
    destination = api4.client.post(
        "/api/v1/transactions",
        headers=api4.headers("alice"),
        json={
            "account_id": card,
            "transaction_date": "2024-02-29",
            "amount": "25.00",
            "description": "Payment received",
            "kind": "income",
        },
    ).json()["id"]
    bob_tx = api4.client.post(
        "/api/v1/transactions",
        headers=api4.headers("bob"),
        json={
            "account_id": other,
            "transaction_date": "2024-02-29",
            "amount": "25.00",
            "description": "Other",
            "kind": "income",
        },
    ).json()["id"]
    assert (
        api4.client.post(
            "/api/v1/transfers/match",
            headers=api4.headers("alice"),
            json={"source_transaction_id": source, "destination_transaction_id": bob_tx},
        ).status_code
        == 404
    )
    matched = api4.client.post(
        "/api/v1/transfers/match",
        headers=api4.headers("alice"),
        json={"source_transaction_id": source, "destination_transaction_id": destination},
    )
    assert matched.status_code == 201, matched.text
    link_id = matched.json()["id"]
    assert (
        api4.client.get(f"/api/v1/transactions/{source}", headers=api4.headers("alice")).json()[
            "kind"
        ]
        == "transfer_out"
    )
    assert (
        api4.client.get(
            f"/api/v1/transactions/{destination}", headers=api4.headers("alice")
        ).json()["kind"]
        == "transfer_in"
    )
    assert (
        api4.client.patch(
            f"/api/v1/transactions/{source}",
            headers=api4.headers("alice"),
            json={"amount": "-20.00"},
        ).status_code
        == 409
    )
    assert (
        api4.client.delete(f"/api/v1/transfers/{link_id}", headers=api4.headers("bob")).status_code
        == 404
    )
    assert (
        api4.client.delete(
            f"/api/v1/transfers/{link_id}", headers=api4.headers("alice")
        ).status_code
        == 204
    )
    assert (
        api4.client.get(f"/api/v1/transactions/{source}", headers=api4.headers("alice")).json()[
            "kind"
        ]
        == "expense"
    )
    restored = api4.client.get(
        f"/api/v1/transactions/{source}", headers=api4.headers("alice")
    ).json()
    assert restored["category_id"] == food
    assert restored["category_source"] == "manual"
    assert (
        api4.client.get(
            f"/api/v1/transactions/{destination}", headers=api4.headers("alice")
        ).json()["kind"]
        == "income"
    )
    with Session(api4.connection, join_transaction_mode="create_savepoint") as session:
        assert count(session, TransactionRevision) == 4


def test_import_database_failure_rolls_back_all_writes(
    api4: Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    aid = account(api4, "alice")
    original = import_routes.process_rows

    def fail_after_writes(*args: Any, **kwargs: Any):
        original(*args, **kwargs)
        raise SQLAlchemyError("synthetic persistence failure")

    monkeypatch.setattr(import_routes, "process_rows", fail_after_writes)
    response = upload(api4, "alice", aid, [expense("rollback")], key="rollback")
    assert response.status_code == 500
    assert response.json() == {"detail": "Import could not be saved"}
    with Session(api4.connection, join_transaction_mode="create_savepoint") as session:
        assert count(session, Transaction) == 0
        assert count(session, ImportJob) == 0
        assert count(session, ImportRecord) == 0


def test_import_limits_and_bad_input(api4: Harness, monkeypatch: pytest.MonkeyPatch) -> None:
    aid = account(api4, "alice")
    bad_json = api4.client.post(
        "/api/v1/imports/preview",
        headers=api4.headers("alice"),
        data={"account_id": aid, "source_identifier": "Bank", "source_format": "json"},
        files={"file": ("bad.json", b"not-json", "application/json")},
    )
    assert bad_json.status_code == 422
    monkeypatch.setenv("IMPORT_MAX_ROWS", "1")
    get_settings.cache_clear()
    assert upload(api4, "alice", aid, [expense(), expense()], preview=True).status_code == 422
    monkeypatch.setenv("IMPORT_MAX_BYTES", "10")
    get_settings.cache_clear()
    assert upload(api4, "alice", aid, [expense()], preview=True).status_code == 413


def test_transfer_failure_rolls_back_classifications_and_link(
    api4: Harness, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    checking = account(api4, "alice")
    savings = account(api4, "alice", "Savings", "savings")
    source = api4.client.post(
        "/api/v1/transactions",
        headers=api4.headers("alice"),
        json={
            "account_id": checking,
            "transaction_date": "2024-02-29",
            "amount": "-25.00",
            "description": "Private source description",
            "kind": "expense",
        },
    ).json()["id"]
    destination = api4.client.post(
        "/api/v1/transactions",
        headers=api4.headers("alice"),
        json={
            "account_id": savings,
            "transaction_date": "2024-02-29",
            "amount": "25.00",
            "description": "Private destination description",
            "kind": "income",
        },
    ).json()["id"]

    def fail_after_flush(_: Session) -> None:
        raise SQLAlchemyError("synthetic secret SQL and private financial record")

    match_body = {"source_transaction_id": source, "destination_transaction_id": destination}
    with monkeypatch.context() as patch:
        patch.setattr(transfer_routes, "commit_or_unprocessable", fail_after_flush)
        with caplog.at_level("ERROR"):
            response = api4.client.post(
                "/api/v1/transfers/match",
                headers=api4.headers("alice"),
                json=match_body,
            )
    assert response.status_code == 500
    assert response.json() == {"detail": "Operation could not be completed"}
    assert "secret" not in caplog.text
    assert "Private" not in caplog.text
    with Session(api4.connection, join_transaction_mode="create_savepoint") as session:
        assert count(session, TransferLink) == 0
        assert count(session, TransactionRevision) == 0
        assert session.get(Transaction, source).kind == "expense"  # type: ignore[union-attr]
        assert session.get(Transaction, destination).kind == "income"  # type: ignore[union-attr]

    matched = api4.client.post(
        "/api/v1/transfers/match", headers=api4.headers("alice"), json=match_body
    )
    assert matched.status_code == 201
    with monkeypatch.context() as patch:
        patch.setattr(transfer_routes, "commit_or_unprocessable", fail_after_flush)
        failed_unmatch = api4.client.delete(
            f"/api/v1/transfers/{matched.json()['id']}", headers=api4.headers("alice")
        )
    assert failed_unmatch.status_code == 500
    with Session(api4.connection, join_transaction_mode="create_savepoint") as session:
        assert count(session, TransferLink) == 1
        assert count(session, TransactionRevision) == 2
        assert session.get(Transaction, source).kind == "transfer_out"  # type: ignore[union-attr]
        assert session.get(Transaction, destination).kind == "transfer_in"  # type: ignore[union-attr]


def test_synthetic_demo_is_repeatable(api4: Harness) -> None:
    api4.client.headers.update(api4.headers("alice"))
    first = run_demo(api4.client)
    second = run_demo(api4.client)
    assert first["account_id"] == second["account_id"]
    assert first["import_id"] == second["import_id"]
    assert first["gross_income"] == "2500.00"
    assert first["gross_expenses"] == "130.00"
    assert first["refunds"] == "20.00"
    assert first["net_cash_flow"] == "2390.00"
    with Session(api4.connection, join_transaction_mode="create_savepoint") as session:
        assert count(session, ImportJob) == 1
        assert count(session, Transaction) == 5


def test_deployment_smoke_contract_with_synthetic_auth(api4: Harness) -> None:
    token = api4.headers("alice")["Authorization"].split(" ", 1)[1]
    check_deployment(api4.client, token)


def test_validation_errors_and_logs_do_not_echo_private_input(api4: Harness) -> None:
    secret = "PRIVATE_RAW_FINANCIAL_RECORD_123"
    response = api4.client.post(
        "/api/v1/accounts",
        headers=api4.headers("alice"),
        json={"name": "Checking", "type": "checking", secret: secret},
    )
    assert response.status_code == 422
    assert secret not in response.text
    assert response.json() == {"detail": [{"type": "extra_forbidden"}]}


def test_request_body_limit_covers_streamed_uploads(
    api4: Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("IMPORT_MAX_BYTES", "10")
    monkeypatch.setenv("REQUEST_MAX_BYTES", "100")
    get_settings.cache_clear()
    response = api4.client.post(
        "/api/v1/accounts",
        headers=api4.headers("alice"),
        content=(piece for piece in (b'{"name":"', b"x" * 150, b'","type":"checking"}')),
    )
    assert response.status_code == 413
    assert response.json() == {"detail": "Request body exceeds size limit"}
