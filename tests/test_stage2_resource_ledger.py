from concurrent.futures import ThreadPoolExecutor

import pytest
import sqlalchemy as sa
from fastapi import HTTPException
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from starlette.requests import Request

from app.db.base import Base
from app.db.models import (
    Admin,
    AdminAccountStatus,
    AdminAuditLog,
    AdminCreditTransfer,
    AdminHierarchySettings,
    AdminRole,
    AdminSuspensionReason,
    AdminUserCreationMode,
    MarzhelpAdminSettings,
)
from app.models.admin import Admin as APIAdmin
from app.models.admin import ManagedAdminCreate, MarzhelpAdminPolicy
from app.models.admin_hierarchy import CreditTransferRequest, RenewalPolicyUpdate
from app.routers.admin import create_managed_admin
from app.routers import admin_hierarchy as hierarchy_router
from app.routers.admin_hierarchy import grant_credit, reclaim_credit, update_renewal_policy
from app.utils import admin_hierarchy


GIB = 1024**3


def _request(path: str, method: str = "POST") -> Request:
    return Request(
        {
            "type": "http",
            "method": method,
            "path": path,
            "headers": [],
            "client": ("127.0.0.1", 5000),
        }
    )


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
    owner = Admin(username="owner", hashed_password="x", is_sudo=True)
    child = Admin(username="child", hashed_password="x", is_sudo=False)
    outsider = Admin(username="outsider", hashed_password="x", is_sudo=False)
    db.add_all([owner, child, outsider])
    db.flush()
    db.add_all(
        [
            MarzhelpAdminSettings(admin_id=owner.id, total_traffic=10_000 * GIB),
            MarzhelpAdminSettings(admin_id=child.id, total_traffic=0),
            MarzhelpAdminSettings(admin_id=outsider.id, total_traffic=0),
        ]
    )
    db.commit()
    admin_hierarchy.set_owner(db, owner.username)
    child_wallet = db.get(MarzhelpAdminSettings, child.id)
    outsider_wallet = db.get(MarzhelpAdminSettings, outsider.id)
    child_wallet.total_traffic = 0
    outsider_wallet.total_traffic = 0
    db.commit()
    return owner, child, outsider


@pytest.fixture()
def db(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'stage2.sqlite3'}")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def test_grant_and_reclaim_record_exact_balances_and_one_audit(db):
    owner, child, _ = _seed(db)
    actor = APIAdmin.model_validate(owner)
    grant = grant_credit(
        child.username,
        CreditTransferRequest(
            amount=30 * GIB,
            idempotency_key="stage2-grant-30-gib",
            note="monthly allocation",
        ),
        _request(f"/api/admin-management/{child.username}/credit/grant"),
        db,
        actor,
    )
    owner_wallet = db.get(MarzhelpAdminSettings, owner.id)
    child_wallet = db.get(MarzhelpAdminSettings, child.id)
    assert grant.resource == "traffic_credit"
    assert grant.delta == 30 * GIB
    assert (grant.balance_before, grant.balance_after) == (0, 30 * GIB)
    assert (grant.source_delegated_before, grant.source_delegated_after) == (0, 30 * GIB)
    assert owner_wallet.delegated_traffic == 30 * GIB
    assert child_wallet.total_traffic == 30 * GIB
    assert db.query(AdminAuditLog).filter_by(
        action="credit.grant", target_id=str(child.id)
    ).count() == 1

    duplicate = grant_credit(
        child.username,
        CreditTransferRequest(
            amount=30 * GIB,
            idempotency_key="stage2-grant-30-gib",
            note="monthly allocation",
        ),
        _request(f"/api/admin-management/{child.username}/credit/grant"),
        db,
        actor,
    )
    assert duplicate.id == grant.id
    assert db.query(AdminCreditTransfer).count() == 1
    assert db.query(AdminAuditLog).filter_by(action="credit.grant").count() == 1
    db.refresh(owner_wallet)
    db.refresh(child_wallet)
    assert owner_wallet.delegated_traffic == 30 * GIB
    assert child_wallet.total_traffic == 30 * GIB

    reclaimed = reclaim_credit(
        child.username,
        CreditTransferRequest(
            amount=30 * GIB,
            idempotency_key="stage2-reclaim-30-gib",
            note="unused allocation",
        ),
        _request(f"/api/admin-management/{child.username}/credit/reclaim"),
        db,
        actor,
    )
    assert reclaimed.delta == -30 * GIB
    assert (reclaimed.balance_before, reclaimed.balance_after) == (30 * GIB, 0)
    db.refresh(owner_wallet)
    db.refresh(child_wallet)
    assert owner_wallet.delegated_traffic == 0
    assert child_wallet.total_traffic == 0
    assert db.query(AdminAuditLog).filter_by(
        action="credit.reclaim", target_id=str(child.id)
    ).count() == 1


def test_over_reclaim_and_unauthorized_adjustment_are_rejected(db):
    owner, child, outsider = _seed(db)
    grant_credit(
        child.username,
        CreditTransferRequest(
            amount=30 * GIB,
            idempotency_key="stage2-grant-before-reclaim",
            note="allocation",
        ),
        _request("/api/admin-management/child/credit/grant"),
        db,
        APIAdmin.model_validate(owner),
    )
    with pytest.raises(HTTPException) as over_reclaim:
        reclaim_credit(
            child.username,
            CreditTransferRequest(
                amount=31 * GIB,
                idempotency_key="stage2-over-reclaim",
                note="invalid reclaim",
            ),
            _request("/api/admin-management/child/credit/reclaim"),
            db,
            APIAdmin.model_validate(owner),
        )
    assert over_reclaim.value.status_code == 400
    assert over_reclaim.value.detail["code"] == "reclaim_exceeds_available"

    with pytest.raises(HTTPException) as forbidden:
        grant_credit(
            child.username,
            CreditTransferRequest(
                amount=GIB,
                idempotency_key="stage2-forbidden-grant",
                note="out of scope",
            ),
            _request("/api/admin-management/child/credit/grant"),
            db,
            APIAdmin.model_validate(outsider),
        )
    assert forbidden.value.status_code == 403
    assert forbidden.value.detail["code"] == "credit_scope_forbidden"


def test_credit_and_audit_commit_or_rollback_together(db, monkeypatch):
    owner, child, _ = _seed(db)

    def fail_audit(*_args, **_kwargs):
        raise RuntimeError("simulated audit failure")

    monkeypatch.setattr(hierarchy_router.AuditLogService, "log", fail_audit)
    with pytest.raises(RuntimeError, match="simulated audit failure"):
        grant_credit(
            child.username,
            CreditTransferRequest(
                amount=30 * GIB,
                idempotency_key="stage2-audit-rollback",
                note="must be atomic",
            ),
            _request("/api/admin-management/child/credit/grant"),
            db,
            APIAdmin.model_validate(owner),
        )

    db.expire_all()
    assert db.query(AdminCreditTransfer).count() == 0
    assert db.get(MarzhelpAdminSettings, owner.id).delegated_traffic == 0
    assert db.get(MarzhelpAdminSettings, child.id).total_traffic == 0


def test_new_admin_initial_credit_uses_parent_funded_ledger(db):
    owner, _, _ = _seed(db)
    response = create_managed_admin(
        _request("/api/admin-management"),
        ManagedAdminCreate(
            username="new-child",
            password="secret-password",
            phone="+982100000000",
            role="ADMIN",
            policy=MarzhelpAdminPolicy(total_traffic=30 * GIB),
        ),
        db,
        APIAdmin.model_validate(owner),
    )
    child = db.query(Admin).filter_by(username="new-child").one()
    transfer = db.query(AdminCreditTransfer).filter_by(adjusted_admin_id=child.id).one()
    owner_wallet = db.get(MarzhelpAdminSettings, owner.id)
    child_wallet = db.get(MarzhelpAdminSettings, child.id)
    assert response.policy.total_traffic == 30 * GIB
    assert transfer.idempotency_key == f"admin-create-{child.id}-traffic-credit"
    assert transfer.delta == 30 * GIB
    assert transfer.note == "Initial admin traffic credit"
    assert owner_wallet.delegated_traffic == 30 * GIB
    assert child_wallet.total_traffic == 30 * GIB
    assert db.query(AdminAuditLog).filter_by(
        action="credit.grant", target_id=str(child.id)
    ).count() == 1


def test_renewal_policy_is_visible_and_parent_or_owner_authorized(db):
    owner, child, outsider = _seed(db)
    result = update_renewal_policy(
        child.username,
        RenewalPolicyUpdate(enabled=True, remaining=4),
        _request("/api/admin-management/child/renewal-policy", "PUT"),
        db,
        APIAdmin.model_validate(owner),
    )
    assert result == {"enabled": True, "remaining": 4}
    settings = db.get(MarzhelpAdminSettings, child.id)
    assert (settings.renewal_limit, settings.renewal_remaining, settings.renewals_used) == (4, 4, 0)
    assert db.query(AdminAuditLog).filter_by(action="admin.renewal_policy_update").count() == 1

    with pytest.raises(HTTPException) as forbidden:
        update_renewal_policy(
            child.username,
            RenewalPolicyUpdate(enabled=False, remaining=0),
            _request("/api/admin-management/child/renewal-policy", "PUT"),
            db,
            APIAdmin.model_validate(outsider),
        )
    assert forbidden.value.status_code == 403


def test_concurrent_reclaims_never_create_negative_or_unfunded_balance(tmp_path):
    database = tmp_path / "stage2-concurrent.sqlite3"
    engine = sa.create_engine(
        f"sqlite:///{database}",
        connect_args={"check_same_thread": False, "timeout": 2},
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    seed = factory()
    owner, child, _ = _seed(seed)
    owner_id, child_id = owner.id, child.id
    admin_hierarchy.transfer_credit(
        seed,
        actor=owner,
        source=owner,
        target=child,
        amount=60 * GIB,
        operation_type="grant",
        idempotency_key="stage2-concurrent-seed",
        note="concurrency seed",
    )
    seed.close()

    def reclaim(key: str):
        session = factory()
        try:
            return admin_hierarchy.transfer_credit(
                session,
                actor=session.get(Admin, owner_id),
                source=session.get(Admin, owner_id),
                target=session.get(Admin, child_id),
                amount=40 * GIB,
                operation_type="reclaim",
                idempotency_key=key,
                note="concurrent reclaim",
            ).id
        except (admin_hierarchy.HierarchyError, OperationalError) as exc:
            return type(exc).__name__
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(reclaim, ("stage2-concurrent-a", "stage2-concurrent-b")))

    verify = factory()
    try:
        owner_wallet = verify.get(MarzhelpAdminSettings, owner_id)
        child_wallet = verify.get(MarzhelpAdminSettings, child_id)
        successful_reclaims = verify.query(AdminCreditTransfer).filter_by(operation_type="reclaim").count()
        assert successful_reclaims == 1
        assert child_wallet.total_traffic == 20 * GIB
        assert owner_wallet.delegated_traffic == 20 * GIB
        assert any(isinstance(outcome, str) for outcome in outcomes)
        assert child_wallet.total_traffic >= 0
        assert owner_wallet.delegated_traffic >= 0
    finally:
        verify.close()
        engine.dispose()
