import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_database_url_requires_psycopg_postgresql() -> None:
    with pytest.raises(ValidationError, match="postgresql\\+psycopg"):
        Settings(database_url="sqlite:///finance.db")


def test_invalid_environment_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(app_env="unknown", database_url="postgresql+psycopg://localhost/finance")  # type: ignore[arg-type]


def test_production_requires_neon_auth_url() -> None:
    with pytest.raises(ValidationError, match="NEON_AUTH_BASE_URL"):
        Settings(app_env="production", database_url="postgresql+psycopg://localhost/finance")


def test_neon_auth_url_must_be_https() -> None:
    with pytest.raises(ValidationError, match="HTTPS"):
        Settings(
            database_url="postgresql+psycopg://localhost/finance",
            neon_auth_base_url="http://auth.example.test/neondb/auth",
        )


def test_request_limit_must_exceed_import_file_limit() -> None:
    with pytest.raises(ValidationError, match="REQUEST_MAX_BYTES"):
        Settings(
            database_url="postgresql+psycopg://localhost/finance",
            import_max_bytes=100,
            request_max_bytes=100,
        )
