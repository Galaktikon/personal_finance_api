from typing import Annotated
from uuid import uuid4

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.security import get_verified_subject
from app.db.session import get_session
from app.models import UserProfile


def get_current_user(
    subject: Annotated[str, Depends(get_verified_subject)],
    session: Annotated[Session, Depends(get_session)],
) -> UserProfile:
    profile = session.scalar(select(UserProfile).where(UserProfile.auth_subject_id == subject))
    if profile is not None:
        return profile
    statement = (
        insert(UserProfile)
        .values(id=uuid4(), auth_subject_id=subject)
        .on_conflict_do_nothing(index_elements=[UserProfile.auth_subject_id])
    )
    session.execute(statement)
    session.commit()
    return session.scalars(select(UserProfile).where(UserProfile.auth_subject_id == subject)).one()


def get_existing_user(
    subject: Annotated[str, Depends(get_verified_subject)],
    session: Annotated[Session, Depends(get_session)],
) -> UserProfile:
    """Read-only identity resolution for import previews."""
    profile = session.scalar(select(UserProfile).where(UserProfile.auth_subject_id == subject))
    if profile is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Account not found")
    return profile
