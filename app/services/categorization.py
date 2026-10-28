from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CategorizationRule, Category


def normalize_text(value: str | None) -> str:
    return " ".join((value or "").split()).casefold()


def select_category(
    session: Session,
    user_id: UUID,
    kind: str,
    description: str,
    merchant: str | None,
) -> tuple[UUID | None, UUID | None, str]:
    expected_kind = "income" if kind == "income" else "expense"
    rules: Iterable[tuple[CategorizationRule, Category]] = session.execute(
        select(CategorizationRule, Category)
        .join(Category, CategorizationRule.category_id == Category.id)
        .where(
            CategorizationRule.is_active.is_(True),
            Category.is_active.is_(True),
            Category.kind == expected_kind,
            (CategorizationRule.user_id == user_id) | (CategorizationRule.user_id.is_(None)),
        )
    ).all()
    ordered = sorted(
        rules,
        key=lambda pair: (
            pair[0].user_id is None,
            pair[0].priority,
            str(pair[0].id),
        ),
    )
    targets = (normalize_text(description), normalize_text(merchant))
    for rule, category in ordered:
        condition = normalize_text(rule.condition_value)
        if not condition:
            continue
        if rule.condition_type == "contains" and any(condition in target for target in targets):
            return category.id, rule.id, "system_rule" if rule.user_id is None else "user_rule"
        if rule.condition_type == "equals" and condition in targets:
            return category.id, rule.id, "system_rule" if rule.user_id is None else "user_rule"
    return None, None, "uncategorized"
