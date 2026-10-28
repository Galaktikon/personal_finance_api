import os
from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Account, CategorizationRule, Category, Transaction, TransferLink, UserProfile

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL is not set"
)


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine(os.environ["TEST_DATABASE_URL"])
    with engine.connect() as connection:
        outer = connection.begin()
        with Session(connection) as db:
            yield db
        outer.rollback()
    engine.dispose()


def seed_owners(session: Session) -> tuple[UserProfile, UserProfile, Account, Account, Account]:
    alice = UserProfile(auth_subject_id="alice-test")
    bob = UserProfile(auth_subject_id="bob-test")
    session.add_all([alice, bob])
    session.flush()
    checking = Account(user_id=alice.id, name="Checking", type="checking")
    savings = Account(user_id=alice.id, name="Savings", type="savings")
    other = Account(user_id=bob.id, name="Other", type="checking")
    session.add_all([checking, savings, other])
    session.flush()
    return alice, bob, checking, savings, other


def make_transaction(
    user_id: UUID,
    account_id: UUID,
    amount: str = "-10.00",
    kind: str = "expense",
    category_id: UUID | None = None,
    category_source: str = "uncategorized",
) -> Transaction:
    return Transaction(
        user_id=user_id,
        account_id=account_id,
        transaction_date=date(2024, 2, 29),
        amount=Decimal(amount),
        currency="USD",
        description="Synthetic transaction",
        kind=kind,
        status="posted",
        category_id=category_id,
        category_source=category_source,
    )


def test_transaction_account_must_share_owner(session: Session) -> None:
    alice, _, _, _, other = seed_owners(session)
    with pytest.raises(IntegrityError), session.begin_nested():
        session.add(make_transaction(alice.id, other.id))
        session.flush()


def test_category_scope_allows_system_and_owner_only(session: Session) -> None:
    alice, bob, checking, _, _ = seed_owners(session)
    system = Category(name="Groceries", kind="expense", user_id=None)
    private = Category(name="Private", kind="expense", user_id=bob.id)
    session.add_all([system, private])
    session.flush()

    allowed = make_transaction(
        alice.id, checking.id, category_id=system.id, category_source="manual"
    )
    session.add(allowed)
    session.flush()

    with pytest.raises(IntegrityError), session.begin_nested():
        session.add(
            make_transaction(
                alice.id, checking.id, category_id=private.id, category_source="manual"
            )
        )
        session.flush()

    with pytest.raises(IntegrityError), session.begin_nested():
        session.add(
            Category(
                name="Invalid child",
                kind="expense",
                user_id=alice.id,
                parent_category_id=private.id,
            )
        )
        session.flush()

    income_category = Category(name="Salary", kind="income", user_id=alice.id)
    session.add(income_category)
    session.flush()
    with pytest.raises(IntegrityError), session.begin_nested():
        session.add(
            make_transaction(
                alice.id, checking.id, category_id=income_category.id, category_source="manual"
            )
        )
        session.flush()


def test_category_hierarchy_and_rules_respect_owner(session: Session) -> None:
    alice, bob, checking, _, _ = seed_owners(session)
    root = Category(name="Root", kind="expense", user_id=alice.id)
    system = Category(name="System", kind="expense", user_id=None)
    other = Category(name="Other", kind="expense", user_id=bob.id)
    session.add_all([root, system, other])
    session.flush()
    child = Category(name="Child", kind="expense", user_id=alice.id, parent_category_id=root.id)
    session.add(child)
    session.flush()

    with pytest.raises(IntegrityError), session.begin_nested():
        root.parent_category_id = child.id
        session.flush()
    session.refresh(root)

    allowed = CategorizationRule(
        user_id=alice.id,
        name="System category rule",
        priority=10,
        condition_type="contains",
        condition_value="STORE",
        category_id=system.id,
    )
    session.add(allowed)
    session.flush()
    categorized = make_transaction(
        alice.id, checking.id, category_id=system.id, category_source="user_rule"
    )
    categorized.categorization_rule_id = allowed.id
    session.add(categorized)
    session.flush()

    with pytest.raises(IntegrityError), session.begin_nested():
        mismatch = make_transaction(
            alice.id, checking.id, category_id=root.id, category_source="user_rule"
        )
        mismatch.categorization_rule_id = allowed.id
        session.add(mismatch)
        session.flush()
    with pytest.raises(IntegrityError), session.begin_nested():
        session.add(
            CategorizationRule(
                user_id=alice.id,
                name="Invalid rule",
                priority=10,
                condition_type="contains",
                condition_value="STORE",
                category_id=other.id,
            )
        )
        session.flush()
    with pytest.raises(IntegrityError), session.begin_nested():
        session.add(
            CategorizationRule(
                user_id=None,
                name="Invalid system rule",
                priority=10,
                condition_type="contains",
                condition_value="STORE",
                category_id=root.id,
            )
        )
        session.flush()


def test_transaction_sign_and_precision_are_enforced(session: Session) -> None:
    alice, _, checking, _, _ = seed_owners(session)
    with pytest.raises(ValueError, match="two fractional"):
        make_transaction(alice.id, checking.id, "-1.234")
    with pytest.raises(IntegrityError), session.begin_nested():
        session.add(make_transaction(alice.id, checking.id, "1.00", "expense"))
        session.flush()


def test_transfer_link_requires_same_owner_and_valid_pair(session: Session) -> None:
    alice, bob, checking, savings, other = seed_owners(session)
    source = make_transaction(alice.id, checking.id, "-25.00", "transfer_out")
    destination = make_transaction(alice.id, savings.id, "25.00", "transfer_in")
    bob_destination = make_transaction(bob.id, other.id, "25.00", "transfer_in")
    session.add_all([source, destination, bob_destination])
    session.flush()

    with pytest.raises(IntegrityError), session.begin_nested():
        session.add(
            TransferLink(
                user_id=alice.id,
                source_transaction_id=source.id,
                destination_transaction_id=bob_destination.id,
            )
        )
        session.flush()

    link = TransferLink(
        user_id=alice.id, source_transaction_id=source.id, destination_transaction_id=destination.id
    )
    session.add(link)
    session.flush()

    with pytest.raises(IntegrityError), session.begin_nested():
        source.amount = Decimal("-24.00")
        session.flush()
    session.refresh(source)
    assert source.amount == Decimal("-25.00")

    wrong_amount = make_transaction(alice.id, savings.id, "24.00", "transfer_in")
    session.add(wrong_amount)
    session.flush()
    with pytest.raises(IntegrityError), session.begin_nested():
        session.add(
            TransferLink(
                user_id=alice.id,
                source_transaction_id=source.id,
                destination_transaction_id=wrong_amount.id,
            )
        )
        session.flush()
