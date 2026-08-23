from concurrent.futures import ThreadPoolExecutor
import os

import pytest
import sqlalchemy as sa
from OpenSSL import crypto
from alembic import command
from alembic.config import Config
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models import (
    Admin,
    AdminAccountStatus,
    AdminCreditTransfer,
    AdminHierarchySettings,
    AdminRole,
    AdminSuspensionReason,
    AdminUserCreationMode,
    AllocatedTrafficRefundEvent,
    AllocatedTrafficRefundRequest,
    MarzhelpAdminSettings,
    User,
    UserUsageResetLogs,
)
from app.models.user import UserStatus
from app.utils import admin_billing, admin_hierarchy, billing_service, marzhelp_policy


def _seed(db):
    db.add_all(
        [
            AdminRole(id=1, code="OWNER"),
            AdminRole(id=2, code="SUPER_ADMIN"),
            AdminRole(id=3, code="ADMIN"),
            AdminUserCreationMode(id=1, code="FREE_FORM"),
            AdminUserCreationMode(id=2, code="PLAN_ONLY"),
            AdminAccountStatus(id=1, code="ACTIVE"),
            AdminAccountStatus(id=2, code="SUSPENDED"),
            AdminAccountStatus(id=3, code="DISABLED"),
            AdminSuspensionReason(id=1, code="MANUAL"),
            AdminSuspensionReason(id=2, code="CREDIT_EXHAUSTED"),
            AdminSuspensionReason(id=3, code="ACCOUNT_EXPIRED"),
            AdminHierarchySettings(id=1, enabled=False, max_depth=64),
        ]
    )
    owner = Admin(username="stage3-owner", hashed_password="x", is_sudo=True)
    child = Admin(username="stage3-child", hashed_password="x", is_sudo=False)
    db.add_all([owner, child])
    db.flush()
    db.add_all(
        [
            MarzhelpAdminSettings(admin_id=owner.id, billing_mode="LEGACY_COMPAT"),
            MarzhelpAdminSettings(
                admin_id=child.id,
                billing_mode="ALLOCATED_TRAFFIC",
                total_traffic=100,
                used_traffic=50,
            ),
        ]
    )
    db.commit()
    admin_hierarchy.set_owner(db, owner.username)
    child = db.get(Admin, child.id)
    owner = db.get(Admin, owner.id)
    user = User(
        username="stage3-user",
        admin_id=child.id,
        status=UserStatus.active,
        data_limit=40,
        used_traffic=10,
        expire=2_000_000_000,
    )
    db.add(user)
    db.commit()
    return owner, child, user


@pytest.fixture()
def db(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'stage3.sqlite3'}")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.mark.parametrize("value", [None, 0, -1])
def test_seat_credit_rejects_missing_zero_unlimited_or_non_positive(value):
    with pytest.raises(admin_billing.BillingModeError) as exc:
        admin_billing.finite_seat_cost(value)
    assert exc.value.code == "seat_plan_requires_finite_devices"


def test_seat_credit_cost_is_explicit_devices_and_never_falls_back_or_refunds():
    strategy = admin_billing.STRATEGIES[admin_billing.BillingMode.SEAT_CREDIT]
    assert strategy.create_capacity_charge(7) == 7
    assert strategy.update_capacity_charge(7, 9) == 2
    assert strategy.update_capacity_charge(9, 3) == 0
    assert strategy.delete_capacity_charge(9) == 0


def test_legacy_compat_preserves_existing_weighted_behavior():
    strategy = admin_billing.STRATEGIES[admin_billing.BillingMode.LEGACY_COMPAT]
    assert strategy.create_capacity_charge(None) == 1
    assert strategy.update_capacity_charge(2, 5) == 3
    assert strategy.delete_capacity_charge(5) == -5


def test_expired_seat_allocation_remains_consumed(db):
    _, child, user = _seed(db)
    settings = db.get(MarzhelpAdminSettings, child.id)
    settings.billing_mode = "SEAT_CREDIT"
    settings.device_capacity_limit = 20
    settings.capacity_used = 5
    settings.used_traffic = 0
    user.concurrent_user_limit = 5
    user.expire = 1
    db.commit()
    assert admin_hierarchy.own_credit_spend(db, settings) == 5
    assert marzhelp_policy.capture_delete(db, user) == 0
    db.commit()
    assert settings.capacity_used == 5


def test_used_traffic_is_derived_incrementally_and_reset_is_not_duplicate(db):
    _, child, user = _seed(db)
    settings = db.get(MarzhelpAdminSettings, child.id)
    settings.billing_mode = "USED_TRAFFIC"
    settings.used_traffic = 999
    db.commit()
    assert admin_hierarchy.own_credit_spend(db, settings) == 10
    user.used_traffic = 15
    db.commit()
    assert admin_hierarchy.own_credit_spend(db, settings) == 15
    user.used_traffic = 0
    db.add(UserUsageResetLogs(user_id=user.id, used_traffic_at_reset=15))
    db.commit()
    assert admin_hierarchy.own_credit_spend(db, settings) == 15
    assert admin_hierarchy.own_credit_spend(db, settings) == 15


def test_allocated_strategy_charges_create_and_positive_increase_only():
    strategy = admin_billing.STRATEGIES[admin_billing.BillingMode.ALLOCATED_TRAFFIC]
    assert strategy.allocated_charge(None, 40, renewal=False) == 40
    assert strategy.allocated_charge(40, 55, renewal=False) == 15
    assert strategy.allocated_charge(55, 20, renewal=False) == 0
    assert strategy.allocated_charge(55, 20, renewal=True) == 20


def test_owner_mode_assignment_cannot_reinterpret_existing_balance(db):
    owner, child, _ = _seed(db)
    with pytest.raises(admin_hierarchy.HierarchyError) as exc:
        billing_service.assign_billing_mode(
            db,
            actor=owner,
            target=child,
            mode=admin_billing.BillingMode.SEAT_CREDIT,
            idempotency_key="stage3-mode-existing-balance",
            reason="must settle first",
        )
    assert exc.value.code == "billing_mode_transition_requires_settlement"
    db.rollback()
    assert db.get(MarzhelpAdminSettings, child.id).billing_mode == "ALLOCATED_TRAFFIC"


def test_allocated_refund_approval_is_separate_idempotent_ledger_credit(db):
    owner, child, user = _seed(db)
    row, created = billing_service.create_refund_request(
        db,
        actor=child,
        user=user,
        requested_refund_amount=30,
        request_reason="unused allocation",
        request_note="delete is separate",
        correlation_id="stage3-correlation-approve",
        idempotency_key="stage3-refund-request-approve",
    )
    assert created is True
    assert row.status == "PENDING"
    assert row.reviewer_admin_id == owner.id
    assert row.snapshot_allocated_quota == 40
    assert row.snapshot_current_quota == 40
    assert row.snapshot_used_traffic == 10
    assert row.snapshot_remaining_traffic == 30
    immutable_snapshot = (
        row.requester_admin_id,
        row.target_user_id,
        row.account_admin_id,
        row.reviewer_admin_id,
        row.snapshot_billing_mode,
        row.snapshot_plan_id,
        row.snapshot_plan_version_id,
        row.snapshot_plan_name,
        row.snapshot_allocated_quota,
        row.snapshot_current_quota,
        row.snapshot_used_traffic,
        row.snapshot_remaining_traffic,
        row.snapshot_user_created_at,
        row.snapshot_user_expire_at,
        row.snapshot_pre_delete_status,
        row.requested_refund_amount,
        row.request_reason,
        row.request_note,
        row.correlation_id,
    )
    assert db.get(MarzhelpAdminSettings, child.id).used_traffic == 50
    assert db.query(AdminCreditTransfer).count() == 0

    approved, changed = billing_service.decide_refund_request(
        db,
        actor=owner,
        request_id=row.id,
        decision="APPROVED",
        idempotency_key="stage3-refund-approve-decision",
        explanation="approved by parent",
    )
    assert changed is True
    assert approved.status == "APPROVED"
    assert db.get(MarzhelpAdminSettings, child.id).used_traffic == 20
    ledger = db.query(AdminCreditTransfer).one()
    assert (ledger.resource, ledger.delta, ledger.balance_before, ledger.balance_after) == (
        "allocated_refund",
        -30,
        50,
        20,
    )
    replay, changed = billing_service.decide_refund_request(
        db,
        actor=owner,
        request_id=row.id,
        decision="APPROVED",
        idempotency_key="stage3-refund-approve-decision",
        explanation="approved by parent",
    )
    assert replay.id == approved.id
    assert changed is False
    assert db.query(AdminCreditTransfer).count() == 1
    assert db.query(AllocatedTrafficRefundEvent).count() == 2
    assert immutable_snapshot == (
        approved.requester_admin_id,
        approved.target_user_id,
        approved.account_admin_id,
        approved.reviewer_admin_id,
        approved.snapshot_billing_mode,
        approved.snapshot_plan_id,
        approved.snapshot_plan_version_id,
        approved.snapshot_plan_name,
        approved.snapshot_allocated_quota,
        approved.snapshot_current_quota,
        approved.snapshot_used_traffic,
        approved.snapshot_remaining_traffic,
        approved.snapshot_user_created_at,
        approved.snapshot_user_expire_at,
        approved.snapshot_pre_delete_status,
        approved.requested_refund_amount,
        approved.request_reason,
        approved.request_note,
        approved.correlation_id,
    )


def test_reject_and_delete_never_return_allocated_credit(db):
    owner, child, user = _seed(db)
    settings = db.get(MarzhelpAdminSettings, child.id)
    assert marzhelp_policy.capture_delete(db, user) == 0
    db.commit()
    assert settings.used_traffic == 50
    row, _ = billing_service.create_refund_request(
        db,
        actor=child,
        user=user,
        requested_refund_amount=20,
        request_reason="review requested",
        request_note=None,
        correlation_id="stage3-correlation-reject",
        idempotency_key="stage3-refund-request-reject",
    )
    rejected, _ = billing_service.decide_refund_request(
        db,
        actor=owner,
        request_id=row.id,
        decision="REJECTED",
        idempotency_key="stage3-refund-reject-decision",
        explanation="not eligible",
    )
    assert rejected.status == "REJECTED"
    assert settings.used_traffic == 50
    assert db.query(AdminCreditTransfer).count() == 0
    cancelled_row, _ = billing_service.create_refund_request(
        db,
        actor=child,
        user=user,
        requested_refund_amount=5,
        request_reason="cancel test",
        request_note=None,
        correlation_id="stage3-correlation-cancel",
        idempotency_key="stage3-refund-request-cancel",
    )
    cancelled, _ = billing_service.decide_refund_request(
        db,
        actor=child,
        request_id=cancelled_row.id,
        decision="CANCELLED",
        idempotency_key="stage3-refund-cancel-decision",
        explanation="request withdrawn",
    )
    assert cancelled.status == "CANCELLED"
    assert settings.used_traffic == 50
    assert db.query(AdminCreditTransfer).count() == 0


def test_unauthorized_refund_decision_is_rejected(db):
    owner, child, user = _seed(db)
    outsider = Admin(username="stage3-outsider", hashed_password="x", is_sudo=False, role_id=3)
    db.add(outsider)
    db.flush()
    db.add(MarzhelpAdminSettings(admin_id=outsider.id, billing_mode="LEGACY_COMPAT"))
    db.commit()
    row, _ = billing_service.create_refund_request(
        db,
        actor=child,
        user=user,
        requested_refund_amount=10,
        request_reason="authorization test",
        request_note=None,
        correlation_id="stage3-correlation-authz",
        idempotency_key="stage3-refund-request-authz",
    )
    with pytest.raises(admin_hierarchy.HierarchyError) as exc:
        billing_service.decide_refund_request(
            db,
            actor=outsider,
            request_id=row.id,
            decision="APPROVED",
            idempotency_key="stage3-refund-unauthorized",
            explanation=None,
        )
    assert exc.value.code == "refund_decision_forbidden"
    assert db.get(MarzhelpAdminSettings, child.id).used_traffic == 50


MYSQL_URL = os.getenv("TEST_MYSQL_DATABASE_URL")


@pytest.mark.skipif(not MYSQL_URL, reason="TEST_MYSQL_DATABASE_URL is not configured")
def test_mysql_concurrent_refund_approval_credits_once(monkeypatch):
    assert make_url(MYSQL_URL).get_backend_name() == "mysql"
    engine = sa.create_engine(MYSQL_URL, pool_pre_ping=True)
    database = make_url(MYSQL_URL).database
    assert database and database.endswith("marzban_test")
    with engine.begin() as connection:
        connection.execute(sa.text("SET FOREIGN_KEY_CHECKS=0"))
        for table in sa.inspect(connection).get_table_names():
            escaped = table.replace("`", "``")
            connection.execute(sa.text(f"DROP TABLE `{escaped}`"))
        connection.execute(sa.text("SET FOREIGN_KEY_CHECKS=1"))
    alembic = Config("alembic.ini")
    alembic.set_main_option("sqlalchemy.url", MYSQL_URL)
    original_not_after = crypto.X509.gmtime_adj_notAfter
    monkeypatch.setattr(
        crypto.X509,
        "gmtime_adj_notAfter",
        lambda certificate, seconds: original_not_after(
            certificate,
            min(seconds, 2_000_000_000),
        ),
    )
    command.upgrade(alembic, "head")
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    seed = factory()
    owner = Admin(username="stage3-owner", hashed_password="x", is_sudo=True)
    child = Admin(username="stage3-child", hashed_password="x", is_sudo=False)
    seed.add_all([owner, child])
    seed.flush()
    seed.add_all(
        [
            MarzhelpAdminSettings(admin_id=owner.id, billing_mode="LEGACY_COMPAT"),
            MarzhelpAdminSettings(
                admin_id=child.id,
                billing_mode="ALLOCATED_TRAFFIC",
                total_traffic=100,
                used_traffic=50,
            ),
        ]
    )
    seed.commit()
    admin_hierarchy.set_owner(seed, owner.username)
    owner, child = seed.get(Admin, owner.id), seed.get(Admin, child.id)
    user = User(
        username="stage3-user",
        admin_id=child.id,
        status=UserStatus.active,
        data_limit=40,
        used_traffic=10,
        expire=2_000_000_000,
    )
    seed.add(user)
    seed.commit()
    row, _ = billing_service.create_refund_request(
        seed,
        actor=child,
        user=user,
        requested_refund_amount=30,
        request_reason="concurrency",
        request_note=None,
        correlation_id="stage3-mysql-concurrency",
        idempotency_key="stage3-mysql-refund-request",
    )
    request_id, owner_id, child_id = row.id, owner.id, child.id
    seed.close()

    def approve(key):
        session = factory()
        try:
            result, changed = billing_service.decide_refund_request(
                session,
                actor=session.get(Admin, owner_id),
                request_id=request_id,
                decision="APPROVED",
                idempotency_key=key,
                explanation="concurrent approval",
            )
            return result.status, changed
        except admin_hierarchy.HierarchyError as exc:
            return exc.code, False
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(approve, ("stage3-mysql-approve-a", "stage3-mysql-approve-b")))
    verify = factory()
    try:
        assert sum(changed for _, changed in outcomes) == 1
        assert verify.query(AdminCreditTransfer).filter_by(operation_type="allocated_refund").count() == 1
        assert verify.get(MarzhelpAdminSettings, child_id).used_traffic == 20
        assert verify.get(AllocatedTrafficRefundRequest, request_id).status == "APPROVED"
        assert verify.query(AllocatedTrafficRefundEvent).filter_by(
            request_id=request_id, to_status="APPROVED"
        ).count() == 1
    finally:
        verify.close()
        engine.dispose()
