import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import crud
from app.db.base import Base
from app.models.admin import (
    AdminCreate,
    AdminModify,
    MarzhelpAdminPolicy,
)


@pytest.fixture()
def session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'admin-management.sqlite3'}")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine, expire_on_commit=False)()
    yield db
    db.close()
    engine.dispose()


def test_create_admin_with_policy_in_one_transaction(session):
    admin = crud.create_admin(
        session,
        AdminCreate(username="reseller", password="secret", is_sudo=False),
        commit=False,
    )
    policy = crud.upsert_marzhelp_admin_policy(
        session,
        admin.id,
        MarzhelpAdminPolicy(
            total_traffic=100 * 1024**3,
            user_limit=20,
            max_users=12,
            max_user_duration_days=31,
            prevent_unlimited_traffic=True,
        ),
        commit=False,
    )
    session.commit()

    assert admin.username == "reseller"
    assert policy.user_limit == 20
    assert policy.max_users == 12
    assert policy.max_user_duration_days == 31
    assert policy.prevent_unlimited_traffic is True


def test_update_admin_can_demote_and_clear_optional_channels(session):
    admin = crud.create_admin(
        session,
        AdminCreate(
            username="operator",
            password="secret",
            is_sudo=True,
            telegram_id=1234,
            discord_webhook="https://discord.com/api/webhooks/example",
        ),
    )

    updated = crud.update_admin(
        session,
        admin,
        AdminModify(is_sudo=False, telegram_id=None, discord_webhook=None),
    )

    assert updated.is_sudo is False
    assert updated.telegram_id is None
    assert updated.discord_webhook is None


def test_management_list_is_stable_and_counted(session):
    for username in ("zeta", "alpha", "middle"):
        crud.create_admin(
            session,
            AdminCreate(username=username, password="secret", is_sudo=False),
        )

    admins, total = crud.get_admins_with_count(session, offset=0, limit=2)

    assert total == 3
    assert [admin.username for admin in admins] == ["alpha", "middle"]


def test_policy_rejects_negative_or_unknown_volume_rules():
    with pytest.raises(ValidationError):
        MarzhelpAdminPolicy(user_limit=-1)
    with pytest.raises(ValidationError):
        MarzhelpAdminPolicy(max_users=0)
    with pytest.raises(ValidationError):
        MarzhelpAdminPolicy(calculate_volume="invalid")


def test_selected_permission_modes_require_values():
    with pytest.raises(ValidationError):
        MarzhelpAdminPolicy(all_inbounds=False)
    with pytest.raises(ValidationError):
        MarzhelpAdminPolicy(all_user_limits=False)
