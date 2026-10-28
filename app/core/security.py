from functools import lru_cache
from typing import Annotated, Any
from urllib.parse import urlsplit

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from jwt.exceptions import InvalidTokenError, PyJWKClientConnectionError, PyJWKClientError

from app.core.config import get_settings

bearer_scheme = HTTPBearer(auto_error=False)


class AuthServiceUnavailable(Exception):
    """The configured JWKS endpoint cannot currently be reached."""


@lru_cache
def get_jwks_client(base_url: str) -> PyJWKClient:
    return PyJWKClient(
        f"{base_url}/.well-known/jwks.json",
        cache_jwk_set=True,
        cache_keys=False,
        lifespan=300,
        cooldown_duration=0,
        timeout=5,
    )


def verify_neon_token(token: str, base_url: str, client: PyJWKClient | None = None) -> str:
    """Return only a subject verified with this branch's EdDSA JWKS and claims."""
    origin = f"{urlsplit(base_url).scheme}://{urlsplit(base_url).netloc}"
    jwks = client or get_jwks_client(base_url)
    try:
        header = jwt.get_unverified_header(token)
        if header.get("alg") != "EdDSA" or not isinstance(header.get("kid"), str):
            raise InvalidTokenError("Unexpected token header")
        key = jwks.get_signing_key_from_jwt(token)
        payload: dict[str, Any] = jwt.decode(
            token,
            key.key,
            algorithms=["EdDSA"],
            issuer=origin,
            audience=origin,
            options={"require": ["exp", "iat", "iss", "aud", "sub"]},
        )
    except PyJWKClientConnectionError as exc:
        raise AuthServiceUnavailable from exc
    except (InvalidTokenError, PyJWKClientError) as exc:
        raise ValueError("Invalid credential") from exc

    subject = payload.get("sub")
    if (
        not isinstance(subject, str)
        or not subject
        or len(subject) > 255
        or payload.get("role") != "authenticated"
        or payload.get("banned") is True
    ):
        raise ValueError("Invalid credential")
    return subject


def get_verified_subject(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing authentication credential",
            headers={"WWW-Authenticate": "Bearer"},
        )
    auth_url = get_settings().neon_auth_base_url
    if auth_url is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured",
        )
    try:
        return verify_neon_token(credentials.credentials, auth_url)
    except AuthServiceUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing authentication credential",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
