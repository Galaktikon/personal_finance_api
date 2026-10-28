"""Apply all migrations to a temporary empty PostgreSQL database and check readiness."""

import os
import subprocess
import sys
from uuid import uuid4

import psycopg
from fastapi.testclient import TestClient
from psycopg import sql
from sqlalchemy.engine import make_url

from app.core.config import get_settings
from app.db.session import get_engine
from app.main import app


def main() -> None:
    source_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not source_url:
        raise SystemExit("Set TEST_DATABASE_URL or DATABASE_URL to a local PostgreSQL URL")
    url = make_url(source_url)
    if url.drivername != "postgresql+psycopg":
        raise SystemExit("A postgresql+psycopg URL is required")
    if url.host not in {"localhost", "127.0.0.1", "::1"}:
        raise SystemExit("Clean migration probe requires local PostgreSQL")
    name = f"finance_phase6_{uuid4().hex[:10]}"
    admin_url = url.set(drivername="postgresql", database="postgres").render_as_string(
        hide_password=False
    )
    temporary_url = url.set(database=name).render_as_string(hide_password=False)
    env = {**os.environ, "DATABASE_URL": temporary_url, "APP_ENV": "test"}
    with psycopg.connect(admin_url, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
        try:
            for command in ("upgrade", "check"):
                args = [sys.executable, "-m", "alembic", command]
                if command == "upgrade":
                    args.append("head")
                subprocess.run(args, env=env, check=True)
            original_url = os.environ.get("DATABASE_URL")
            original_env = os.environ.get("APP_ENV")
            os.environ["DATABASE_URL"] = temporary_url
            os.environ["APP_ENV"] = "test"
            get_settings.cache_clear()
            get_engine.cache_clear()
            try:
                with TestClient(app) as client:
                    assert client.get("/health/live").status_code == 200
                    assert client.get("/health/ready").status_code == 200
            finally:
                get_engine().dispose()
                get_engine.cache_clear()
                get_settings.cache_clear()
                if original_url is None:
                    os.environ.pop("DATABASE_URL", None)
                else:
                    os.environ["DATABASE_URL"] = original_url
                if original_env is None:
                    os.environ.pop("APP_ENV", None)
                else:
                    os.environ["APP_ENV"] = original_env
            print("Clean migration, schema check, and health probes passed")
        finally:
            admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))


if __name__ == "__main__":
    main()
