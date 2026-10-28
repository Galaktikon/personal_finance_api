import base64
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
from jwt.exceptions import PyJWKClientConnectionError
from sqlalchemy import create_engine, select
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

from app.core import security
from app.core.config import get_settings
from app.db.session import get_session
from app.main import app
from app.models import CategorizationRule, Category, Transaction, TransactionRevision, UserProfile

AUTH_URL = "https://auth.example.test/neondb/auth"
ORIGIN = "https://auth.example.test"


@dataclass
class ApiHarness:
    client: TestClient
    private_key: Ed25519PrivateKey
    connection: Connection

    def headers(self, subject: str, **claims: Any) -> dict[str, str]:
        now = int(time.time())
        payload = {
            "sub": subject,
            "iss": ORIGIN,
            "aud": ORIGIN,
            "iat": now,
            "exp": now + 900,
            "role": "authenticated",
        }
        payload.update(claims)
        token = jwt.encode(payload, self.private_key, algorithm="EdDSA", headers={"kid": "test"})
        return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def api(monkeypatch: pytest.MonkeyPatch) -> Iterator[ApiHarness]:
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

        private = Ed25519PrivateKey.generate()
        public = private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        public_b64 = base64.urlsafe_b64encode(public).rstrip(b"=").decode()
        jwk = {
            "kty": "OKP",
            "crv": "Ed25519",
            "alg": "EdDSA",
            "use": "sig",
            "kid": "test",
            "x": public_b64,
        }
        jwks = PyJWKClient(f"{AUTH_URL}/.well-known/jwks.json", cooldown_duration=0)
        monkeypatch.setattr(jwks, "fetch_data", lambda: {"keys": [jwk]})
        monkeypatch.setattr(security, "get_jwks_client", lambda _: jwks)
        try:
            with TestClient(app) as client:
                yield ApiHarness(client, private, connection)
        finally:
            app.dependency_overrides.clear()
            get_settings.cache_clear()
            outer.rollback()
    engine.dispose()


def create_account(api: ApiHarness, subject: str, name: str = "Checking") -> str:
    response = api.client.post(
        "/api/v1/accounts",
        headers=api.headers(subject),
        json={"name": name, "type": "checking"},
    )
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


def create_category(api: ApiHarness, subject: str, name: str = "Food") -> str:
    response = api.client.post(
        "/api/v1/categories",
        headers=api.headers(subject),
        json={"name": name, "kind": "expense"},
    )
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


def create_transaction(api: ApiHarness, subject: str, account_id: str, **extra: Any) -> str:
    body = {
        "account_id": account_id,
        "transaction_date": "2024-02-29",
        "amount": "-12.50",
        "description": "Synthetic groceries",
        "kind": "expense",
    }
    body.update(extra)
    response = api.client.post("/api/v1/transactions", headers=api.headers(subject), json=body)
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


def test_authentication_failures_are_generic(api: ApiHarness) -> None:
    endpoint = "/api/v1/accounts"
    assert api.client.get(endpoint).status_code == 401
    assert api.client.get(endpoint, headers={"Authorization": "Bearer invalid"}).status_code == 401
    assert api.client.get(endpoint, headers=api.headers("alice", exp=1)).status_code == 401
    assert (
        api.client.get(endpoint, headers=api.headers("alice", iss="https://other.test")).status_code
        == 401
    )
    assert (
        api.client.get(endpoint, headers=api.headers("alice", aud="https://other.test")).status_code
        == 401
    )
    assert api.client.get(endpoint, headers=api.headers("alice")).status_code == 200


def test_jwks_outage_returns_sanitized_503(
    api: ApiHarness, monkeypatch: pytest.MonkeyPatch
) -> None:
    class OfflineJWKS:
        def get_signing_key_from_jwt(self, token: str) -> None:
            raise PyJWKClientConnectionError("synthetic network failure")

    monkeypatch.setattr(security, "get_jwks_client", lambda _: OfflineJWKS())
    response = api.client.get("/api/v1/accounts", headers=api.headers("alice"))
    assert response.status_code == 503
    assert response.json() == {"detail": "Authentication service unavailable"}


def test_accounts_are_scoped_and_archive_instead_of_delete(api: ApiHarness) -> None:
    alice_id = create_account(api, "alice")
    bob_id = create_account(api, "bob", "Bob account")
    alice = api.headers("alice")
    bob = api.headers("bob")
    assert [row["id"] for row in api.client.get("/api/v1/accounts", headers=alice).json()] == [
        alice_id
    ]
    assert api.client.get(f"/api/v1/accounts/{bob_id}", headers=alice).status_code == 404
    assert (
        api.client.patch(
            f"/api/v1/accounts/{bob_id}", headers=alice, json={"name": "X"}
        ).status_code
        == 404
    )
    assert api.client.delete(f"/api/v1/accounts/{bob_id}", headers=alice).status_code == 404
    assert (
        api.client.post(
            "/api/v1/accounts",
            headers=alice,
            json={"name": "Forged", "type": "cash", "user_id": "bob"},
        ).status_code
        == 422
    )
    assert api.client.delete(f"/api/v1/accounts/{alice_id}", headers=alice).status_code == 204
    assert (
        api.client.get(f"/api/v1/accounts/{alice_id}", headers=alice).json()["is_active"] is False
    )
    assert api.client.get(f"/api/v1/accounts/{bob_id}", headers=bob).status_code == 200


def test_categories_system_visibility_and_cross_user_protection(api: ApiHarness) -> None:
    alice_category = create_category(api, "alice")
    bob_category = create_category(api, "bob", "Bob private")
    system = Category(name="System food", kind="expense", user_id=None)
    with Session(
        api.connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
    ) as session:
        session.add(system)
        session.commit()
    alice = api.headers("alice")
    rows = api.client.get("/api/v1/categories", headers=alice).json()
    assert {row["id"] for row in rows} == {alice_category, str(system.id)}
    assert next(row for row in rows if row["id"] == str(system.id))["is_system"] is True
    assert (
        api.client.patch(
            f"/api/v1/categories/{bob_category}", headers=alice, json={"name": "X"}
        ).status_code
        == 404
    )
    assert (
        api.client.patch(
            f"/api/v1/categories/{system.id}", headers=alice, json={"name": "X"}
        ).status_code
        == 404
    )


def test_transactions_are_scoped_validated_and_voided(api: ApiHarness) -> None:
    alice_account = create_account(api, "alice")
    bob_account = create_account(api, "bob", "Bob account")
    alice_category = create_category(api, "alice")
    bob_category = create_category(api, "bob", "Bob private")
    alice = api.headers("alice")
    bob = api.headers("bob")
    tx_id = create_transaction(api, "alice", alice_account, category_id=alice_category)
    assert api.client.get(f"/api/v1/transactions/{tx_id}", headers=bob).status_code == 404
    assert (
        api.client.patch(
            f"/api/v1/transactions/{tx_id}", headers=bob, json={"amount": "-1.00"}
        ).status_code
        == 404
    )
    assert api.client.delete(f"/api/v1/transactions/{tx_id}", headers=bob).status_code == 404
    assert [row["id"] for row in api.client.get("/api/v1/transactions", headers=bob).json()] == []
    assert (
        api.client.post(
            "/api/v1/transactions",
            headers=alice,
            json={
                "account_id": bob_account,
                "transaction_date": "2024-02-29",
                "amount": "-1.00",
                "description": "X",
                "kind": "expense",
            },
        ).status_code
        == 404
    )
    assert (
        api.client.post(
            "/api/v1/transactions",
            headers=alice,
            json={
                "account_id": alice_account,
                "transaction_date": "2024-02-29",
                "amount": "-1.00",
                "description": "X",
                "kind": "expense",
                "category_id": bob_category,
            },
        ).status_code
        == 404
    )
    assert (
        api.client.patch(
            f"/api/v1/transactions/{tx_id}", headers=alice, json={"amount": "-1.234"}
        ).status_code
        == 422
    )
    forged = {
        "account_id": alice_account,
        "transaction_date": "2024-02-29",
        "amount": "-1.00",
        "description": "Forged",
        "kind": "expense",
        "user_id": "bob",
    }
    assert api.client.post("/api/v1/transactions", headers=alice, json=forged).status_code == 422
    assert (
        api.client.patch(
            f"/api/v1/transactions/{tx_id}", headers=alice, json={"amount": "-15.00"}
        ).status_code
        == 200
    )
    assert (
        api.client.get(f"/api/v1/transactions/{tx_id}", headers=alice).json()["amount"] == "-15.00"
    )
    assert api.client.delete(f"/api/v1/transactions/{tx_id}", headers=alice).status_code == 204
    assert (
        api.client.get(f"/api/v1/transactions/{tx_id}", headers=alice).json()["status"] == "voided"
    )
    with Session(api.connection, join_transaction_mode="create_savepoint") as session:
        assert len(session.scalars(select(TransactionRevision)).all()) == 2


def test_list_filters_pagination_and_inactive_account(api: ApiHarness) -> None:
    account_id = create_account(api, "alice")
    first = create_transaction(api, "alice", account_id, transaction_date="2024-02-29")
    create_transaction(api, "alice", account_id, transaction_date="2024-03-01")
    headers = api.headers("alice")
    response = api.client.get(
        "/api/v1/transactions?start_date=2024-02-01&end_date=2024-03-01&limit=1", headers=headers
    )
    assert [row["id"] for row in response.json()] == [first]
    assert api.client.get("/api/v1/transactions?limit=101", headers=headers).status_code == 422
    assert (
        api.client.get(
            "/api/v1/transactions?start_date=2024-03-01&end_date=2024-02-01", headers=headers
        ).status_code
        == 422
    )
    assert api.client.delete(f"/api/v1/accounts/{account_id}", headers=headers).status_code == 204
    body = {
        "account_id": account_id,
        "transaction_date": "2024-03-02",
        "amount": "-1.00",
        "description": "X",
        "kind": "expense",
    }
    assert api.client.post("/api/v1/transactions", headers=headers, json=body).status_code == 422


def test_profile_subject_is_mapped_from_token(api: ApiHarness) -> None:
    create_account(api, "alice")
    with Session(api.connection, join_transaction_mode="create_savepoint") as session:
        profiles = session.scalars(select(UserProfile)).all()
        assert len(profiles) == 1
        assert profiles[0].auth_subject_id == "alice"


def test_manual_category_override_clears_rule_reference(api: ApiHarness) -> None:
    account_id = create_account(api, "alice")
    category_id = create_category(api, "alice")
    tx_id = create_transaction(api, "alice", account_id)
    with Session(api.connection, join_transaction_mode="create_savepoint") as session:
        user = session.scalars(
            select(UserProfile).where(UserProfile.auth_subject_id == "alice")
        ).one()
        rule = CategorizationRule(
            user_id=user.id,
            name="Store rule",
            priority=10,
            condition_type="contains",
            condition_value="STORE",
            category_id=category_id,
        )
        session.add(rule)
        session.flush()
        tx = session.get(Transaction, tx_id)
        assert tx is not None
        tx.category_id = category_id
        tx.category_source = "user_rule"
        tx.categorization_rule_id = rule.id
        session.commit()
    response = api.client.patch(
        f"/api/v1/transactions/{tx_id}",
        headers=api.headers("alice"),
        json={"category_id": category_id},
    )
    assert response.status_code == 200, response.text
    assert response.json()["category_source"] == "manual"
    with Session(api.connection, join_transaction_mode="create_savepoint") as session:
        tx = session.get(Transaction, tx_id)
        assert tx is not None
        assert tx.categorization_rule_id is None
