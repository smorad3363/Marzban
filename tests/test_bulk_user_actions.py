import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import crud
from app.db.base import Base
from app.db.models import Admin, User
from app.models.user import (
    BulkUserActionRequest,
    BulkUserOperation,
    UserStatus,
)


@pytest.fixture()
def session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'bulk-users.sqlite3'}")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine, expire_on_commit=False)()
    yield db
    db.close()
    engine.dispose()


def test_bulk_amount_is_required_only_for_numeric_operations():
    with pytest.raises(ValidationError):
        BulkUserActionRequest(
            usernames=["user-one"], operation=BulkUserOperation.add_days
        )

    request = BulkUserActionRequest(
        usernames=["user-one"],
        operation=BulkUserOperation.add_data,
        amount=1024,
    )
    assert request.amount == 1024

    status_request = BulkUserActionRequest(
        usernames=["user-one"],
        operation=BulkUserOperation.activate,
        amount=20,
    )
    assert status_request.amount is None


def test_bulk_request_rejects_empty_selection():
    with pytest.raises(ValidationError):
        BulkUserActionRequest(usernames=[], operation=BulkUserOperation.delete)


def test_users_can_be_sorted_by_owner_admin(session):
    alpha = Admin(username="alpha-admin", hashed_password="x")
    zeta = Admin(username="zeta-admin", hashed_password="x")
    session.add_all([zeta, alpha])
    session.flush()
    session.add_all(
        [
            User(
                username="user-zeta",
                admin_id=zeta.id,
                status=UserStatus.active,
            ),
            User(
                username="user-alpha",
                admin_id=alpha.id,
                status=UserStatus.active,
            ),
        ]
    )
    session.commit()

    ascending = crud.get_users(
        session, sort=[crud.UsersSortingOptions.admin]
    )
    descending = crud.get_users(
        session, sort=[crud.UsersSortingOptions["-admin"]]
    )

    assert [user.username for user in ascending] == ["user-alpha", "user-zeta"]
    assert [user.username for user in descending] == ["user-zeta", "user-alpha"]
