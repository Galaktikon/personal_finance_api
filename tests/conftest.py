import os

os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://finance:finance_local_only@localhost:5432/finance"
)
os.environ.setdefault("APP_ENV", "test")
