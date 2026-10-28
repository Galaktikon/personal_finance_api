from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.common import commit_or_unprocessable
from app.db.session import get_session
from app.models import Category, UserProfile
from app.repositories.finance import owned_category, visible_category
from app.schemas.finance import CategoryCreate, CategoryOut, CategoryPatch
from app.services.identity import get_current_user

router = APIRouter(prefix="/categories", tags=["categories"])
SessionDep = Annotated[Session, Depends(get_session)]
UserDep = Annotated[UserProfile, Depends(get_current_user)]


def category_out(category: Category) -> CategoryOut:
    return CategoryOut.model_validate(category).model_copy(
        update={"is_system": category.user_id is None}
    )


def check_parent(session: Session, user_id: UUID, parent_id: UUID | None, kind: str) -> None:
    if parent_id is None:
        return
    parent = visible_category(session, user_id, parent_id)
    if not parent.is_active or parent.kind != kind:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Invalid parent category")


@router.get("", response_model=list[CategoryOut])
def list_categories(
    session: SessionDep,
    user: UserDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[CategoryOut]:
    query = select(Category).where((Category.user_id == user.id) | (Category.user_id.is_(None)))
    categories = session.scalars(
        query.order_by(Category.name, Category.id).limit(limit).offset(offset)
    )
    return [category_out(category) for category in categories]


@router.post("", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(body: CategoryCreate, session: SessionDep, user: UserDep) -> CategoryOut:
    check_parent(session, user.id, body.parent_category_id, body.kind)
    category = Category(user_id=user.id, **body.model_dump())
    session.add(category)
    commit_or_unprocessable(session)
    return category_out(category)


@router.patch("/{category_id}", response_model=CategoryOut)
def update_category(
    category_id: UUID, body: CategoryPatch, session: SessionDep, user: UserDep
) -> CategoryOut:
    category = owned_category(session, user.id, category_id)
    changes = body.model_dump(exclude_unset=True)
    if "parent_category_id" in changes:
        check_parent(session, user.id, body.parent_category_id, category.kind)
    for key, value in changes.items():
        if value is None and key != "parent_category_id":
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"{key} cannot be null")
        setattr(category, key, value)
    commit_or_unprocessable(session)
    return category_out(category)
