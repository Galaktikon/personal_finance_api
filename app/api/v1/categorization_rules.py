from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.common import commit_or_unprocessable
from app.db.session import get_session
from app.models import CategorizationRule, UserProfile
from app.repositories.finance import visible_category
from app.schemas.rules import RuleCreate, RuleOut, RulePatch
from app.services.identity import get_current_user

router = APIRouter(prefix="/categorization-rules", tags=["categorization rules"])
SessionDep = Annotated[Session, Depends(get_session)]
UserDep = Annotated[UserProfile, Depends(get_current_user)]


def rule_out(rule: CategorizationRule) -> RuleOut:
    return RuleOut.model_validate(rule).model_copy(update={"is_system": rule.user_id is None})


def owned_rule(session: Session, user_id: UUID, rule_id: UUID) -> CategorizationRule:
    rule = session.scalar(
        select(CategorizationRule).where(
            CategorizationRule.id == rule_id, CategorizationRule.user_id == user_id
        )
    )
    if rule is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rule not found")
    return rule


def check_rule_category(session: Session, user_id: UUID, category_id: UUID) -> None:
    category = visible_category(session, user_id, category_id)
    if not category.is_active:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Category is inactive")


@router.get("", response_model=list[RuleOut])
def list_rules(
    session: SessionDep,
    user: UserDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[RuleOut]:
    query = select(CategorizationRule).where(
        (CategorizationRule.user_id == user.id) | (CategorizationRule.user_id.is_(None))
    )
    rows = session.scalars(
        query.order_by(CategorizationRule.priority, CategorizationRule.id)
        .limit(limit)
        .offset(offset)
    )
    return [rule_out(row) for row in rows]


@router.post("", response_model=RuleOut, status_code=status.HTTP_201_CREATED)
def create_rule(body: RuleCreate, session: SessionDep, user: UserDep) -> RuleOut:
    check_rule_category(session, user.id, body.category_id)
    rule = CategorizationRule(user_id=user.id, **body.model_dump())
    session.add(rule)
    commit_or_unprocessable(session)
    return rule_out(rule)


@router.patch("/{rule_id}", response_model=RuleOut)
def update_rule(rule_id: UUID, body: RulePatch, session: SessionDep, user: UserDep) -> RuleOut:
    rule = owned_rule(session, user.id, rule_id)
    changes = body.model_dump(exclude_unset=True)
    if "category_id" in changes and changes["category_id"] is not None:
        check_rule_category(session, user.id, changes["category_id"])
    for key, value in changes.items():
        if value is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"{key} cannot be null")
        setattr(rule, key, value)
    commit_or_unprocessable(session)
    return rule_out(rule)


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_rule(rule_id: UUID, session: SessionDep, user: UserDep) -> Response:
    rule = owned_rule(session, user.id, rule_id)
    rule.is_active = False
    commit_or_unprocessable(session)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
