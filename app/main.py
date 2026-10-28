from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.accounts import router as accounts_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.categories import router as categories_router
from app.api.v1.categorization_rules import router as rules_router
from app.api.v1.demo import router as demo_router
from app.api.v1.imports import router as imports_router
from app.api.v1.transactions import router as transactions_router
from app.api.v1.transfers import router as transfers_router
from app.core.config import get_settings
from app.core.http_hardening import SafeRequestMiddleware
from app.db.session import database_is_ready


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    get_settings()  # Fail fast on missing or invalid configuration.
    yield


app = FastAPI(title="Personal Finance Analytics API", version="0.1.0", lifespan=lifespan)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATIC_ROOT = Path(__file__).resolve().parent / "static"


@app.exception_handler(RequestValidationError)
def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    # Pydantic's default response includes submitted values and possibly user-supplied keys.
    errors = [{"type": error["type"]} for error in exc.errors()]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, content={"detail": errors}
    )


app.add_middleware(SafeRequestMiddleware)
app.mount("/demo-assets", StaticFiles(directory=STATIC_ROOT), name="demo-assets")
app.include_router(demo_router, prefix="/api/v1")
app.include_router(accounts_router, prefix="/api/v1")
app.include_router(transactions_router, prefix="/api/v1")
app.include_router(categories_router, prefix="/api/v1")
app.include_router(rules_router, prefix="/api/v1")
app.include_router(transfers_router, prefix="/api/v1")
app.include_router(imports_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")


@app.get("/", include_in_schema=False)
def demo_page() -> FileResponse:
    return FileResponse(STATIC_ROOT / "index.html", media_type="text/html")


@app.get("/samples/demo_transactions.csv", include_in_schema=False)
def demo_sample() -> FileResponse:
    return FileResponse(
        PROJECT_ROOT / "sample_data" / "demo_transactions.csv",
        media_type="text/csv",
        filename="demo_transactions.csv",
    )


@app.get("/samples/mixed_results.csv", include_in_schema=False)
def mixed_sample() -> FileResponse:
    return FileResponse(
        PROJECT_ROOT / "sample_data" / "mixed_results.csv",
        media_type="text/csv",
        filename="mixed_results.csv",
    )


@app.get("/health/live", tags=["health"])
def liveness() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready", tags=["health"])
def readiness(response: Response) -> dict[str, str]:
    if not database_is_ready():
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unavailable"}
    return {"status": "ok"}
