"""Load the public synthetic demo file through the authenticated API."""

import argparse
import os
from pathlib import Path
from typing import Any

import httpx

DATA_FILE = Path(__file__).resolve().parents[1] / "sample_data" / "demo_transactions.csv"


def find_or_create(
    client: httpx.Client,
    route: str,
    name: str,
    body: dict[str, Any],
) -> dict[str, Any]:
    offset = 0
    while True:
        response = client.get(route, params={"limit": 100, "offset": offset})
        response.raise_for_status()
        items = response.json()
        for item in items:
            if (
                item["name"] == name
                and item.get("is_active", True)
                and not item.get("is_system", False)
            ):
                return item
        if len(items) < 100:
            break
        offset += 100
    response = client.post(route, json=body)
    response.raise_for_status()
    return response.json()


def run_demo(client: httpx.Client, data_file: Path = DATA_FILE) -> dict[str, Any]:
    account = find_or_create(
        client,
        "/api/v1/accounts",
        "Synthetic Demo Checking",
        {"name": "Synthetic Demo Checking", "type": "checking"},
    )
    food = find_or_create(
        client,
        "/api/v1/categories",
        "Synthetic Demo Food",
        {"name": "Synthetic Demo Food", "kind": "expense"},
    )
    find_or_create(
        client,
        "/api/v1/categorization-rules",
        "Synthetic Demo Market",
        {
            "name": "Synthetic Demo Market",
            "priority": 10,
            "condition_type": "contains",
            "condition_value": "market",
            "category_id": food["id"],
        },
    )
    with data_file.open("rb") as handle:
        response = client.post(
            "/api/v1/imports",
            data={
                "account_id": account["id"],
                "source_identifier": "synthetic-demo",
                "source_format": "csv",
            },
            files={"file": (data_file.name, handle, "text/csv")},
            headers={"Idempotency-Key": f"synthetic-demo-v1-{account['id']}"},
        )
    response.raise_for_status()
    summary = client.get("/api/v1/analytics/summary", params={"account_id": account["id"]})
    summary.raise_for_status()
    return {"account_id": account["id"], "import_id": response.json()["id"], **summary.json()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    token = os.getenv("DEMO_BEARER_TOKEN")
    if not token:
        parser.error("DEMO_BEARER_TOKEN is required")
    with httpx.Client(
        base_url=args.base_url.rstrip("/"),
        headers={"Authorization": f"Bearer {token}"},
        timeout=20,
    ) as client:
        result = run_demo(client)
    print(
        "Synthetic demo loaded: "
        f"gross income {result['gross_income']}, "
        f"gross expenses {result['gross_expenses']}, "
        f"refunds {result['refunds']}, "
        f"net cash flow {result['net_cash_flow']}"
    )


if __name__ == "__main__":
    main()
