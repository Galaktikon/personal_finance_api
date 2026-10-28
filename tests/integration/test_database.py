import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.main import app


@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL is not set")
def test_postgresql_connection() -> None:
    url = os.environ["TEST_DATABASE_URL"]
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            assert connection.execute(text("SELECT 1")).scalar_one() == 1
            version = connection.execute(text("SELECT version_num FROM alembic_version"))
            assert version.scalar_one() == "0001_foundation"
    finally:
        engine.dispose()


@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL is not set")
def test_readiness_with_postgresql() -> None:
    with TestClient(app) as client:
        response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
