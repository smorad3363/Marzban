from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models import (
    Admin,
    MarzhelpAccountingTransaction,
    MarzhelpAdminSettings,
    MarzhelpAdminInboundPermission,
    MarzhelpAdminUserLimitPermission,
    MarzhelpDeletedUser,
    Proxy,
    ProxyInbound,
    User,
    UserUsageResetLogs,
)
from app.db import crud
from app.dependencies import get_validated_user
from app.models.admin import Admin as AdminSchema
from app.models.proxy import ProxyTypes
from app.models.user import UserCreate
from app.routers.system import get_inbounds
from app.models.user import UserStatus
from app.utils import marzhelp_policy as policy


GB = 1024**3


@pytest.fixture()
def session(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'policy.sqlite3'}",
        connect_args={"check_same_thread": False, "timeout": 10},
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    db = Session()
    db.info["session_factory"] = Session
    yield db
    db.close()
    engine.dispose()


def add_admin(db, allowance=None, **settings):
    admin = Admin(username=f"admin-{id(db)}-{db.query(Admin).count()}", hashed_password="x")
    db.add(admin)
    db.flush()
    row = MarzhelpAdminSettings(admin_id=admin.id, user_limit=allowance, **settings)
    db.add(row)
    db.commit()
    return admin, row


def plan(data_limit=10 * GB, expire=None, on_hold_expire_duration=None, next_plan=None):
    return SimpleNamespace(
        data_limit=data_limit,
        expire=expire,
        on_hold_expire_duration=on_hold_expire_duration,
        next_plan=next_plan,
    )


@pytest.mark.parametrize(
    ("used", "expected"),
    [(50 * GB, 0), (30 * GB, 20 * GB), (0, 50 * GB), (60 * GB, 0)],
)
def test_delete_refund_formula(used, expected):
    assert policy.calculate_delete_refund(50 * GB, used) == expected


def test_existing_user_count_limit_blocks_create_and_delete_frees_slot(session):
    admin, _ = add_admin(session, max_users=2)
    session.add_all(
        [
            User(username="counted-one", admin_id=admin.id, status=UserStatus.active),
            User(username="counted-two", admin_id=admin.id, status=UserStatus.disabled),
        ]
    )
    session.commit()

    with pytest.raises(policy.MarzhelpPolicyError) as exc:
        policy.validate_create(session, admin.id, plan())
    assert exc.value.code == "max_users_exceeded"

    session.delete(session.query(User).filter(User.username == "counted-two").one())
    session.commit()
    assert policy.validate_create(session, admin.id, plan()) is not None


def test_unlimited_traffic_does_not_bypass_account_limit(session):
    admin, _ = add_admin(session, max_users=1)
    session.add(User(username="unlimited-existing", admin_id=admin.id, data_limit=None))
    session.commit()

    with pytest.raises(policy.MarzhelpPolicyError) as exc:
        policy.validate_create(session, admin.id, plan(data_limit=0))
    assert exc.value.code == "max_users_exceeded"


def test_provisioning_volume_rejects_overspend_atomically(session):
    admin, settings = add_admin(
        session,
        provisioning_volume_limit=20 * GB,
    )
    with pytest.raises(policy.MarzhelpPolicyError) as exc:
        policy.validate_create(session, admin.id, plan(data_limit=50 * GB))
    assert exc.value.code == "provisioning_volume_exceeded"
    session.rollback()
    assert settings.provisioning_volume_used == 0

    policy.record_quota_rejection(exc.value, session)
    rejection = session.query(MarzhelpAccountingTransaction).one()
    assert rejection.operation_type == "provisioning_volume"
    assert rejection.volume_delta == 0
    assert rejection.renewal_delta == 0
    assert rejection.result == "rejected"
    assert rejection.details == {
        "code": "provisioning_volume_exceeded",
        "requested_delta": 50 * GB,
        "used": 0,
        "limit": 20 * GB,
    }


def test_delete_is_idempotent_and_records_actual_usage(session):
    admin, _ = add_admin(session)
    user = User(
        username="delete-me",
        admin_id=admin.id,
        status=UserStatus.active,
        data_limit=50 * GB,
        used_traffic=30 * GB,
    )
    session.add(user)
    session.commit()

    assert policy.capture_delete(session, user) == 20 * GB
    assert policy.capture_delete(session, user) == 0
    session.commit()

    ledger = session.query(MarzhelpDeletedUser).one()
    assert ledger.used_traffic_total == 30 * GB
    assert ledger.refunded_traffic == 20 * GB
    assert session.query(MarzhelpAccountingTransaction).count() == 1


def test_create_and_renewal_quotas_are_independent(session):
    admin, _ = add_admin(session, allowance=12, renewal_limit=8)
    for _ in range(12):
        policy.validate_create(session, admin.id, plan())
        session.commit()

    user = User(
        username="renew-me",
        admin_id=admin.id,
        status=UserStatus.active,
        data_limit=GB,
        used_traffic=0,
    )
    session.add(user)
    session.commit()
    for index in range(8):
        modification = plan(data_limit=(index + 2) * GB)
        renewal, consumed = policy.validate_update(session, user, modification)
        assert renewal and consumed
        user.data_limit = modification.data_limit
        session.commit()

    settings = session.get(MarzhelpAdminSettings, admin.id)
    assert settings.user_limit == 0
    assert settings.renewals_used == 8
    with pytest.raises(policy.MarzhelpPolicyError, match="allowance"):
        policy.validate_create(session, admin.id, plan())
    with pytest.raises(policy.MarzhelpPolicyError, match="renewal quota"):
        policy.validate_update(session, user, plan(data_limit=11 * GB))


def test_failed_operation_rollback_does_not_consume_allowance(session):
    admin, _ = add_admin(session, allowance=1)
    policy.validate_create(session, admin.id, plan())
    session.rollback()
    assert session.get(MarzhelpAdminSettings, admin.id).user_limit == 1


def test_concurrent_last_allowance_only_one_wins(session):
    admin, _ = add_admin(session, allowance=1)
    Session = session.info["session_factory"]

    def attempt():
        db = Session()
        try:
            policy.validate_create(db, admin.id, plan())
            db.commit()
            return True
        except policy.MarzhelpPolicyError:
            db.rollback()
            return False
        finally:
            db.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: attempt(), range(2)))
    assert sorted(results) == [False, True]


def test_unlimited_traffic_rejected_on_create_edit_and_next_plan(session):
    admin, _ = add_admin(session, prevent_unlimited_traffic=True)
    policy.validate_create(session, admin.id, plan(data_limit=GB))
    session.rollback()
    with pytest.raises(policy.MarzhelpPolicyError, match="unlimited traffic"):
        policy.validate_create(session, admin.id, plan(data_limit=0))

    user = User(
        username="finite-user",
        admin_id=admin.id,
        status=UserStatus.active,
        data_limit=GB,
        used_traffic=0,
    )
    session.add(user)
    session.commit()
    with pytest.raises(policy.MarzhelpPolicyError, match="unlimited traffic"):
        policy.validate_update(session, user, plan(data_limit=0))
    with pytest.raises(policy.MarzhelpPolicyError, match="unlimited traffic"):
        policy.validate_update(
            session,
            user,
            plan(data_limit=GB, next_plan=SimpleNamespace(data_limit=0, expire=None)),
        )


def test_conversion_to_unlimited_counts_as_renewal(session):
    admin, _ = add_admin(session, allowance=1, renewal_limit=1)
    user = User(
        username="upgrade-to-unlimited",
        admin_id=admin.id,
        status=UserStatus.active,
        data_limit=GB,
        used_traffic=0,
    )
    session.add(user)
    session.commit()

    renewal, consumed = policy.validate_update(session, user, plan(data_limit=0))

    assert renewal and consumed
    settings = session.get(MarzhelpAdminSettings, admin.id)
    assert settings.user_limit == 1
    assert settings.renewals_used == 1


def test_created_traffic_counts_usage_and_resets_for_existing_unlimited_users(session):
    admin, _ = add_admin(
        session,
        total_traffic=10 * GB,
        calculate_volume="created_traffic",
    )
    user = User(
        username="legacy-unlimited",
        admin_id=admin.id,
        status=UserStatus.active,
        data_limit=None,
        used_traffic=8 * GB,
    )
    session.add(user)
    session.flush()
    session.add(UserUsageResetLogs(user_id=user.id, used_traffic_at_reset=3 * GB))
    session.commit()

    with pytest.raises(policy.MarzhelpPolicyError, match="credit is exhausted"):
        policy.validate_create(session, admin.id, plan(data_limit=GB))


def test_maximum_duration_create_and_renewal(session):
    admin, _ = add_admin(session, max_user_duration_days=31)
    now = int(datetime.now(timezone.utc).timestamp())
    policy.validate_create(session, admin.id, plan(expire=now + 31 * 86400))
    session.rollback()
    with pytest.raises(policy.MarzhelpPolicyError, match="31 days"):
        policy.validate_create(session, admin.id, plan(expire=now + 32 * 86400))
    with pytest.raises(policy.MarzhelpPolicyError, match="no-expiry"):
        policy.validate_create(session, admin.id, plan(expire=None))

    user = User(
        username="duration-user",
        admin_id=admin.id,
        status=UserStatus.active,
        data_limit=GB,
        expire=now + 20 * 86400,
        used_traffic=0,
    )
    session.add(user)
    session.commit()
    with pytest.raises(policy.MarzhelpPolicyError, match="31 days"):
        policy.validate_update(session, user, plan(data_limit=GB, expire=now + 32 * 86400))


def test_weighted_capacity_counts_existing_users_and_requested_limit(session):
    admin, settings = add_admin(session, max_users=10, device_capacity_limit=10)
    session.add_all(
        [
            User(username="weighted-two", admin_id=admin.id, concurrent_user_limit=2),
            User(username="weighted-four", admin_id=admin.id, concurrent_user_limit=4),
        ]
    )
    session.commit()

    request = plan()
    request.concurrent_user_limit = 4
    policy.validate_create(session, admin.id, request)

    assert settings.capacity_used == 10
    with pytest.raises(policy.MarzhelpPolicyError) as exc:
        policy.validate_create(session, admin.id, request)
    assert exc.value.code == "weighted_capacity_exceeded"


def test_weighted_capacity_edit_applies_only_delta(session):
    admin, settings = add_admin(session, max_users=10, device_capacity_limit=10)
    user = User(
        username="weighted-edit",
        admin_id=admin.id,
        concurrent_user_limit=2,
        status=UserStatus.active,
    )
    session.add(user)
    session.commit()

    upgrade = SimpleNamespace(
        data_limit=None,
        expire=None,
        next_plan=None,
        inbounds={},
        proxies={},
        on_hold_expire_duration=None,
        concurrent_user_limit=4,
        model_fields_set={"concurrent_user_limit"},
    )
    policy.validate_update(session, user, upgrade)
    user.concurrent_user_limit = 4
    session.commit()
    assert settings.capacity_used == 4

    downgrade = SimpleNamespace(
        data_limit=None,
        expire=None,
        next_plan=None,
        inbounds={},
        proxies={},
        on_hold_expire_duration=None,
        concurrent_user_limit=1,
        model_fields_set={"concurrent_user_limit"},
    )
    policy.validate_update(session, user, downgrade)
    user.concurrent_user_limit = 1
    session.commit()
    assert settings.capacity_used == 1


def test_selected_user_limits_are_enforced_server_side(session):
    admin, settings = add_admin(session, all_user_limits=False)
    settings.user_limit_permissions = [
        MarzhelpAdminUserLimitPermission(admin_id=admin.id, concurrent_user_limit=1),
        MarzhelpAdminUserLimitPermission(admin_id=admin.id, concurrent_user_limit=2),
    ]
    session.commit()

    allowed = plan()
    allowed.concurrent_user_limit = 2
    policy.validate_create(session, admin.id, allowed)
    session.rollback()

    denied = plan()
    denied.concurrent_user_limit = 4
    with pytest.raises(policy.MarzhelpPolicyError) as exc:
        policy.validate_create(session, admin.id, denied)
    assert exc.value.code == "user_limit_forbidden"


def test_inbound_permissions_filter_and_protect_users(session, monkeypatch):
    inbounds = [
        {"tag": "allowed", "protocol": "vless", "network": "tcp", "tls": "none"},
        {"tag": "denied", "protocol": "vless", "network": "tcp", "tls": "none"},
    ]
    monkeypatch.setattr(policy.xray.config, "inbounds_by_protocol", {ProxyTypes.VLESS: inbounds})
    monkeypatch.setattr(policy.xray.config, "inbounds_by_tag", {item["tag"]: item for item in inbounds})

    admin, settings = add_admin(session, all_inbounds=False)
    settings.inbound_permissions = [
        MarzhelpAdminInboundPermission(admin_id=admin.id, inbound_tag="allowed")
    ]
    allowed_inbound = ProxyInbound(tag="allowed")
    denied_inbound = ProxyInbound(tag="denied")
    accessible = User(
        username="accessible-user",
        admin_id=admin.id,
        proxies=[Proxy(type=ProxyTypes.VLESS, settings={}, excluded_inbounds=[denied_inbound])],
    )
    inaccessible = User(
        username="inaccessible-user",
        admin_id=admin.id,
        proxies=[Proxy(type=ProxyTypes.VLESS, settings={})],
    )
    session.add_all([allowed_inbound, accessible, inaccessible])
    session.commit()

    assert policy.can_access_user(session, admin, accessible)
    assert not policy.can_access_user(session, admin, inaccessible)
    assert [user.username for user in crud.get_users(
        session,
        admin=admin,
        allowed_inbounds={"allowed"},
    )] == ["accessible-user"]
    api_admin = AdminSchema.model_validate(admin)
    assert get_validated_user("accessible-user", admin=api_admin, db=session).username == "accessible-user"
    with pytest.raises(HTTPException) as exc:
        get_validated_user("inaccessible-user", admin=api_admin, db=session)
    assert exc.value.status_code == 403
    visible_inbounds = get_inbounds(db=session, admin=api_admin)
    assert [item["tag"] for item in visible_inbounds[ProxyTypes.VLESS]] == ["allowed"]

    request = plan()
    request.concurrent_user_limit = 1
    request.inbounds = {ProxyTypes.VLESS: ["denied"]}
    with pytest.raises(policy.MarzhelpPolicyError) as exc:
        policy.validate_create(session, admin.id, request)
    assert exc.value.code == "inbound_forbidden"

    sudo = Admin(username="root-access", hashed_password="x", is_sudo=True)
    session.add(sudo)
    session.commit()
    assert policy.can_access_user(session, sudo, inaccessible)


def test_deleting_weighted_user_releases_active_capacity(session):
    admin, settings = add_admin(session, max_users=6, device_capacity_limit=6)
    user = User(
        username="weighted-delete",
        admin_id=admin.id,
        concurrent_user_limit=4,
        status=UserStatus.active,
    )
    session.add(user)
    session.commit()
    settings.capacity_used = 4
    session.commit()

    policy.capture_delete(session, user)
    session.delete(user)
    session.commit()

    assert settings.capacity_used == 0
    assert policy.capacity_used(session, admin.id) == 0


def test_concurrent_weighted_creates_cannot_exceed_capacity(session, monkeypatch):
    inbounds = [{"tag": "capacity", "protocol": "vless", "network": "tcp", "tls": "none"}]
    monkeypatch.setattr(policy.xray.config, "inbounds_by_protocol", {ProxyTypes.VLESS: inbounds})
    monkeypatch.setattr(policy.xray.config, "inbounds_by_tag", {"capacity": inbounds[0]})
    admin, _ = add_admin(session, max_users=4, device_capacity_limit=4)
    Session = session.info["session_factory"]

    def attempt(index: int):
        db = Session()
        try:
            dbadmin = db.get(Admin, admin.id)
            crud.create_user(
                db,
                UserCreate(
                    username=f"concurrent-{index}",
                    proxies={"vless": {}},
                    inbounds={"vless": ["capacity"]},
                    concurrent_user_limit=3,
                ),
                admin=dbadmin,
            )
            return True
        except policy.MarzhelpPolicyError:
            db.rollback()
            return False
        finally:
            db.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, range(2)))

    assert sorted(results) == [False, True]
    assert policy.capacity_used(session, admin.id) == 3


def test_concurrent_creates_with_one_account_slot_only_one_succeeds(session, monkeypatch):
    inbounds = [{"tag": "account", "protocol": "vless", "network": "tcp", "tls": "none"}]
    monkeypatch.setattr(policy.xray.config, "inbounds_by_protocol", {ProxyTypes.VLESS: inbounds})
    monkeypatch.setattr(policy.xray.config, "inbounds_by_tag", {"account": inbounds[0]})
    admin, _ = add_admin(session, max_users=1)
    Session = session.info["session_factory"]

    def attempt(index: int):
        db = Session()
        try:
            crud.create_user(
                db,
                UserCreate(
                    username=f"account-slot-{index}",
                    proxies={"vless": {}},
                    inbounds={"vless": ["account"]},
                    concurrent_user_limit=1,
                ),
                admin=db.get(Admin, admin.id),
            )
            return True
        except policy.MarzhelpPolicyError:
            db.rollback()
            return False
        finally:
            db.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, range(2)))

    assert sorted(results) == [False, True]
    assert policy.user_count_used(session, admin.id) == 1
