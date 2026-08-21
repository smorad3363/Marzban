from contextlib import contextmanager
from datetime import datetime, timedelta

import pytest
import sqlalchemy as sa
from fastapi import BackgroundTasks, HTTPException
from sqlalchemy.orm import sessionmaker
from starlette.requests import Request

from app import xray
from app.db import crud
from app.db.base import Base
from app.db.models import (
    Admin as DBAdmin,
    DeviceLimitSettings,
    DeviceLimitUserState,
    NextPlan,
    Proxy,
    User,
)
from app.device_limit.engine import DeviceLimitEngine
from app.jobs import review_users
from app.models import user as user_models
from app.models.admin import Admin as APIAdmin
from app.models.proxy import ProxyTypes
from app.models.user import UserModify, UserStatus
from app.routers.user import (
    active_next_plan,
    modify_user,
    reset_user_data_usage as reset_user_data_usage_route,
)


@pytest.fixture()
def db(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'user-status-integrity.sqlite3'}")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture(autouse=True)
def deterministic_user_response(monkeypatch):
    monkeypatch.setattr(
        user_models,
        "generate_v2ray_links",
        lambda *_args, **_kwargs: ["test-link"],
    )
    monkeypatch.setattr(
        user_models,
        "create_subscription_token",
        lambda _username: "test-token",
    )


def _request(method: str, path: str) -> Request:
    return Request(
        {
            "type": "http",
            "method": method,
            "path": path,
            "headers": [],
            "client": ("127.0.0.1", 1234),
        }
    )


def _admin(db) -> DBAdmin:
    admin = DBAdmin(username="status-admin", hashed_password="x", is_sudo=True)
    db.add(admin)
    db.commit()
    return admin


def _user(db, admin: DBAdmin, username: str, status: UserStatus) -> User:
    user = User(
        username=username,
        admin=admin,
        status=status,
        used_traffic=4096,
        proxies=[Proxy(type=ProxyTypes.VLESS, settings={})],
    )
    db.add(user)
    db.commit()
    return user


def _has_background_task(background: BackgroundTasks, function) -> bool:
    return any(task.func is function for task in background.tasks)


@pytest.mark.parametrize(
    ("starting_status", "expected_status", "queues_xray_add"),
    [
        (UserStatus.active, UserStatus.active, True),
        (UserStatus.disabled, UserStatus.disabled, False),
        (UserStatus.expired, UserStatus.expired, False),
        (UserStatus.on_hold, UserStatus.on_hold, True),
    ],
)
def test_single_usage_reset_preserves_status_and_xray_contract(
    db,
    starting_status,
    expected_status,
    queues_xray_add,
):
    admin = _admin(db)
    user = _user(db, admin, f"reset-{starting_status.value}", starting_status)
    background = BackgroundTasks()

    reset_user_data_usage_route(
        request=_request("POST", f"/api/user/{user.username}/reset"),
        bg=background,
        db=db,
        dbuser=user,
        admin=APIAdmin.model_validate(admin),
    )

    db.refresh(user)
    assert user.used_traffic == 0
    assert user.status == expected_status
    assert _has_background_task(background, xray.operations.add_user) is queues_xray_add


def test_bulk_usage_reset_preserves_non_active_statuses_without_xray_add(db, monkeypatch):
    admin = _admin(db)
    users = {
        status: _user(db, admin, f"bulk-{status.value}", status)
        for status in (
            UserStatus.active,
            UserStatus.disabled,
            UserStatus.expired,
            UserStatus.on_hold,
        )
    }
    added = []
    monkeypatch.setattr(xray.operations, "add_user", added.append)

    crud.reset_all_users_data_usage(db, admin=admin)

    for status, user in users.items():
        db.refresh(user)
        assert user.used_traffic == 0
        assert user.status == status
    assert added == []


def test_manual_disable_during_temporary_penalty_survives_release(db, monkeypatch):
    admin = _admin(db)
    penalty_at = datetime.utcnow() - timedelta(minutes=5)
    user = _user(db, admin, "manual-lock", UserStatus.disabled)
    user.last_status_change = penalty_at
    settings = DeviceLimitSettings(id=1, enabled=True)
    state = DeviceLimitUserState(
        user=user,
        penalty_status="temporarily_disabled",
        blocked_until=penalty_at + timedelta(seconds=30),
        status_before_penalty=UserStatus.active.value,
        updated_at=penalty_at,
    )
    db.add_all([settings, state])
    db.commit()

    crud.update_user(db, user, UserModify(status=UserStatus.disabled))
    added = []
    monkeypatch.setattr(xray.operations, "add_user", added.append)

    DeviceLimitEngine()._release_due_penalties(db, settings)

    db.refresh(user)
    db.refresh(state)
    assert user.status == UserStatus.disabled
    assert state.penalty_status == "clear"
    assert state.blocked_until is None
    assert added == []


def test_temporary_penalty_release_restores_engine_disabled_user(db, monkeypatch):
    admin = _admin(db)
    penalty_at = datetime.utcnow() - timedelta(minutes=5)
    user = _user(db, admin, "penalty-release", UserStatus.disabled)
    user.last_status_change = penalty_at
    settings = DeviceLimitSettings(id=1, enabled=True)
    state = DeviceLimitUserState(
        user=user,
        penalty_status="temporarily_disabled",
        blocked_until=penalty_at + timedelta(seconds=30),
        status_before_penalty=UserStatus.active.value,
        updated_at=penalty_at,
    )
    db.add_all([settings, state])
    db.commit()
    added = []
    monkeypatch.setattr(xray.operations, "add_user", added.append)

    DeviceLimitEngine()._release_due_penalties(db, settings)

    db.refresh(user)
    assert user.status == UserStatus.active
    assert added == [user]


def test_explicit_authorized_activation_still_updates_xray(db):
    admin = _admin(db)
    user = _user(db, admin, "explicit-activate", UserStatus.disabled)
    background = BackgroundTasks()

    response = modify_user(
        request=_request("PUT", f"/api/user/{user.username}"),
        modified_user=UserModify(status=UserStatus.active),
        bg=background,
        db=db,
        dbuser=user,
        admin=APIAdmin.model_validate(admin),
    )

    db.refresh(user)
    assert response.status == UserStatus.active
    assert user.status == UserStatus.active
    assert _has_background_task(background, xray.operations.update_user_by_id)


def test_disabled_user_is_not_eligible_for_automatic_next_plan_activation(db, monkeypatch):
    admin = _admin(db)
    user = _user(db, admin, "disabled-next-plan", UserStatus.disabled)
    user.data_limit = 1024
    user.used_traffic = 1024
    user.expire = int((datetime.utcnow() - timedelta(minutes=1)).timestamp())
    user.next_plan = NextPlan(data_limit=2048, expire=None, fire_on_either=True)
    db.commit()

    @contextmanager
    def current_db():
        yield db

    monkeypatch.setattr(review_users, "GetDB", current_db)
    monkeypatch.setattr(
        review_users.xray.operations,
        "update_user",
        lambda _user: pytest.fail("disabled user was re-added to Xray"),
    )
    monkeypatch.setattr(
        review_users.xray.operations,
        "remove_user",
        lambda _user: pytest.fail("disabled user entered automatic status review"),
    )

    review_users.review()

    db.refresh(user)
    assert user.status == UserStatus.disabled
    assert user.next_plan is not None
    assert user.used_traffic == 1024


def test_active_next_plan_is_an_explicit_activation(db):
    admin = _admin(db)
    user = _user(db, admin, "explicit-next-plan", UserStatus.disabled)
    user.data_limit = 1024
    user.next_plan = NextPlan(data_limit=2048, expire=None, fire_on_either=True)
    db.commit()
    background = BackgroundTasks()

    response = active_next_plan(
        request=_request("POST", f"/api/user/{user.username}/active-next"),
        bg=background,
        db=db,
        dbuser=user,
        admin=APIAdmin.model_validate(admin),
    )

    db.refresh(user)
    assert response.status == UserStatus.active
    assert user.status == UserStatus.active
    assert user.data_limit == 2048
    assert user.next_plan is None
    assert _has_background_task(background, xray.operations.add_user)


def test_active_next_plan_without_plan_fails_before_reset(db, monkeypatch):
    admin = _admin(db)
    user = _user(db, admin, "no-next-plan", UserStatus.disabled)
    background = BackgroundTasks()
    monkeypatch.setattr(
        crud,
        "reset_user_by_next",
        lambda *_args, **_kwargs: pytest.fail("reset ran without a next plan"),
    )

    with pytest.raises(HTTPException) as exc_info:
        active_next_plan(
            request=_request("POST", f"/api/user/{user.username}/active-next"),
            bg=background,
            db=db,
            dbuser=user,
            admin=APIAdmin.model_validate(admin),
        )

    assert exc_info.value.status_code == 404
    assert user.status == UserStatus.disabled
    assert background.tasks == []
