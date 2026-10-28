from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from app import main


def test_liveness_does_not_query_database(monkeypatch: MonkeyPatch) -> None:
    # Liveness must remain available even when PostgreSQL is down.
    monkeypatch.setattr(main, "database_is_ready", lambda: False)
    with TestClient(main.app) as client:
        response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_when_database_available(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(main, "database_is_ready", lambda: True)
    with TestClient(main.app) as client:
        response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_when_database_unavailable(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(main, "database_is_ready", lambda: False)
    with TestClient(main.app) as client:
        response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}
