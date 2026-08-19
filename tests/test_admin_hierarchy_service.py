from datetime import datetime, timedelta

import pytest
import sqlalchemy as sa
from sqlalchemy import event
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models import (
    Admin,
    AdminAccountStatus,
    AdminBulkJob,
    AdminHierarchySettings,
    AdminPlanCategoryAccess,
    AdminRole,
    AdminSuspensionReason,
    AdminUserCreationMode,
    MarzhelpAdminSettings,
    User,
    UserPlanAssignment,
)
from app.models.admin_hierarchy import PlanCategoryCreate, PlanCreate, PlanVersionInput
from app.models.admin import Admin as APIAdmin
from app.models.user import UserStatus
from app.routers.admin_hierarchy import get_admin_tree
from app.utils import admin_hierarchy, admin_plans, marzhelp_policy


@pytest.fixture()
def db():
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
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
    session.commit()
    try:
        yield session
    finally:
        session.close()


def _legacy_tree(db):
    owner = Admin(username="owner", hashed_password="x", is_sudo=True)
    sibling = Admin(username="sibling", hashed_password="x", is_sudo=True)
    leaf = Admin(username="leaf", hashed_password="x", is_sudo=False)
    db.add_all([owner, sibling, leaf])
    db.flush()
    db.add_all(
        [
            MarzhelpAdminSettings(admin_id=owner.id, total_traffic=10_000, calculate_volume="created_traffic"),
            MarzhelpAdminSettings(admin_id=sibling.id, total_traffic=0, calculate_volume="created_traffic"),
            MarzhelpAdminSettings(admin_id=leaf.id, total_traffic=0, calculate_volume="created_traffic"),
        ]
    )
    unowned = User(username="unowned", status=UserStatus.active)
    db.add(unowned)
    db.commit()
    report = admin_hierarchy.set_owner(db, "owner")
    db.refresh(owner)
    db.refresh(sibling)
    db.refresh(leaf)
    return owner, sibling, leaf, unowned, report


def test_set_owner_backfills_without_deleting_ids_or_users(db):
    owner, sibling, leaf, unowned, report = _legacy_tree(db)

    assert report["owner"] == "owner"
    assert report["admin_count"] == 3
    assert owner.role_id == admin_hierarchy.ROLE_IDS[admin_hierarchy.OWNER]
    assert owner.parent_admin_id is None
    assert sibling.role_id == admin_hierarchy.ROLE_IDS[admin_hierarchy.SUPER_ADMIN]
    assert leaf.role_id == admin_hierarchy.ROLE_IDS[admin_hierarchy.ADMIN]
    assert sibling.parent_admin_id == owner.id
    assert leaf.parent_admin_id == owner.id
    assert db.get(User, unowned.id).admin_id == owner.id
    assert admin_hierarchy.hierarchy_enabled(db)
    assert report["closure_rows"] == 5


def test_owner_credit_is_unlimited_for_plan_validation(db, monkeypatch):
    owner, _, _, _, _ = _legacy_tree(db)
    wallet = db.get(MarzhelpAdminSettings, owner.id)
    monkeypatch.setattr(
        admin_plans.xray.config,
        "inbounds_by_tag",
        {"VLESS TCP": {"tag": "VLESS TCP", "protocol": "vless"}},
    )

    assert wallet.total_traffic is None
    assert admin_hierarchy.available_credit(db, wallet) is None
    plan = admin_plans.create_plan(
        db,
        owner,
        PlanCreate(
            name="owner-unlimited",
            version=PlanVersionInput(
                data_limit=10**15,
                duration_days=30,
                inbounds=["VLESS TCP"],
            ),
        ),
    )

    assert plan.owner_admin_id == owner.id


def test_plan_category_assignment_controls_admin_access(db, monkeypatch):
    owner, sibling, leaf, _, _ = _legacy_tree(db)
    monkeypatch.setattr(
        admin_plans.xray.config,
        "inbounds_by_tag",
        {"VLESS TCP": {"tag": "VLESS TCP", "protocol": "vless"}},
    )
    category = admin_plans.create_category(
        db,
        owner,
        PlanCategoryCreate(name="reseller plans"),
    )
    admin_plans.replace_admin_categories(
        db,
        actor=owner,
        target=sibling,
        category_ids=[category.id],
    )
    db.commit()
    plan = admin_plans.create_plan(
        db,
        owner,
        PlanCreate(
            name="category-plan",
            category_id=category.id,
            version=PlanVersionInput(
                data_limit=100,
                duration_days=30,
                inbounds=["VLESS TCP"],
            ),
        ),
    )

    assert admin_plans.admin_category_ids(db, sibling.id) == [category.id]
    assert db.query(AdminPlanCategoryAccess).count() == 1
    assert admin_plans.can_use_plan(db, sibling, plan.id)
    assert not admin_plans.can_use_plan(db, leaf, plan.id)

    admin_plans.replace_admin_categories(
        db,
        actor=owner,
        target=sibling,
        category_ids=[],
    )
    db.commit()
    assert not admin_plans.can_use_plan(db, sibling, plan.id)


def test_scope_blocks_siblings_and_allows_ancestor(db):
    owner, sibling, leaf, _, _ = _legacy_tree(db)
    child = Admin(username="child", hashed_password="x", is_sudo=False)
    db.add(child)
    db.flush()
    db.add(MarzhelpAdminSettings(admin_id=child.id, calculate_volume="created_traffic"))
    admin_hierarchy.attach_new_child(
        db,
        actor=owner,
        parent=sibling,
        child=child,
        child_role=admin_hierarchy.ADMIN,
    )

    assert admin_hierarchy.admin_in_scope(db, sibling, child.id)
    assert not admin_hierarchy.admin_in_scope(db, leaf, child.id)
    assert not admin_hierarchy.admin_in_scope(db, child, sibling.id)
    assert admin_hierarchy.admin_in_scope(db, owner, leaf.id)


def test_admin_tree_uses_constant_query_count(db):
    owner, _, _, _, _ = _legacy_tree(db)
    statements: list[str] = []

    def capture(_connection, _cursor, statement, _parameters, _context, _many):
        statements.append(statement)

    engine = db.get_bind()
    event.listen(engine, "before_cursor_execute", capture)
    try:
        tree = get_admin_tree(
            db=db,
            admin=APIAdmin(id=owner.id, username=owner.username, is_sudo=True),
        )
    finally:
        event.remove(engine, "before_cursor_execute", capture)

    assert len(tree) == 1
    assert tree[0].username == owner.username
    assert len(tree[0].children) == 2
    assert len(statements) <= 4


def test_credit_transfer_is_idempotent_and_reclaim_is_bounded(db):
    owner, child, _, _, _ = _legacy_tree(db)
    owner_wallet = db.get(MarzhelpAdminSettings, owner.id)
    child_wallet = db.get(MarzhelpAdminSettings, child.id)
    owner_wallet.total_traffic = 1_000
    child_wallet.total_traffic = 0
    db.commit()

    first = admin_hierarchy.transfer_credit(
        db,
        actor=owner,
        source=owner,
        target=child,
        amount=300,
        operation_type="grant",
        idempotency_key="grant-test-0001",
    )
    duplicate = admin_hierarchy.transfer_credit(
        db,
        actor=owner,
        source=owner,
        target=child,
        amount=300,
        operation_type="grant",
        idempotency_key="grant-test-0001",
    )
    db.refresh(owner_wallet)
    db.refresh(child_wallet)
    assert duplicate.id == first.id
    assert owner_wallet.delegated_traffic == 300
    assert child_wallet.total_traffic == 300

    with pytest.raises(admin_hierarchy.HierarchyError) as conflict:
        admin_hierarchy.transfer_credit(
            db,
            actor=owner,
            source=owner,
            target=child,
            amount=299,
            operation_type="grant",
            idempotency_key="grant-test-0001",
        )
    assert conflict.value.code == "idempotency_conflict"

    with pytest.raises(admin_hierarchy.HierarchyError) as raised:
        admin_hierarchy.transfer_credit(
            db,
            actor=owner,
            source=owner,
            target=child,
            amount=301,
            operation_type="reclaim",
            idempotency_key="reclaim-test-0001",
        )
    assert raised.value.code == "reclaim_exceeds_available"

    reclaimed = admin_hierarchy.transfer_credit(
        db,
        actor=owner,
        source=owner,
        target=child,
        amount=100,
        operation_type="reclaim",
        idempotency_key="reclaim-test-0002",
    )
    assert reclaimed.from_admin_id == child.id
    assert reclaimed.to_admin_id == owner.id


def test_zero_credit_is_finite_after_hierarchy_activation(db):
    _, child, _, _, _ = _legacy_tree(db)
    wallet = db.get(MarzhelpAdminSettings, child.id)
    wallet.total_traffic = 0
    wallet.calculate_volume = "created_traffic"
    db.commit()

    with pytest.raises(marzhelp_policy.MarzhelpPolicyError) as raised:
        marzhelp_policy._validate_traffic_credit(db, wallet, allocated_charge=1)
    assert raised.value.code == "traffic_exhausted"
    assert admin_hierarchy.automatic_suspension_reason(db, wallet) == 2

    wallet.total_traffic = None
    db.commit()
    assert admin_hierarchy.automatic_suspension_reason(db, wallet) is None


def test_bulk_disable_resumes_from_persisted_cursor(db):
    owner, child, _, _, _ = _legacy_tree(db)
    users = [User(username=f"bulk-{index}", admin_id=child.id, status=UserStatus.active) for index in range(4)]
    db.add_all(users)
    db.commit()
    users[0].status = UserStatus.disabled
    job = AdminBulkJob(
        actor_admin_id=owner.id,
        target_admin_id=child.id,
        operation="disable",
        include_subtree=False,
        status="processing",
        total_count=4,
        processed_count=1,
        last_user_id=users[0].id,
        idempotency_key="bulk-resume-0001",
    )
    db.add(job)
    db.commit()

    resumed = admin_hierarchy.run_disable_job(
        db,
        actor=owner,
        target=child,
        include_subtree=False,
        idempotency_key="bulk-resume-0001",
        batch_size=1,
    )
    assert resumed.status == "complete"
    assert resumed.processed_count == 4
    assert all(db.get(User, user.id).status == UserStatus.disabled for user in users)


def test_external_api_token_revoke_invalidates_active_token(db):
    owner, child, _, _, _ = _legacy_tree(db)
    child.external_api_enabled = True
    db.commit()
    row, plaintext = admin_hierarchy.issue_api_token(
        db,
        owner=owner,
        target=child,
        name="automation",
        scopes={"users:read"},
        expires_at=datetime.utcnow() + timedelta(hours=1),
    )

    authenticated, scopes = admin_hierarchy.authenticate_api_token(db, plaintext)
    assert authenticated.id == child.id
    assert scopes == {"users:read"}
    assert admin_hierarchy.revoke_api_access(db, owner, child) == 1
    assert admin_hierarchy.authenticate_api_token(db, plaintext) is None
    assert db.get(type(row), row.id).revoked_at is not None


def test_suspend_resume_restores_only_users_changed_by_event(db):
    owner, child, _, _, _ = _legacy_tree(db)
    active = User(username="active-child", admin_id=child.id, status=UserStatus.active)
    disabled = User(username="disabled-child", admin_id=child.id, status=UserStatus.disabled)
    db.add_all([active, disabled])
    db.commit()

    event = admin_hierarchy.suspend_admin(
        db,
        actor=owner,
        target=child,
        reason_id=1,
        include_subtree=True,
        batch_size=1,
    )
    db.refresh(active)
    db.refresh(disabled)
    assert active.status == UserStatus.disabled
    assert disabled.status == UserStatus.disabled
    assert event.status == "complete"

    restored = admin_hierarchy.resume_admin(db, actor=owner, target=child)
    db.refresh(active)
    db.refresh(disabled)
    assert restored == 1
    assert active.status == UserStatus.active
    assert disabled.status == UserStatus.disabled


def test_plan_updates_append_immutable_version(db, monkeypatch):
    owner, child, _, _, _ = _legacy_tree(db)
    monkeypatch.setattr(
        admin_plans.xray.config,
        "inbounds_by_tag",
        {"VLESS TCP": {"tag": "VLESS TCP", "protocol": "vless"}},
    )
    values = PlanCreate(
        name="standard",
        version=PlanVersionInput(
            data_limit=100,
            duration_days=30,
            concurrent_user_limit=1,
            inbounds=["VLESS TCP"],
        ),
        allowed_admin_ids=[child.id],
    )
    plan = admin_plans.create_plan(db, owner, values)
    first_version = plan.current_version_id
    update = values.model_dump(exclude={"name"})
    update["version"]["data_limit"] = 200
    updated = admin_plans.update_plan(db, owner, plan, admin_plans.PlanUpdate(**update))

    assert updated.current_version_id != first_version
    response = admin_plans.plan_response(db, updated)
    assert response.version_number == 2
    assert response.version.data_limit == 200
    assert admin_plans.can_use_plan(db, child, plan.id)

    replay_user = User(username="idempotency-owner", admin_id=owner.id, status=UserStatus.active)
    db.add(replay_user)
    db.flush()
    db.add(
        UserPlanAssignment(
            user_id=replay_user.id,
            plan_id=plan.id,
            version_id=updated.current_version_id,
            actor_admin_id=owner.id,
            operation_type="create",
            idempotency_key="plan-replay-0001",
        )
    )
    db.commit()
    with pytest.raises(admin_hierarchy.HierarchyError) as conflict:
        admin_plans._assignment_replay(
            db,
            actor=child,
            plan_id=plan.id,
            username=replay_user.username,
            operation_type="create",
            idempotency_key="plan-replay-0001",
        )
    assert conflict.value.code == "idempotency_conflict"
