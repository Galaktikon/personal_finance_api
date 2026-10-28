import base64
import time
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from jwt import PyJWKClient

from app.core.security import verify_neon_token

AUTH_URL = "https://auth.example.test/neondb/auth"
ORIGIN = "https://auth.example.test"


def key_material() -> tuple[Ed25519PrivateKey, dict[str, str]]:
    private = Ed25519PrivateKey.generate()
    raw = private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    public = base64.urlsafe_b64encode(raw).rstrip(b"=").decode()
    return private, {"kty": "OKP", "crv": "Ed25519", "alg": "EdDSA", "use": "sig", "x": public}


def token(private: Ed25519PrivateKey, kid: str, **overrides: Any) -> str:
    now = int(time.time())
    claims: dict[str, Any] = {
        "sub": "synthetic-user-1",
        "iss": ORIGIN,
        "aud": ORIGIN,
        "iat": now,
        "exp": now + 900,
        "role": "authenticated",
        "banned": False,
    }
    claims.update(overrides)
    return jwt.encode(claims, private, algorithm="EdDSA", headers={"kid": kid})


def jwks_client(monkeypatch: pytest.MonkeyPatch, keys: list[dict[str, str]]) -> PyJWKClient:
    client = PyJWKClient(f"{AUTH_URL}/.well-known/jwks.json", cooldown_duration=0)
    monkeypatch.setattr(client, "fetch_data", lambda: {"keys": keys})
    return client


def test_valid_ed25519_token(monkeypatch: pytest.MonkeyPatch) -> None:
    private, public = key_material()
    public["kid"] = "one"
    assert verify_neon_token(
        token(private, "one"), AUTH_URL, jwks_client(monkeypatch, [public])
    ) == ("synthetic-user-1")


@pytest.mark.parametrize(
    "claims",
    [
        {"exp": 1},
        {"iat": int(time.time()) + 3600},
        {"iss": "https://wrong.example.test"},
        {"aud": "https://wrong.example.test"},
        {"sub": ""},
        {"role": "anonymous"},
        {"banned": True},
    ],
)
def test_invalid_claims_are_rejected(
    monkeypatch: pytest.MonkeyPatch, claims: dict[str, Any]
) -> None:
    private, public = key_material()
    public["kid"] = "one"
    with pytest.raises(ValueError, match="Invalid credential"):
        verify_neon_token(
            token(private, "one", **claims), AUTH_URL, jwks_client(monkeypatch, [public])
        )


def test_wrong_signature_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    private, _ = key_material()
    _, public = key_material()
    public["kid"] = "one"
    with pytest.raises(ValueError, match="Invalid credential"):
        verify_neon_token(token(private, "one"), AUTH_URL, jwks_client(monkeypatch, [public]))


def test_key_rotation_refreshes_unknown_kid(monkeypatch: pytest.MonkeyPatch) -> None:
    first_private, first_public = key_material()
    second_private, second_public = key_material()
    first_public["kid"] = "first"
    second_public["kid"] = "second"
    keys = [first_public]
    client = jwks_client(monkeypatch, keys)
    assert verify_neon_token(token(first_private, "first"), AUTH_URL, client) == "synthetic-user-1"
    keys.append(second_public)
    assert (
        verify_neon_token(token(second_private, "second"), AUTH_URL, client) == "synthetic-user-1"
    )
