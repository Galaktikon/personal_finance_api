from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_session
from app.models import ImportJob, ImportRecord, UserProfile
from app.repositories.finance import owned_account
from app.schemas.imports import ImportJobDetail, ImportJobOut, ImportPreviewOut, ImportRecordOut
from app.services.identity import get_current_user, get_existing_user
from app.services.import_service import (
    ImportInputError,
    SourceFormat,
    parse_file,
    process_rows,
    request_digest,
)

router = APIRouter(prefix="/imports", tags=["imports"])
SessionDep = Annotated[Session, Depends(get_session)]
UserDep = Annotated[UserProfile, Depends(get_current_user)]
ExistingUserDep = Annotated[UserProfile, Depends(get_existing_user)]
FormatForm = Annotated[Literal["csv", "json"], Form()]
AccountForm = Annotated[UUID, Form()]
SourceForm = Annotated[str, Form(min_length=1, max_length=120)]
FilePart = Annotated[UploadFile, File()]


def read_upload(file: UploadFile, source_format: SourceFormat) -> bytes:
    settings = get_settings()
    filename = (file.filename or "").lower()
    if not filename.endswith(f".{source_format}"):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "File extension does not match format"
        )
    allowed_mime = {
        "csv": {"text/csv", "text/plain", "application/vnd.ms-excel", "application/octet-stream"},
        "json": {"application/json", "text/json", "application/octet-stream"},
    }
    if file.content_type not in allowed_mime[source_format]:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Unsupported file content type")
    content = file.file.read(settings.import_max_bytes + 1)
    if len(content) > settings.import_max_bytes:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "File exceeds size limit")
    if not content:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "File is empty")
    return content


def normalize_source(source_identifier: str) -> str:
    source = " ".join(source_identifier.split()).casefold()
    if not source:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Source identifier is required")
    return source


def parsed_rows(content: bytes, source_format: SourceFormat) -> list[dict[str, object]]:
    try:
        return parse_file(content, source_format, get_settings().import_max_rows)
    except ImportInputError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc


def job_detail(session: Session, job: ImportJob) -> ImportJobDetail:
    records = session.scalars(
        select(ImportRecord)
        .where(ImportRecord.import_job_id == job.id, ImportRecord.user_id == job.user_id)
        .order_by(ImportRecord.row_number)
    )
    return ImportJobDetail(
        **ImportJobOut.model_validate(job).model_dump(),
        rows=[ImportRecordOut.model_validate(record) for record in records],
    )


@router.post("/preview", response_model=ImportPreviewOut)
def preview_import(
    session: SessionDep,
    user: ExistingUserDep,
    account_id: AccountForm,
    source_identifier: SourceForm,
    source_format: FormatForm,
    file: FilePart,
) -> ImportPreviewOut:
    account = owned_account(session, user.id, account_id)
    if not account.is_active:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Account is inactive")
    source = normalize_source(source_identifier)
    content = read_upload(file, source_format)
    return process_rows(session, user.id, account, source, parsed_rows(content, source_format))


@router.post("", response_model=ImportJobDetail, status_code=status.HTTP_201_CREATED)
def commit_import(
    response: Response,
    session: SessionDep,
    user: UserDep,
    account_id: AccountForm,
    source_identifier: SourceForm,
    source_format: FormatForm,
    file: FilePart,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
) -> ImportJobDetail:
    account = owned_account(session, user.id, account_id)
    if not account.is_active:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Account is inactive")
    source = normalize_source(source_identifier)
    key = idempotency_key.strip()
    if not key:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Idempotency key is required")
    content = read_upload(file, source_format)
    digest = request_digest(content, account_id, source, source_format)
    existing = session.scalar(
        select(ImportJob).where(ImportJob.user_id == user.id, ImportJob.idempotency_key == key)
    )
    if existing is not None:
        if existing.content_digest != digest:
            raise HTTPException(status.HTTP_409_CONFLICT, "Idempotency key conflicts with content")
        response.status_code = status.HTTP_200_OK
        return job_detail(session, existing)
    rows = parsed_rows(content, source_format)
    job = ImportJob(
        user_id=user.id,
        source_format=source_format,
        status="processing",
        content_digest=digest,
        idempotency_key=key,
        started_at=datetime.now(UTC),
    )
    try:
        session.add(job)
        session.flush()
        process_rows(session, user.id, account, source, rows, job)
        session.commit()
    except SQLAlchemyError as exc:
        session.rollback()
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "Import could not be saved"
        ) from exc
    return job_detail(session, job)


@router.get("", response_model=list[ImportJobOut])
def list_imports(
    session: SessionDep,
    user: UserDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ImportJob]:
    return list(
        session.scalars(
            select(ImportJob)
            .where(ImportJob.user_id == user.id)
            .order_by(ImportJob.started_at.desc(), ImportJob.id)
            .limit(limit)
            .offset(offset)
        )
    )


@router.get("/{import_id}", response_model=ImportJobDetail)
def get_import(import_id: UUID, session: SessionDep, user: UserDep) -> ImportJobDetail:
    job = session.scalar(
        select(ImportJob).where(ImportJob.id == import_id, ImportJob.user_id == user.id)
    )
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Import not found")
    return job_detail(session, job)
