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
    AdminHierarchySettings,
    MarzhelpAccountingTransaction,
    MarzhelpAdminSettings,
    MarzhelpAdminInboundPermission,
    MarzhelpAdminUserLimitPermission,
    MarzhelpDeletedUser,
    NextPlan,
    Proxy,
    ProxyInbound,
    SystemOwner,
    User,
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
    [(50 * GB, 0), (30 * GB, 0), (0, 0), (60 * GB, 0)],
)
def test_delete_refund_formula(used, expected):
    assert policy.calculate_delete_refund(50 * GB, used) == expected


def test_legacy_sudo_remains_credit_exempt_when_hierarchy_is_disabled(session):
    sudo = Admin(username="legacy-sudo", hashed_password="x", is_sudo=True)
    session.add(sudo)
    session.flush()
    settings = MarzhelpAdminSettings(
        admin_id=sudo.id,
        total_traffic=10 * GB,
        calculate_volume="created_traffic",
    )
    session.add(settings)
    session.commit()

    assert policy.validate_create(session, sudo.id, plan(data_limit=10 * GB)) is None
    session.refresh(settings)
    assert settings.used_traffic == 0


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


def test_allocated_credit_rejects_overspend_atomically(session):
    admin, settings = add_admin(
        session,
        total_traffic=20 * GB,
        calculate_volume="created_traffic",
    )
    with pytest.raises(policy.MarzhelpPolicyError) as exc:
        policy.validate_create(session, admin.id, plan(data_limit=50 * GB))
    assert exc.value.code == "traffic_exhausted"
    session.rollback()
    assert settings.used_traffic == 0

    policy.record_quota_rejection(exc.value, session)
    rejection = session.query(MarzhelpAccountingTransaction).one()
    assert rejection.operation_type == "traffic_credit"
    assert rejection.volume_delta == 0
    assert rejection.renewal_delta == 0
    assert rejection.result == "rejected"
    assert rejection.details == {
        "code": "traffic_exhausted",
        "requested_delta": 50 * GB,
        "used": 0,
        "limit": 20 * GB,
    }


def test_delete_is_idempotent_records_usage_and_never_refunds_credit(session):
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

    assert policy.quota_summary(session, admin.id)["credit_used"] == 30 * GB
    assert policy.capture_delete(session, user) == 0
    assert policy.capture_delete(session, user) == 0
    session.delete(user)
    session.commit()

    ledger = session.query(MarzhelpDeletedUser).one()
    assert ledger.used_traffic_total == 30 * GB
    assert ledger.refunded_traffic == 0
    assert policy.quota_summary(session, admin.id)["credit_used"] == 30 * GB
    assert session.query(MarzhelpAccountingTransaction).count() == 1


def test_ordinary_volume_and_time_edits_never_consume_renewal_quota(session):
    admin, settings = add_admin(session, allowance=3)
    settings.renewal_remaining = 0
    settings.renewals_used = 4
    policy.validate_create(session, admin.id, plan())
    session.commit()
    assert settings.user_limit == 2

    now = int(datetime.now(timezone.utc).timestamp())
    user = User(
        username="renew-me",
        admin_id=admin.id,
        status=UserStatus.active,
        data_limit=GB,
        expire=now + 30 * 86400,
        used_traffic=0,
    )
    session.add(user)
    session.commit()

    renewal, consumed = policy.validate_update(session, user, plan(data_limit=2 * GB))
    assert not renewal and consumed
    user.data_limit = 2 * GB
    session.commit()
    assert settings.user_limit == 2
    assert settings.renewal_remaining == 0
    assert settings.renewals_used == 4

    renewal, consumed = policy.validate_update(
        session,
        user,
        plan(data_limit=2 * GB, expire=now + 20 * 86400),
    )
    assert not renewal and consumed
    session.commit()
    assert settings.user_limit == 1
    assert settings.renewal_remaining == 0
    assert settings.renewals_used == 4


def test_explicit_renewal_enforces_and_consumes_renewal_quota_once(session):
    admin, settings = add_admin(
        session,
        allowance=2,
        renewal_remaining=1,
        renewals_used=0,
    )
    user = User(
        username="explicit-renewal",
        admin_id=admin.id,
        status=UserStatus.active,
        data_limit=GB,
        used_traffic=0,
    )
    session.add(user)
    session.commit()

    renewal, consumed = policy.validate_update(
        session,
        user,
        plan(data_limit=2 * GB),
        operation=policy.UserUpdateOperation.renew,
    )

    assert renewal and consumed
    assert settings.renewal_remaining == 0
    assert settings.renewals_used == 1
    assert settings.user_limit == 1

    session.rollback()
    settings.renewal_remaining = 0
    session.commit()
    with pytest.raises(policy.MarzhelpPolicyError) as raised:
        policy.validate_update(
            session,
            user,
            plan(data_limit=3 * GB),
            operation=policy.UserUpdateOperation.renew,
        )
    assert raised.value.code == "renewal_quota_exhausted"


def test_next_plan_activation_is_an_explicit_renewal(session):
    admin, settings = add_admin(
        session,
        allowance=2,
        renewal_remaining=0,
        renewals_used=3,
    )
    user = User(
        username="next-plan-renewal",
        admin_id=admin.id,
        status=UserStatus.active,
        data_limit=GB,
        used_traffic=0,
    )
    user.next_plan = NextPlan(data_limit=2 * GB, expire=None)
    session.add(user)
    session.commit()

    with pytest.raises(policy.MarzhelpPolicyError) as raised:
        policy.validate_next_plan_activation(session, user)
    assert raised.value.code == "renewal_quota_exhausted"
    session.rollback()

    settings.renewal_remaining = 1
    session.commit()
    assert policy.validate_next_plan_activation(session, user)
    assert settings.renewal_remaining == 0
    assert settings.renewals_used == 4
    assert settings.user_limit == 1


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


def test_conversion_to_unlimited_is_an_ordinary_edit_not_renewal(session):
    admin, settings = add_admin(
        session,
        allowance=1,
        renewal_remaining=0,
        renewals_used=2,
    )
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

    assert not renewal and consumed
    assert settings.user_limit == 1
    assert settings.renewal_remaining == 0
    assert settings.renewals_used == 2


def test_only_real_owner_is_policy_exempt_when_hierarchy_is_enabled(session):
    owner = Admin(username="policy-owner", hashed_password="x", is_sudo=True)
    delegated_sudo = Admin(username="policy-super", hashed_password="x", is_sudo=True)
    session.add_all((owner, delegated_sudo))
    session.flush()
    session.add_all(
        (
            AdminHierarchySettings(id=1, enabled=True, max_depth=64),
            SystemOwner(id=1, admin_id=owner.id),
            MarzhelpAdminSettings(
                admin_id=owner.id,
                total_traffic=0,
                calculate_volume="created_traffic",
            ),
            MarzhelpAdminSettings(
                admin_id=delegated_sudo.id,
                total_traffic=0,
                calculate_volume="created_traffic",
            ),
        )
    )
    session.commit()

    assert policy.validate_create(session, owner.id, plan(data_limit=GB)) is None
    with pytest.raises(policy.MarzhelpPolicyError) as raised:
        policy.validate_create(session, delegated_sudo.id, plan(data_limit=GB))
    assert raised.value.code == "traffic_exhausted"


def test_allocated_credit_uses_persistent_non_refundable_counter(session):
    admin, settings = add_admin(
        session,
        total_traffic=50 * GB,
        calculate_volume="created_traffic",
    )
    policy.validate_create(session, admin.id, plan(data_limit=50 * GB))
    user = User(
        username="allocated-delete",
        admin_id=admin.id,
        status=UserStatus.active,
        data_limit=50 * GB,
        used_traffic=50 * GB,
    )
    session.add(user)
    session.commit()

    policy.capture_delete(session, user)
    session.delete(user)
    session.commit()
    assert settings.used_traffic == 50 * GB
    assert policy.quota_summary(session, admin.id)["credit_remaining"] == 0
    with pytest.raises(policy.MarzhelpPolicyError, match="credit is exhausted"):
        policy.validate_create(session, admin.id, plan(data_limit=GB))
    session.rollback()
    assert settings.used_traffic == 50 * GB


def test_actual_usage_warning_thresholds_are_independent(session):
    admin, _ = add_admin(
        session,
        total_traffic=100 * GB,
        calculate_volume="used_traffic",
        admin_traffic_warning_percent=70,
        sudo_traffic_warning_percent=90,
    )
    session.add(
        User(
            username="warning-user",
            admin_id=admin.id,
            data_limit=100 * GB,
            used_traffic=75 * GB,
        )
    )
    session.commit()

    quota = policy.quota_summary(session, admin.id)
    assert quota["credit_usage_percent"] == 75
    assert quota["admin_warning_active"] is True
    assert quota["sudo_warning_active"] is False


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
