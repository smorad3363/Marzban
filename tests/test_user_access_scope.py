from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from inspect import signature
from types import SimpleNamespace

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
    AdminAuditLog,
    AdminHierarchy,
    AdminHierarchySettings,
    AdminBulkJobTarget,
    MarzhelpAccountingTransaction,
    MarzhelpAdminSettings,
    MarzhelpDeletedUser,
    AdminRole,
    NodeUserUsage,
    Proxy,
    SystemOwner,
    User,
)
from app.dependencies import get_expired_users_list, get_validated_user
from app.models.admin import Admin as APIAdmin
from app.models.bulk import BulkTargetScope, BulkUserJobCreateRequest
from app.models.proxy import ProxyTypes
from app.models import user as user_models
from app.models.user import (
    BulkUserActionRequest,
    BulkUserOperation,
    UserCreate,
    UserModify,
    UserStatus,
)
from app.routers.user import (
    active_next_plan,
    add_user,
    bulk_user_action,
    get_user,
    get_user_usage,
    get_users,
    get_users_usage,
    modify_user,
    remove_user,
    reset_user_data_usage,
    revoke_user_subscription,
    set_owner as set_user_owner,
)
from app.utils import bulk_operations, marzhelp_policy, report
from app.utils.audit import AuditLogService
from cli import user as cli_user


@pytest.fixture()
def db(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'user-access-scope.sqlite3'}")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture(autouse=True)
def unrestricted_inbounds(monkeypatch):
    monkeypatch.setattr(
        marzhelp_policy,
        "allowed_inbound_tags",
        lambda _db, _admin: None,
    )
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


def _utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _api_admin(admin: DBAdmin) -> APIAdmin:
    return APIAdmin.model_validate(admin)


def _list_users(db, admin: DBAdmin, owners=None) -> list[str]:
    response = get_users(
        offset=0,
        limit=50,
        username=None,
        search=None,
        owner=owners,
        status=None,
        sort=None,
        db=db,
        admin=_api_admin(admin),
    )
    return sorted(user.username for user in response["users"])


def _usage_total(db, admin: DBAdmin, owners=None) -> int:
    now = _utc_now_naive()
    response = get_users_usage(
        start=now - timedelta(days=1),
        end=now + timedelta(days=1),
        db=db,
        owner=owners,
        admin=_api_admin(admin),
    )
    return sum(item.used_traffic for item in response["usages"])


def _add_user_with_usage(db, username: str, admin: DBAdmin, traffic: int) -> User:
    user = User(
        username=username,
        admin=admin,
        status=UserStatus.active,
        proxies=[Proxy(type=ProxyTypes.VLESS, settings={})],
    )
    db.add(user)
    db.flush()
    db.add(
        NodeUserUsage(
            created_at=_utc_now_naive(),
            user_id=user.id,
            node_id=None,
            used_traffic=traffic,
        )
    )
    return user


def _seed_hierarchy_off(db):
    sudo = DBAdmin(username="sudo", hashed_password="x", is_sudo=True)
    admin_a = DBAdmin(username="admin-a", hashed_password="x", is_sudo=False)
    admin_b = DBAdmin(username="admin-b", hashed_password="x", is_sudo=False)
    db.add_all(
        [
            AdminHierarchySettings(id=1, enabled=False, max_depth=64),
            sudo,
            admin_a,
            admin_b,
        ]
    )
    db.flush()
    user_a = _add_user_with_usage(db, "user-a", admin_a, 11)
    user_b = _add_user_with_usage(db, "user-b", admin_b, 29)
    db.commit()
    return sudo, admin_a, admin_b, user_a, user_b


def _seed_hierarchy_on(db):
    db.add_all(
        [
            AdminRole(id=1, code="OWNER"),
            AdminRole(id=2, code="SUPER_ADMIN"),
            AdminRole(id=3, code="ADMIN"),
            AdminHierarchySettings(id=1, enabled=True, max_depth=64),
        ]
    )
    owner = DBAdmin(
        username="owner",
        hashed_password="x",
        is_sudo=True,
        role_id=1,
    )
    super_admin = DBAdmin(
        username="super-a",
        hashed_password="x",
        is_sudo=True,
        role_id=2,
        parent=owner,
    )
    child = DBAdmin(
        username="admin-a",
        hashed_password="x",
        is_sudo=False,
        role_id=3,
        parent=super_admin,
    )
    sibling = DBAdmin(
        username="admin-b",
        hashed_password="x",
        is_sudo=False,
        role_id=3,
        parent=owner,
    )
    db.add_all([owner, super_admin, child, sibling])
    db.flush()
    db.add(SystemOwner(id=1, admin_id=owner.id))
    db.add_all(
        [
            AdminHierarchy(ancestor_id=owner.id, descendant_id=owner.id, depth=0),
            AdminHierarchy(ancestor_id=owner.id, descendant_id=super_admin.id, depth=1),
            AdminHierarchy(ancestor_id=owner.id, descendant_id=child.id, depth=2),
            AdminHierarchy(ancestor_id=owner.id, descendant_id=sibling.id, depth=1),
            AdminHierarchy(ancestor_id=super_admin.id, descendant_id=super_admin.id, depth=0),
            AdminHierarchy(ancestor_id=super_admin.id, descendant_id=child.id, depth=1),
            AdminHierarchy(ancestor_id=child.id, descendant_id=child.id, depth=0),
            AdminHierarchy(ancestor_id=sibling.id, descendant_id=sibling.id, depth=0),
        ]
    )
    users = {
        "owner": _add_user_with_usage(db, "user-owner", owner, 1),
        "super": _add_user_with_usage(db, "user-super", super_admin, 2),
        "child": _add_user_with_usage(db, "user-child", child, 4),
        "sibling": _add_user_with_usage(db, "user-sibling", sibling, 8),
    }
    db.commit()
    return owner, super_admin, child, sibling, users


def _seed_credit_hierarchy(db):
    db.add_all(
        [
            AdminRole(id=1, code="OWNER"),
            AdminRole(id=2, code="SUPER_ADMIN"),
            AdminRole(id=3, code="ADMIN"),
            AdminHierarchySettings(id=1, enabled=True, max_depth=64),
        ]
    )
    owner = DBAdmin(
        username="credit-owner",
        hashed_password="x",
        is_sudo=True,
        role_id=1,
    )
    super_admin = DBAdmin(
        username="credit-super-a",
        hashed_password="x",
        is_sudo=True,
        role_id=2,
        parent=owner,
    )
    child = DBAdmin(
        username="credit-admin-b",
        hashed_password="x",
        role_id=3,
        parent=super_admin,
    )
    foreign = DBAdmin(
        username="credit-foreign",
        hashed_password="x",
        role_id=3,
        parent=owner,
    )
    db.add_all((owner, super_admin, child, foreign))
    db.flush()
    db.add(SystemOwner(id=1, admin_id=owner.id))
    db.add_all(
        [
            AdminHierarchy(ancestor_id=owner.id, descendant_id=owner.id, depth=0),
            AdminHierarchy(ancestor_id=owner.id, descendant_id=super_admin.id, depth=1),
            AdminHierarchy(ancestor_id=owner.id, descendant_id=child.id, depth=2),
            AdminHierarchy(ancestor_id=owner.id, descendant_id=foreign.id, depth=1),
            AdminHierarchy(ancestor_id=super_admin.id, descendant_id=super_admin.id, depth=0),
            AdminHierarchy(ancestor_id=super_admin.id, descendant_id=child.id, depth=1),
            AdminHierarchy(ancestor_id=child.id, descendant_id=child.id, depth=0),
            AdminHierarchy(ancestor_id=foreign.id, descendant_id=foreign.id, depth=0),
        ]
    )
    settings = {}
    for admin in (super_admin, child, foreign):
        settings[admin.username] = MarzhelpAdminSettings(
            admin_id=admin.id,
            total_traffic=100 * 1024**3,
            calculate_volume="created_traffic",
            max_users=10,
            device_capacity_limit=20,
        )
    db.add_all(settings.values())
    db.commit()
    return owner, super_admin, child, foreign, settings


def _provision_credit_user(
    db,
    admin: DBAdmin,
    username: str,
    allocated: int,
    *,
    used: int = 0,
    concurrent_user_limit: int = 2,
) -> User:
    request = SimpleNamespace(
        data_limit=allocated,
        expire=None,
        on_hold_expire_duration=None,
        concurrent_user_limit=concurrent_user_limit,
        inbounds={},
        next_plan=None,
    )
    quota = marzhelp_policy.validate_create(db, admin.id, request)
    user = User(
        username=username,
        admin=admin,
        status=UserStatus.active,
        data_limit=allocated,
        used_traffic=used,
        concurrent_user_limit=concurrent_user_limit,
        proxies=[Proxy(type=ProxyTypes.VLESS, settings={})],
    )
    db.add(user)
    db.flush()
    marzhelp_policy.record_create(db, user, quota is not None)
    db.commit()
    return user


def test_hierarchy_off_list_and_usage_are_owner_scoped(db):
    sudo, admin_a, admin_b, _, _ = _seed_hierarchy_off(db)

    assert _list_users(db, sudo) == ["user-a", "user-b"]
    assert _list_users(db, sudo, ["admin-b"]) == ["user-b"]
    assert _list_users(db, admin_a) == ["user-a"]
    assert _list_users(db, admin_b) == ["user-b"]
    assert _list_users(db, admin_a, ["admin-b"]) == []

    assert _usage_total(db, sudo) == 40
    assert _usage_total(db, sudo, ["admin-b"]) == 29
    assert _usage_total(db, admin_a) == 11
    assert _usage_total(db, admin_b) == 29
    assert _usage_total(db, admin_a, ["admin-b"]) == 0


def test_hierarchy_on_list_and_usage_enforce_subtree_intersection(db):
    owner, super_admin, child, sibling, _ = _seed_hierarchy_on(db)

    assert _list_users(db, owner) == [
        "user-child",
        "user-owner",
        "user-sibling",
        "user-super",
    ]
    assert _list_users(db, super_admin) == ["user-child", "user-super"]
    assert _list_users(db, child) == ["user-child"]
    assert _list_users(db, sibling) == ["user-sibling"]
    assert _list_users(db, super_admin, ["admin-b"]) == []
    assert _list_users(db, super_admin, ["admin-a", "admin-b"]) == ["user-child"]

    assert _usage_total(db, owner) == 15
    assert _usage_total(db, super_admin) == 6
    assert _usage_total(db, child) == 4
    assert _usage_total(db, sibling) == 8
    assert _usage_total(db, super_admin, ["admin-b"]) == 0
    assert _usage_total(db, super_admin, ["does-not-exist"]) == 0
    assert _usage_total(db, super_admin, ["admin-a", "admin-b"]) == 4


def test_single_user_routes_share_fail_closed_foreign_user_dependency(db):
    _, admin_a, _, _, user_b = _seed_hierarchy_off(db)

    with pytest.raises(HTTPException) as raised:
        get_validated_user(user_b.username, admin=_api_admin(admin_a), db=db)
    assert raised.value.status_code == 403

    for handler in (
        get_user,
        modify_user,
        remove_user,
        reset_user_data_usage,
        revoke_user_subscription,
        get_user_usage,
        active_next_plan,
    ):
        dependency = signature(handler).parameters["dbuser"].default.dependency
        assert dependency is get_validated_user


def test_bulk_action_rejects_foreign_user_before_any_mutation(db):
    _, admin_a, _, user_a, user_b = _seed_hierarchy_off(db)
    payload = BulkUserActionRequest(
        usernames=[user_a.username, user_b.username],
        operation=BulkUserOperation.deactivate,
    )

    with pytest.raises(HTTPException) as raised:
        bulk_user_action(
            request=_request("POST", "/api/users/bulk"),
            payload=payload,
            bg=BackgroundTasks(),
            db=db,
            admin=_api_admin(admin_a),
        )

    assert raised.value.status_code == 403
    db.refresh(user_a)
    db.refresh(user_b)
    assert user_a.status == UserStatus.active
    assert user_b.status == UserStatus.active
    assert db.query(AdminAuditLog).count() == 0


def test_expired_user_query_is_scoped_with_hierarchy_off(db):
    _, admin_a, _, user_a, user_b = _seed_hierarchy_off(db)
    now = datetime.now(timezone.utc)
    expires_at = int((now + timedelta(hours=1)).timestamp())
    user_a.status = UserStatus.expired
    user_a.expire = expires_at
    user_b.status = UserStatus.expired
    user_b.expire = expires_at
    db.commit()

    visible = get_expired_users_list(
        db,
        _api_admin(admin_a),
        now - timedelta(days=1),
        now + timedelta(days=1),
    )
    assert [user.username for user in visible] == ["user-a"]


def test_hierarchy_on_foreign_single_bulk_and_expired_paths_fail_closed(db):
    _, super_admin, _, _, users = _seed_hierarchy_on(db)
    now = datetime.now(timezone.utc)
    expires_at = int((now + timedelta(hours=1)).timestamp())
    users["child"].status = UserStatus.expired
    users["child"].expire = expires_at
    users["sibling"].status = UserStatus.expired
    users["sibling"].expire = expires_at
    db.commit()

    with pytest.raises(HTTPException) as single_error:
        get_validated_user(
            users["sibling"].username,
            admin=_api_admin(super_admin),
            db=db,
        )
    assert single_error.value.status_code == 403

    payload = BulkUserActionRequest(
        usernames=[users["child"].username, users["sibling"].username],
        operation=BulkUserOperation.deactivate,
    )
    with pytest.raises(HTTPException) as bulk_error:
        bulk_user_action(
            request=_request("POST", "/api/users/bulk"),
            payload=payload,
            bg=BackgroundTasks(),
            db=db,
            admin=_api_admin(super_admin),
        )
    assert bulk_error.value.status_code == 403
    assert users["child"].status == UserStatus.expired
    assert users["sibling"].status == UserStatus.expired

    visible = get_expired_users_list(
        db,
        _api_admin(super_admin),
        now - timedelta(days=1),
        now + timedelta(days=1),
    )
    assert [user.username for user in visible] == ["user-child"]


@pytest.mark.parametrize("hierarchy_enabled", [False, True])
def test_create_user_records_authenticated_owner_and_audit_actor(
    db,
    monkeypatch,
    hierarchy_enabled,
):
    if hierarchy_enabled:
        _, _, admin_a, _, _ = _seed_hierarchy_on(db)
    else:
        _, admin_a, _, _, _ = _seed_hierarchy_off(db)
    monkeypatch.setattr(
        xray.config,
        "inbounds_by_protocol",
        {
            ProxyTypes.VLESS: [
                {"tag": "VLESS TCP", "protocol": "vless"},
            ]
        },
    )
    monkeypatch.setattr(
        xray.config,
        "inbounds_by_tag",
        {"VLESS TCP": {"tag": "VLESS TCP", "protocol": "vless"}},
    )
    reported = {}
    monkeypatch.setattr(
        report,
        "user_created",
        lambda *, user, user_id, by, user_admin: reported.update(
            user=user,
            user_id=user_id,
            by=by,
            user_admin=user_admin,
        ),
    )
    payload = UserCreate(
        username="created_by_a",
        proxies={ProxyTypes.VLESS: {}},
        inbounds={ProxyTypes.VLESS: ["VLESS TCP"]},
    )

    response = add_user(
        request=_request("POST", "/api/user"),
        new_user=payload,
        bg=BackgroundTasks(),
        db=db,
        admin=_api_admin(admin_a),
    )

    created = db.query(User).filter(User.username == response.username).one()
    audit = db.query(AdminAuditLog).filter_by(action="user.create").one()
    assert created.admin_id == admin_a.id
    assert created.username == f"{admin_a.user_namespace_prefix}_{payload.username}"
    assert response.admin.username == admin_a.username
    assert reported["by"].username == admin_a.username
    assert reported["user_admin"].username == admin_a.username
    assert audit.admin_id == admin_a.id
    assert audit.admin_username == admin_a.username
    assert audit.target_id == str(created.id)
    assert audit.target_name == created.username


def test_set_owner_is_explicit_authorized_and_audited(db):
    sudo, admin_a, admin_b, user_a, _ = _seed_hierarchy_off(db)
    dependency = signature(set_user_owner).parameters["admin"].default.dependency
    assert dependency.__func__ is APIAdmin.check_sudo_admin.__func__

    response = set_user_owner(
        request=_request("PUT", f"/api/user/{user_a.username}/set-owner"),
        admin_username=admin_b.username,
        dbuser=user_a,
        db=db,
        admin=_api_admin(sudo),
    )

    audit = db.query(AdminAuditLog).filter_by(action="user.owner_change").one()
    assert response.admin.username == admin_b.username
    assert user_a.admin_id == admin_b.id
    assert audit.admin_id == sudo.id
    assert audit.admin_username == sudo.username
    assert audit.target_id == str(user_a.id)
    assert audit.target_name == user_a.username
    assert audit.previous_value == {"admin": admin_a.username}
    assert audit.new_value == {"admin": admin_b.username}


def test_set_owner_dependency_rejects_non_owner_in_hierarchy_mode(db, monkeypatch):
    _, super_admin, _, _, _ = _seed_hierarchy_on(db)
    api_super = _api_admin(super_admin)
    monkeypatch.setattr(
        APIAdmin,
        "get_admin",
        classmethod(lambda _cls, _token, _db: api_super),
    )

    with pytest.raises(HTTPException) as raised:
        APIAdmin.check_sudo_admin(
            _request("PUT", "/api/user/user-child/set-owner"),
            db=db,
            token="test-token",
        )
    assert raised.value.status_code == 403


def test_set_owner_rolls_back_when_audit_cannot_be_written(db, monkeypatch):
    sudo, admin_a, admin_b, user_a, _ = _seed_hierarchy_off(db)

    def fail_audit(*_args, **_kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr(AuditLogService, "log", fail_audit)
    with pytest.raises(RuntimeError, match="audit unavailable"):
        set_user_owner(
            request=_request("PUT", f"/api/user/{user_a.username}/set-owner"),
            admin_username=admin_b.username,
            dbuser=user_a,
            db=db,
            admin=_api_admin(sudo),
        )

    db.expire_all()
    assert db.get(User, user_a.id).admin_id == admin_a.id


def test_cli_set_owner_is_an_explicit_audited_operation(db, monkeypatch):
    _, admin_a, admin_b, user_a, _ = _seed_hierarchy_off(db)

    @contextmanager
    def test_db():
        yield db

    monkeypatch.setattr(cli_user, "GetDB", test_db)
    monkeypatch.setattr(cli_user.utils, "success", lambda _message: None)
    cli_user.set_owner(
        username=user_a.username,
        admin=admin_b.username,
        yes_to_all=True,
    )

    db.refresh(user_a)
    audit = db.query(AdminAuditLog).filter_by(action="user.owner_change").one()
    assert user_a.admin_id == admin_b.id
    assert audit.admin_username == "cli"
    assert audit.target_id == str(user_a.id)
    assert audit.previous_value == {"admin": admin_a.username}
    assert audit.new_value == {"admin": admin_b.username}


@pytest.mark.parametrize("delete_actor", ["self", "parent"])
def test_delete_charges_actual_owner_never_actor_and_never_refunds_credit(
    db,
    delete_actor,
):
    _, super_admin, child, _, settings = _seed_credit_hierarchy(db)
    allocated = 12 * 1024**3
    user = _provision_credit_user(
        db,
        child,
        f"delete-{delete_actor}",
        allocated,
        used=5 * 1024**3,
        concurrent_user_limit=3,
    )
    user_id = user.id
    actor = child if delete_actor == "self" else super_admin
    validated = get_validated_user(user.username, admin=_api_admin(actor), db=db)

    remove_user(
        request=_request("DELETE", f"/api/user/{user.username}"),
        bg=BackgroundTasks(),
        db=db,
        dbuser=validated,
        admin=_api_admin(actor),
    )

    child_settings = settings[child.username]
    db.refresh(child_settings)
    ledger = db.get(MarzhelpDeletedUser, user_id)
    transaction = (
        db.query(MarzhelpAccountingTransaction)
        .filter_by(operation_key=f"delete:{user_id}")
        .one()
    )
    audit = db.query(AdminAuditLog).filter_by(action="user.delete").one()
    assert ledger.admin_id == child.id
    assert ledger.allocated_traffic == allocated
    assert ledger.refunded_traffic == 0
    assert transaction.admin_id == child.id
    assert transaction.traffic_delta == 0
    assert transaction.volume_delta == 0
    assert child_settings.used_traffic == allocated
    assert child_settings.user_count_used == 0
    assert child_settings.capacity_used == 0
    assert audit.admin_id == actor.id
    assert audit.target_id == str(user_id)
    assert audit.target_name == f"delete-{delete_actor}"


def test_super_admin_and_owner_creation_keep_owner_credit_boundaries(db):
    owner, super_admin, _, _, settings = _seed_credit_hierarchy(db)
    allocated = 8 * 1024**3
    super_user = _provision_credit_user(
        db,
        super_admin,
        "super-credit-user",
        allocated,
    )
    owner_user = User(
        username="owner-exempt-user",
        admin=owner,
        status=UserStatus.active,
        data_limit=allocated,
        used_traffic=1024**3,
        proxies=[Proxy(type=ProxyTypes.VLESS, settings={})],
    )
    db.add(owner_user)
    db.commit()
    owner_user_id = owner_user.id

    assert super_user.admin_id == super_admin.id
    db.refresh(settings[super_admin.username])
    assert settings[super_admin.username].used_traffic == allocated
    assert db.get(MarzhelpAdminSettings, owner.id) is None

    remove_user(
        request=_request("DELETE", f"/api/user/{owner_user.username}"),
        bg=BackgroundTasks(),
        db=db,
        dbuser=owner_user,
        admin=_api_admin(owner),
    )
    owner_ledger = db.get(MarzhelpDeletedUser, owner_user_id)
    assert owner_ledger.admin_id == owner.id
    assert owner_ledger.refunded_traffic == 0


def test_explicit_owner_transfer_then_delete_keeps_both_allocations_non_refundable(db):
    owner, super_admin, child, _, settings = _seed_credit_hierarchy(db)
    allocated = 10 * 1024**3
    user = _provision_credit_user(db, child, "transfer-delete", allocated)
    user_id = user.id

    transferred = set_user_owner(
        request=_request("PUT", f"/api/user/{user.username}/set-owner"),
        admin_username=super_admin.username,
        dbuser=user,
        db=db,
        admin=_api_admin(owner),
    )
    transferred_dbuser = db.get(User, user_id)
    assert transferred.admin.username == super_admin.username
    remove_user(
        request=_request("DELETE", f"/api/user/{user.username}"),
        bg=BackgroundTasks(),
        db=db,
        dbuser=transferred_dbuser,
        admin=_api_admin(owner),
    )

    child_settings = settings[child.username]
    super_settings = settings[super_admin.username]
    db.refresh(child_settings)
    db.refresh(super_settings)
    ledger = db.get(MarzhelpDeletedUser, user_id)
    audits = db.query(AdminAuditLog).order_by(AdminAuditLog.id).all()
    assert child_settings.used_traffic == allocated
    assert child_settings.user_count_used == 0
    assert super_settings.used_traffic == allocated
    assert super_settings.user_count_used == 0
    assert ledger.admin_id == super_admin.id
    assert ledger.refunded_traffic == 0
    assert [entry.action for entry in audits] == [
        "user.owner_change",
        "user.delete",
    ]
    assert all(entry.admin_id == owner.id for entry in audits)
    assert all(entry.target_id == str(user_id) for entry in audits)


def test_foreign_delete_is_rejected_before_bulk_parent_delete_accounts_by_owner(db):
    _, super_admin, child, foreign, settings = _seed_credit_hierarchy(db)
    first = _provision_credit_user(db, child, "bulk-child-one", 4 * 1024**3)
    second = _provision_credit_user(db, child, "bulk-child-two", 6 * 1024**3)

    with pytest.raises(HTTPException) as raised:
        get_validated_user(first.username, admin=_api_admin(foreign), db=db)
    assert raised.value.status_code == 403
    assert db.get(User, first.id) is not None
    assert db.query(MarzhelpDeletedUser).count() == 0

    job, created = bulk_operations.create_user_job(
        db,
        super_admin,
        BulkUserJobCreateRequest(
            operation_id="bulk-delete-child-scope",
            operation=BulkUserOperation.delete,
            target_scope=BulkTargetScope.SELECTED_ADMINS_DIRECT,
            selected_admin_ids=[child.id],
        ),
    )
    response, _ = bulk_operations.execute_job(
        db,
        super_admin,
        job.idempotency_key,
        chunk_size=100,
        retry_failed=False,
    )

    child_settings = settings[child.username]
    db.refresh(child_settings)
    ledgers = db.query(MarzhelpDeletedUser).order_by(MarzhelpDeletedUser.user_id).all()
    targets = db.query(AdminBulkJobTarget).filter_by(job_id=job.id).order_by(AdminBulkJobTarget.sequence).all()
    assert created is True
    assert response.status == "COMPLETE"
    assert response.success_count == 2
    assert [target.target_username for target in targets] == ["bulk-child-one", "bulk-child-two"]
    assert all(target.status == "SUCCESS" for target in targets)
    assert [entry.admin_id for entry in ledgers] == [child.id, child.id]
    assert [entry.refunded_traffic for entry in ledgers] == [0, 0]
    assert child_settings.used_traffic == 10 * 1024**3
    assert child_settings.user_count_used == 0
    assert child_settings.capacity_used == 0


def test_delete_after_usage_reset_and_renewal_preserves_lifetime_and_credit(db):
    _, _, child, _, settings = _seed_credit_hierarchy(db)
    user = _provision_credit_user(
        db,
        child,
        "reset-renew-delete",
        10 * 1024**3,
        used=3 * 1024**3,
    )
    user_id = user.id

    crud.reset_user_data_usage(db, user)
    crud.update_user(
        db,
        user,
        UserModify(data_limit=15 * 1024**3),
        operation=marzhelp_policy.UserUpdateOperation.renew,
    )
    user.used_traffic = 2 * 1024**3
    db.commit()
    remove_user(
        request=_request("DELETE", f"/api/user/{user.username}"),
        bg=BackgroundTasks(),
        db=db,
        dbuser=user,
        admin=_api_admin(child),
    )

    child_settings = settings[child.username]
    db.refresh(child_settings)
    ledger = db.get(MarzhelpDeletedUser, user_id)
    transactions = (
        db.query(MarzhelpAccountingTransaction)
        .filter_by(user_id=user_id)
        .order_by(MarzhelpAccountingTransaction.id)
        .all()
    )
    assert ledger.used_traffic_total == 5 * 1024**3
    assert ledger.allocated_traffic == 15 * 1024**3
    assert ledger.refunded_traffic == 0
    assert child_settings.used_traffic == 15 * 1024**3
    summary = marzhelp_policy.quota_summary(db, child.id)
    assert summary["lifetime_consumed_traffic"] == 5 * 1024**3
    assert summary["lifetime_created_traffic"] == 25 * 1024**3
    assert [entry.operation_type for entry in transactions] == [
        "create",
        "renew",
        "delete",
    ]
