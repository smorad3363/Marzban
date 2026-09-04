import sqlalchemy as sa
import pytest
from fastapi import BackgroundTasks, HTTPException
from starlette.requests import Request
from sqlalchemy.orm import sessionmaker

from app.db import crud
from app.db.base import Base
from app.db.models import (
    AdminUserPlan,
    AdminUserPlanHost,
    AdminUserPlanInbound,
    AdminUserPlanVersion,
    ProxyHost,
    ProxyInbound,
    User,
    UserPlanAssignment,
)
from app.models.proxy import ProxyHost as ProxyHostModify
from app.models.user import UserStatus
from app.utils.network_impact import analyze_host_update
from app.routers.system import modify_hosts
from app.utils import admin_plans


def _session():
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _host(*, host_id: int | None = None, address: str = "one.example") -> ProxyHostModify:
    return ProxyHostModify(
        id=host_id,
        remark="stable {USERNAME}",
        address=address,
    )


def test_update_hosts_preserves_existing_host_id():
    db = _session()
    try:
        inbound = ProxyInbound(tag="VLESS TCP")
        existing = ProxyHost(
            remark="stable {USERNAME}",
            address="one.example",
            inbound=inbound,
        )
        db.add(inbound)
        db.commit()
        existing_id = existing.id

        crud.update_hosts(
            db,
            inbound.tag,
            [_host(host_id=existing_id, address="renamed.example")],
        )

        rows = db.query(ProxyHost).filter(ProxyHost.inbound_tag == inbound.tag).all()
        assert [(row.id, row.address) for row in rows] == [
            (existing_id, "renamed.example")
        ]
    finally:
        db.close()


def test_update_hosts_is_transaction_neutral(monkeypatch):
    db = _session()
    try:
        inbound = ProxyInbound(tag="VLESS TCP")
        db.add(inbound)
        db.commit()
        commits = []
        monkeypatch.setattr(db, "commit", lambda: commits.append(True))

        crud.update_hosts(db, inbound.tag, [_host()])

        assert commits == []
        assert db.query(ProxyHost).filter(ProxyHost.inbound_tag == inbound.tag).count() == 1
    finally:
        db.close()


def _plan_assignment(db, host_id: int, tag: str):
    plan = AdminUserPlan(owner_admin_id=1, name="affected")
    db.add(plan)
    db.flush()
    version = AdminUserPlanVersion(
        plan_id=plan.id,
        version_number=1,
        price_toman=100,
        data_limit=1024,
        duration_days=30,
        reset_strategy="no_reset",
        renewal_volume_strategy="replace",
        renewal_time_strategy="extend_max",
        created_by_admin_id=1,
    )
    db.add(version)
    db.flush()
    plan.current_version_id = version.id
    db.add_all([
        AdminUserPlanInbound(version_id=version.id, inbound_tag=tag),
        AdminUserPlanHost(version_id=version.id, inbound_tag=tag, host_id=host_id),
    ])
    user = User(username="active-user", status=UserStatus.active, admin_id=1)
    db.add(user)
    db.flush()
    db.add(UserPlanAssignment(
        user_id=user.id,
        plan_id=plan.id,
        version_id=version.id,
        actor_admin_id=1,
        operation_type="create",
        idempotency_key="stage2-impact",
    ))
    db.commit()
    return plan, version


def test_host_impact_counts_plan_versions_and_active_users():
    db = _session()
    try:
        inbound = ProxyInbound(tag="VLESS TCP")
        host = ProxyHost(remark="stable {USERNAME}", address="one.example", inbound=inbound)
        db.add(inbound)
        db.commit()
        plan, version = _plan_assignment(db, host.id, inbound.tag)

        impact = analyze_host_update(
            db,
            {inbound.tag: [_host(host_id=host.id, address="changed.example")]},
        )

        assert impact.affected_plan_ids == [plan.id]
        assert impact.affected_version_ids == [version.id]
        assert impact.affected_plan_count == 1
        assert impact.affected_plan_version_count == 1
        assert impact.active_user_count == 1
        assert impact.invalid_plan_ids == []
    finally:
        db.close()


def test_host_impact_marks_plan_invalid_when_only_host_is_removed():
    db = _session()
    try:
        inbound = ProxyInbound(tag="VLESS TCP")
        host = ProxyHost(remark="stable {USERNAME}", address="one.example", inbound=inbound)
        db.add(inbound)
        db.commit()
        plan, _ = _plan_assignment(db, host.id, inbound.tag)

        impact = analyze_host_update(db, {inbound.tag: []})

        assert impact.removed_host_ids == [host.id]
        assert impact.invalid_plan_ids == [plan.id]
    finally:
        db.close()


def test_host_impact_keeps_plan_valid_when_another_selected_host_remains():
    db = _session()
    try:
        inbound = ProxyInbound(tag="VLESS TCP")
        removed = ProxyHost(remark="removed {USERNAME}", address="one.example", inbound=inbound)
        retained = ProxyHost(remark="retained {USERNAME}", address="two.example", inbound=inbound)
        db.add(inbound)
        db.commit()
        plan, version = _plan_assignment(db, removed.id, inbound.tag)
        db.add(AdminUserPlanHost(version_id=version.id, inbound_tag=inbound.tag, host_id=retained.id))
        db.commit()

        impact = analyze_host_update(
            db,
            {inbound.tag: [_host(host_id=retained.id, address="two.example")]},
        )

        assert impact.affected_plan_ids == [plan.id]
        assert impact.invalid_plan_ids == []
    finally:
        db.close()


def test_host_mutation_requires_explicit_action_and_keeps_db_unchanged(monkeypatch):
    db = _session()
    try:
        inbound = ProxyInbound(tag="VLESS TCP")
        host = ProxyHost(remark="stable {USERNAME}", address="one.example", inbound=inbound)
        db.add(inbound)
        db.commit()
        _plan_assignment(db, host.id, inbound.tag)
        monkeypatch.setattr(
            "app.routers.system.xray.config.inbounds_by_tag",
            {inbound.tag: {"tag": inbound.tag}},
        )
        request = Request({"type": "http", "method": "PUT", "path": "/api/hosts", "headers": []})

        with pytest.raises(HTTPException) as raised:
            modify_hosts(
                request=request,
                bg=BackgroundTasks(),
                modified_hosts={inbound.tag: [_host(host_id=host.id, address="changed.example")]},
                impact_action=None,
                db=db,
                admin=type("Admin", (), {"username": "owner"})(),
            )

        assert raised.value.status_code == 409
        assert raised.value.detail["error_code"] == "host_change_confirmation_required"
        assert raised.value.detail["message"] == "این تغییر روی 1 پلن و 1 کاربر فعال اثر می‌گذارد. روش اعمال را انتخاب کنید."
        db.expire_all()
        assert db.get(ProxyHost, host.id).address == "one.example"
    finally:
        db.close()


def test_future_only_network_revision_preserves_assignment_and_financial_snapshot():
    db = _session()
    try:
        inbound = ProxyInbound(tag="VLESS TCP")
        first = ProxyHost(remark="first {USERNAME}", address="one.example", inbound=inbound)
        second = ProxyHost(remark="second {USERNAME}", address="two.example", inbound=inbound)
        db.add(inbound)
        db.commit()
        plan, previous = _plan_assignment(db, first.id, inbound.tag)
        assignment = db.query(UserPlanAssignment).one()

        old, revision = admin_plans.add_network_revision(
            db,
            actor=type("Admin", (), {"id": 1})(),
            plan=plan,
            inbounds={inbound.tag},
            hosts={inbound.tag: {second.id}},
        )
        db.flush()

        assert old.id == previous.id
        assert plan.current_version_id == revision.id
        assert revision.price_toman == previous.price_toman
        assert revision.data_limit == previous.data_limit
        assert revision.duration_days == previous.duration_days
        assert assignment.version_id == previous.id
        assert db.query(UserPlanAssignment).count() == 1
    finally:
        db.close()


def test_legacy_host_is_hidden_from_editor_but_available_to_runtime():
    db = _session()
    try:
        inbound = ProxyInbound(tag="VLESS TCP")
        host = ProxyHost(
            remark="legacy {USERNAME}",
            address="legacy.example",
            inbound=inbound,
            is_legacy=True,
        )
        db.add(inbound)
        db.commit()

        assert [row.id for row in crud.get_hosts(db, inbound.tag)] == [host.id]
        assert crud.get_hosts(db, inbound.tag, include_legacy=False) == []
    finally:
        db.close()


def _owner():
    return type("Admin", (), {"id": 1, "username": "owner"})()


def _request():
    return Request({
        "type": "http",
        "method": "PUT",
        "path": "/api/hosts",
        "headers": [],
        "client": ("127.0.0.1", 1234),
    })


def _runtime(monkeypatch, tag: str):
    inbound = {"tag": tag, "protocol": "vless"}
    monkeypatch.setattr("app.routers.system.xray.config.inbounds_by_tag", {tag: inbound})
    monkeypatch.setattr("app.utils.admin_plans.xray.config.inbounds_by_tag", {tag: inbound})
    monkeypatch.setattr("app.utils.admin_plans.xray.config.inbounds_by_protocol", {"vless": [inbound]})
    monkeypatch.setattr("app.routers.system.xray.hosts.update", lambda: None)


def test_future_only_endpoint_retires_old_host_and_preserves_current_assignment(monkeypatch):
    db = _session()
    try:
        tag = "VLESS TCP"
        inbound = ProxyInbound(tag=tag)
        host = ProxyHost(remark="old {USERNAME}", address="old.example", inbound=inbound)
        db.add(inbound)
        db.commit()
        plan, previous = _plan_assignment(db, host.id, tag)
        _runtime(monkeypatch, tag)

        modify_hosts(
            request=_request(),
            bg=BackgroundTasks(),
            modified_hosts={tag: [_host(host_id=host.id, address="new.example")]},
            impact_action="future_only",
            db=db,
            admin=_owner(),
        )

        db.expire_all()
        old = db.get(ProxyHost, host.id)
        active_hosts = crud.get_hosts(db, tag, include_legacy=False)
        assert old.is_legacy is True
        assert [(row.address, row.is_legacy) for row in active_hosts] == [("new.example", False)]
        assert plan.current_version_id != previous.id
        assert db.query(UserPlanAssignment).one().version_id == previous.id
    finally:
        db.close()


def test_detach_endpoint_creates_revision_and_syncs_active_user(monkeypatch):
    db = _session()
    try:
        tag = "VLESS TCP"
        inbound = ProxyInbound(tag=tag)
        removed = ProxyHost(remark="removed {USERNAME}", address="one.example", inbound=inbound)
        retained = ProxyHost(remark="retained {USERNAME}", address="two.example", inbound=inbound)
        db.add(inbound)
        db.commit()
        removed_id = removed.id
        plan, previous = _plan_assignment(db, removed.id, tag)
        db.add(AdminUserPlanHost(version_id=previous.id, inbound_tag=tag, host_id=retained.id))
        db.commit()
        _runtime(monkeypatch, tag)
        bg = BackgroundTasks()

        modify_hosts(
            request=_request(),
            bg=bg,
            modified_hosts={tag: [_host(host_id=retained.id, address="two.example")]},
            impact_action="detach",
            db=db,
            admin=_owner(),
        )

        db.expire_all()
        assert db.get(ProxyHost, removed_id) is None
        assert plan.current_version_id != previous.id
        assignments = db.query(UserPlanAssignment).order_by(UserPlanAssignment.id).all()
        assert [row.operation_type for row in assignments] == ["create", "network_sync"]
        assert assignments[-1].version_id == plan.current_version_id
        assert len(bg.tasks) == 1
    finally:
        db.close()
