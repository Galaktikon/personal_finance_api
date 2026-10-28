"""Check public health, OpenAPI, and optional authenticated access on a deployed API."""

import argparse
import os

import httpx

REQUIRED_PATHS = {
    "/api/v1/accounts",
    "/api/v1/transactions",
    "/api/v1/imports",
    "/api/v1/analytics/summary",
}


def check_deployment(client: httpx.Client, token: str | None = None) -> None:
    for path in ("/health/live", "/health/ready"):
        response = client.get(path)
        response.raise_for_status()
        if response.json() != {"status": "ok"}:
            raise RuntimeError(f"Unexpected health result at {path}")
    schema = client.get("/openapi.json")
    schema.raise_for_status()
    if not REQUIRED_PATHS <= set(schema.json()["paths"]):
        raise RuntimeError("OpenAPI is missing required routes")
    anonymous = client.get("/api/v1/accounts")
    if anonymous.status_code != 401:
        raise RuntimeError("Protected account route did not reject anonymous access")
    if token is not None:
        authenticated = client.get("/api/v1/accounts", headers={"Authorization": f"Bearer {token}"})
        authenticated.raise_for_status()
        if not isinstance(authenticated.json(), list):
            raise RuntimeError("Unexpected authenticated account response")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    args = parser.parse_args()
    with httpx.Client(base_url=args.base_url.rstrip("/"), timeout=30) as client:
        check_deployment(client, os.getenv("DEMO_BEARER_TOKEN"))
    print("Deployment health, OpenAPI, and access checks passed")


if __name__ == "__main__":
    main()
