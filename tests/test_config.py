import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_database_url_requires_psycopg_postgresql() -> None:
    with pytest.raises(ValidationError, match="postgresql\\+psycopg"):
        Settings(database_url="sqlite:///finance.db")


def test_invalid_environment_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(app_env="unknown", database_url="postgresql+psycopg://localhost/finance")  # type: ignore[arg-type]
