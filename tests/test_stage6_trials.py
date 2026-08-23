from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
import os

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from OpenSSL import crypto
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app import app as fastapi_app, xray
from app.db.base import Base
from app.db.models import (
    Admin,
    AdminAccountStatus,
    AdminCreditTransfer,
    AdminHierarchy,
    AdminHierarchySettings,
    AdminRole,
    AdminSuspensionReason,
    AdminUserCreationMode,
    MarzhelpAdminSettings,
    MarzhelpDeletedUser,
    ProxyHost,
    ProxyInbound,
    SystemOwner,
    TrialCleanupOperation,
    User,
    UserPlanAssignment,
)
from app.models.admin_hierarchy import PlanCreate, PlanVersionInput
from app.models.user import UserStatus
from app.utils import admin_hierarchy, admin_plans, trials
from app.utils.marzhelp_policy import MarzhelpPolicyError


GIB = 1024**3
MYSQL_URL = os.getenv("TEST_MYSQL_DATABASE_URL")


@pytest.fixture()
def db(tmp_path, monkeypatch):
    engine = sa.create_engine(
        f"sqlite:///{tmp_path / 'stage6.sqlite3'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    session.add_all(
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
    owner = Admin(username="owner", hashed_password="x", is_sudo=True)
    session.add(owner)
    session.flush()
    session.add_all(
        [
            SystemOwner(id=1, admin_id=owner.id),
            MarzhelpAdminSettings(
                admin_id=owner.id,
                billing_mode="USED_TRAFFIC",
                total_traffic=20 * GIB,
                trial_quota=20,
                can_manage_plans=True,
            ),
        ]
    )
    tag = "VLESS TRIAL"
    inbound = ProxyInbound(tag=tag)
    session.add(inbound)
    session.flush()
    host = ProxyHost(remark="trial {USERNAME}", address="trial.example", inbound=inbound)
    session.add(host)
    session.commit()
    inbound_config = {
        "tag": tag,
        "protocol": "vless",
        "network": "tcp",
        "tls": "none",
        "port": 443,
        "sni": [],
        "host": [],
        "path": "",
        "header_type": "none",
    }
    monkeypatch.setattr(xray.config, "inbounds_by_tag", {tag: inbound_config})
    monkeypatch.setattr(xray.config, "inbounds_by_protocol", {"vless": [inbound_config]})
    try:
        yield session, owner, tag, host
    finally:
        session.close()
        engine.dispose()


def _trial_plan(db, owner, tag, host_id, *, data_limit, devices, name):
    return admin_plans.create_plan(
        db,
        owner,
        PlanCreate(
            name=name,
            is_trial=True,
            version=PlanVersionInput(
                data_limit=data_limit,
                duration_days=1,
                concurrent_user_limit=devices,
                inbounds=[tag],
                hosts={tag: [host_id]},
            ),
        ),
    )


def test_stage6_api_contract_is_registered():
    methods_by_path = {
        route.path: set(route.methods or [])
        for route in fastapi_app.routes
        if hasattr(route, "methods")
    }
    assert "POST" in methods_by_path["/api/admin-management/{username}/trial-quota/grant"]
    assert "POST" in methods_by_path["/api/admin-management/{username}/trial-quota/reclaim"]
    assert "GET" in methods_by_path["/api/trials/cleanup/preview"]
    assert "POST" in methods_by_path["/api/trials/cleanup"]


@pytest.mark.parametrize(
    ("data_limit", "devices"),
    [(GIB, 1), (2 * GIB, 1), (0, 1), (0, 2)],
)
def test_required_trial_shapes_are_first_class_and_accounted(db, data_limit, devices):
    session, owner, tag, host = db
    plan = _trial_plan(
        session,
        owner,
        tag,
        host.id,
        data_limit=data_limit,
        devices=devices,
        name=f"trial-{data_limit}-{devices}",
    )
    before = session.get(MarzhelpAdminSettings, owner.id).trial_quota
    user, assignment, created = admin_plans.create_user_from_plan(
        session,
        actor=owner,
        plan_id=plan.id,
        username=f"shape-{data_limit}-{devices}",
        status="active",
        note=None,
        idempotency_key=f"stage6-shape-{data_limit}-{devices}",
    )
    assert created is True
    assert plan.is_trial is True
    assert assignment.is_trial is True
    assert user.data_limit == (data_limit or None)
    assert user.concurrent_user_limit == devices
    assert session.get(MarzhelpAdminSettings, owner.id).trial_quota == before - 1


def test_trial_quota_exhaustion_and_retry_consumes_once(db):
    session, owner, tag, host = db
    plan = _trial_plan(session, owner, tag, host.id, data_limit=GIB, devices=1, name="quota")
    settings = session.get(MarzhelpAdminSettings, owner.id)
    settings.trial_quota = 1
    session.commit()
    first = admin_plans.create_user_from_plan(
        session,
        actor=owner,
        plan_id=plan.id,
        username="once",
        status="active",
        note=None,
        idempotency_key="stage6-create-once",
    )
    replay = admin_plans.create_user_from_plan(
        session,
        actor=owner,
        plan_id=plan.id,
        username="once",
        status="active",
        note=None,
        idempotency_key="stage6-create-once",
    )
    assert first[2] is True and replay[2] is False
    assert session.get(MarzhelpAdminSettings, owner.id).trial_quota == 0
    assert session.get(MarzhelpAdminSettings, owner.id).trials_used == 1
    with pytest.raises((admin_hierarchy.HierarchyError, MarzhelpPolicyError)) as exc:
        admin_plans.create_user_from_plan(
            session,
            actor=owner,
            plan_id=plan.id,
            username="exhausted",
            status="active",
            note=None,
            idempotency_key="stage6-create-exhausted",
        )
    assert exc.value.code == "trial_quota_exhausted"


def test_unlimited_allocated_trial_with_finite_credit_fails_closed(db):
    session, owner, tag, host = db
    child = Admin(
        username="allocated-child",
        hashed_password="x",
        is_sudo=False,
        role_id=3,
        parent_admin_id=owner.id,
    )
    session.add(child)
    session.flush()
    session.add_all(
        [
            AdminHierarchy(ancestor_id=child.id, descendant_id=child.id, depth=0),
            AdminHierarchy(ancestor_id=owner.id, descendant_id=child.id, depth=1),
            MarzhelpAdminSettings(
                admin_id=child.id,
                billing_mode="ALLOCATED_TRAFFIC",
                total_traffic=10 * GIB,
                trial_quota=1,
            ),
        ]
    )
    session.commit()
    plan = admin_plans.create_plan(
        session,
        owner,
        PlanCreate(
            name="unsafe",
            is_trial=True,
            allowed_admin_ids=[child.id],
            version=PlanVersionInput(
                data_limit=0,
                duration_days=1,
                concurrent_user_limit=1,
                inbounds=[tag],
                hosts={tag: [host.id]},
            ),
        ),
    )
    with pytest.raises((admin_hierarchy.HierarchyError, MarzhelpPolicyError)) as exc:
        admin_plans.create_user_from_plan(
            session,
            actor=child,
            plan_id=plan.id,
            username="unsafe-unlimited",
            status="active",
            note=None,
            idempotency_key="stage6-unsafe-unlimited",
        )
    assert exc.value.code == "unlimited_traffic_forbidden"


def test_owner_trial_quota_grant_reclaim_is_idempotent_and_audited(db):
    session, owner, _, _ = db
    settings = session.get(MarzhelpAdminSettings, owner.id)
    settings.trial_quota = 0
    session.commit()
    granted, created = trials.adjust_quota(
        session,
        actor=owner,
        target=owner,
        amount=3,
        operation="grant",
        idempotency_key="stage6-trial-grant",
        note="test grant",
    )
    session.commit()
    replay, replay_created = trials.adjust_quota(
        session,
        actor=owner,
        target=owner,
        amount=3,
        operation="grant",
        idempotency_key="stage6-trial-grant",
        note="test grant",
    )
    assert created is True and replay_created is False and replay.id == granted.id
    assert session.get(MarzhelpAdminSettings, owner.id).trial_quota == 3
    reclaimed, _ = trials.adjust_quota(
        session,
        actor=owner,
        target=owner,
        amount=2,
        operation="reclaim",
        idempotency_key="stage6-trial-reclaim",
        note="test reclaim",
    )
    session.commit()
    assert reclaimed.resource == "trial_quota"
    assert session.get(MarzhelpAdminSettings, owner.id).trial_quota == 1


def test_cleanup_preview_and_execute_use_metadata_and_preserve_deleted_accounting(db):
    session, owner, tag, host = db
    plan = _trial_plan(session, owner, tag, host.id, data_limit=GIB, devices=1, name="cleanup")
    trial_user, _, _ = admin_plans.create_user_from_plan(
        session,
        actor=owner,
        plan_id=plan.id,
        username="cleanup-target",
        status="active",
        note="real trial",
        idempotency_key="stage6-cleanup-create",
    )
    trial_user.expire = int((datetime.now(timezone.utc) - timedelta(days=2)).timestamp())
    trial_user.used_traffic = 1234
    normal = User(
        username="normal-test-account",
        note="test trial looking note",
        status=UserStatus.expired,
        expire=int((datetime.now(timezone.utc) - timedelta(days=3)).timestamp()),
        admin=owner,
    )
    session.add(normal)
    session.commit()
    cutoff = datetime.now(timezone.utc) - timedelta(days=1)
    count, usernames = trials.cleanup_preview(session, owner, cutoff)
    assert count == 1
    assert usernames == [trial_user.username]

    operation, created = trials.cleanup(
        session,
        actor=owner,
        expired_before=cutoff,
        idempotency_key="stage6-cleanup-operation",
    )
    session.commit()
    assert created is True
    assert operation.deleted_usernames == [trial_user.username]
    assert session.get(User, trial_user.id) is None
    assert session.get(User, normal.id) is not None
    deleted = session.query(MarzhelpDeletedUser).filter_by(user_id=trial_user.id).one()
    assert deleted.used_traffic_total == 1234
    replay, replay_created = trials.cleanup(
        session,
        actor=owner,
        expired_before=cutoff,
        idempotency_key="stage6-cleanup-operation",
    )
    assert replay_created is False
    assert replay.id == session.query(TrialCleanupOperation.id).scalar()


@pytest.mark.skipif(not MYSQL_URL, reason="TEST_MYSQL_DATABASE_URL is not configured")
def test_mysql_stage6_migration_and_last_trial_quota_concurrency(monkeypatch):
    database = make_url(MYSQL_URL).database
    assert database and database.endswith("marzban_test")
    engine = sa.create_engine(MYSQL_URL, pool_pre_ping=True)
    original_not_after = crypto.X509.gmtime_adj_notAfter
    monkeypatch.setattr(
        crypto.X509,
        "gmtime_adj_notAfter",
        lambda certificate, seconds: original_not_after(
            certificate,
            min(seconds, 2_000_000_000),
        ),
    )
    with engine.begin() as connection:
        connection.execute(sa.text("SET FOREIGN_KEY_CHECKS=0"))
        for table in sa.inspect(connection).get_table_names():
            escaped = table.replace("`", "``")
            connection.execute(sa.text(f"DROP TABLE `{escaped}`"))
        connection.execute(sa.text("SET FOREIGN_KEY_CHECKS=1"))
    alembic = Config("alembic.ini")
    alembic.set_main_option("sqlalchemy.url", MYSQL_URL)
    command.upgrade(alembic, "3a7e5c1b8d42")
    with engine.begin() as connection:
        legacy_admin_id = connection.execute(
            sa.text(
                "INSERT INTO admins (username, hashed_password, is_sudo) "
                "VALUES ('stage6-legacy', 'x', 0)"
            )
        ).lastrowid
        connection.execute(
            sa.text("INSERT INTO marzhelp_admin_settings (admin_id) VALUES (:admin_id)"),
            {"admin_id": legacy_admin_id},
        )
        legacy_plan_id = connection.execute(
            sa.text(
                "INSERT INTO admin_user_plans (owner_admin_id, name) "
                "VALUES (:admin_id, 'legacy-commercial-plan')"
            ),
            {"admin_id": legacy_admin_id},
        ).lastrowid
    command.upgrade(alembic, "head")

    inspector = sa.inspect(engine)
    assert "trial_cleanup_operations" in inspector.get_table_names()
    assert {"trial_quota", "trials_used"} <= {
        column["name"] for column in inspector.get_columns("marzhelp_admin_settings")
    }
    assert "is_trial" in {
        column["name"] for column in inspector.get_columns("admin_user_plans")
    }
    assert any(
        index.get("column_names") == ["is_trial", "operation_type", "user_id"]
        for index in inspector.get_indexes("user_plan_assignments")
    )
    with engine.connect() as connection:
        assert connection.execute(
            sa.text(
                "SELECT trial_quota, trials_used FROM marzhelp_admin_settings "
                "WHERE admin_id=:admin_id"
            ),
            {"admin_id": legacy_admin_id},
        ).one() == (0, 0)
        assert connection.execute(
            sa.text("SELECT is_trial FROM admin_user_plans WHERE id=:plan_id"),
            {"plan_id": legacy_plan_id},
        ).scalar_one() == 0

    factory = sessionmaker(bind=engine, expire_on_commit=False)
    seed = factory()
    owner = Admin(username="stage6-mysql-owner", hashed_password="x", is_sudo=True, role_id=1)
    child = Admin(
        username="stage6-mysql-child",
        hashed_password="x",
        is_sudo=False,
        role_id=3,
        parent_admin_id=None,
    )
    seed.add_all([owner, child])
    seed.flush()
    child.parent_admin_id = owner.id
    seed.add_all(
        [
            SystemOwner(id=1, admin_id=owner.id),
            AdminHierarchy(ancestor_id=owner.id, descendant_id=owner.id, depth=0),
            AdminHierarchy(ancestor_id=child.id, descendant_id=child.id, depth=0),
            AdminHierarchy(ancestor_id=owner.id, descendant_id=child.id, depth=1),
            MarzhelpAdminSettings(
                admin_id=owner.id,
                billing_mode="USED_TRAFFIC",
                total_traffic=None,
                trial_quota=0,
                can_manage_plans=True,
            ),
            MarzhelpAdminSettings(
                admin_id=child.id,
                billing_mode="USED_TRAFFIC",
                total_traffic=10 * GIB,
                trial_quota=1,
            ),
        ]
    )
    tag = "VLESS MYSQL TRIAL"
    inbound = ProxyInbound(tag=tag)
    seed.add(inbound)
    seed.flush()
    host = ProxyHost(remark="mysql trial {USERNAME}", address="mysql.example", inbound=inbound)
    seed.add(host)
    seed.commit()
    inbound_config = {
        "tag": tag,
        "protocol": "vless",
        "network": "tcp",
        "tls": "none",
        "port": 443,
        "sni": [],
        "host": [],
        "path": "",
        "header_type": "none",
    }
    monkeypatch.setattr(xray.config, "inbounds_by_tag", {tag: inbound_config})
    monkeypatch.setattr(xray.config, "inbounds_by_protocol", {"vless": [inbound_config]})
    plan = admin_plans.create_plan(
        seed,
        owner,
        PlanCreate(
            name="mysql-trial",
            is_trial=True,
            allowed_admin_ids=[child.id],
            version=PlanVersionInput(
                data_limit=GIB,
                duration_days=1,
                concurrent_user_limit=1,
                inbounds=[tag],
                hosts={tag: [host.id]},
            ),
        ),
    )
    plan_id, child_id, owner_id = plan.id, child.id, owner.id
    seed.close()

    def create_trial(number: int):
        worker = factory()
        try:
            user, _, created = admin_plans.create_user_from_plan(
                worker,
                actor=worker.get(Admin, child_id),
                plan_id=plan_id,
                username=f"race-{number}",
                status="active",
                note=None,
                idempotency_key=f"stage6-mysql-race-{number}",
            )
            return "created" if created and user.id else "replayed"
        except (admin_hierarchy.HierarchyError, MarzhelpPolicyError) as exc:
            worker.rollback()
            return exc.code
        finally:
            worker.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = sorted(executor.map(create_trial, range(2)))

    def grant_same_key(_: int):
        worker = factory()
        try:
            row, _ = trials.adjust_quota(
                worker,
                actor=worker.get(Admin, owner_id),
                target=worker.get(Admin, child_id),
                amount=3,
                operation="grant",
                idempotency_key="stage6-mysql-same-grant",
                note="concurrent idempotent grant",
            )
            worker.commit()
            return row.id
        finally:
            worker.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        grant_ids = list(executor.map(grant_same_key, range(2)))
    verify = factory()
    try:
        assert outcomes == ["created", "trial_quota_exhausted"]
        assert grant_ids[0] == grant_ids[1]
        settings = verify.get(MarzhelpAdminSettings, child_id)
        assert settings.trial_quota == 3
        assert settings.trials_used == 1
        assert verify.query(UserPlanAssignment).filter_by(is_trial=True).count() == 1
        assert verify.query(AdminCreditTransfer).filter_by(
            idempotency_key="stage6-mysql-same-grant"
        ).count() == 1
    finally:
        verify.close()
        engine.dispose()
