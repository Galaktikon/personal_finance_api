from pathlib import Path

from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from app import main
from scripts.smoke_deployment import check_deployment

app = main.app

SAMPLES = Path(__file__).resolve().parents[2] / "sample_data"


def test_frontend_and_downloadable_samples() -> None:
    with TestClient(app) as client:
        page = client.get("/")
        script = client.get("/demo-assets/app.js")
        sample = client.get("/samples/demo_transactions.csv")
        mixed = client.get("/samples/mixed_results.csv")
    assert page.status_code == 200
    assert "No account or sign-in needed" in page.text
    assert script.status_code == 200
    assert sample.content == (SAMPLES / "demo_transactions.csv").read_bytes()
    assert mixed.content == (SAMPLES / "mixed_results.csv").read_bytes()
    assert "attachment" in sample.headers["content-disposition"]


def test_anonymous_csv_processing_and_pending_exclusion() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/demo/process",
            files={
                "file": (
                    "demo_transactions.csv",
                    (SAMPLES / "demo_transactions.csv").read_bytes(),
                    "text/csv",
                )
            },
        )
        protected = client.get("/api/v1/accounts")
    assert response.status_code == 200
    result = response.json()
    assert (result["total_rows"], result["accepted_count"], result["failed_count"]) == (5, 5, 0)
    assert (result["posted_count"], result["pending_count"]) == (4, 1)
    assert result["gross_income"] == "2500.00"
    assert result["gross_expenses"] == "130.00"
    assert result["refunds"] == "20.00"
    assert result["net_spending"] == "110.00"
    assert result["net_cash_flow"] == "2390.00"
    assert protected.status_code == 401


def test_anonymous_csv_reports_invalid_rows_without_echoing_values() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/demo/process",
            files={
                "file": (
                    "mixed_results.csv",
                    (SAMPLES / "mixed_results.csv").read_bytes(),
                    "text/csv",
                )
            },
        )
    assert response.status_code == 200
    result = response.json()
    assert (result["accepted_count"], result["failed_count"]) == (4, 1)
    assert result["rows"][4]["error_code"] == "invalid_row"
    assert "Synthetic invalid amount" not in response.text
    assert result["net_cash_flow"] == "1772.75"


def test_demo_rejects_non_csv_and_bad_headers() -> None:
    with TestClient(app) as client:
        wrong_extension = client.post(
            "/api/v1/demo/process", files={"file": ("demo.txt", b"hello", "text/csv")}
        )
        bad_headers = client.post(
            "/api/v1/demo/process", files={"file": ("demo.csv", b"amount\n12.00\n", "text/csv")}
        )
    assert wrong_extension.status_code == 422
    assert bad_headers.status_code == 422


def test_deployment_smoke_includes_public_demo(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(main, "database_is_ready", lambda: True)
    with TestClient(app) as client:
        check_deployment(client)
