"""Versioned, scoped administrator plans and immutable user assignments."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, exists, func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import xray
from app.db import crud
from app.db.models import (
    Admin,
    AdminHierarchy,
    AdminPlanCategory,
    AdminPlanCategoryAccess,
    AdminUserPlan,
    AdminUserPlanAccess,
    AdminUserPlanInbound,
    AdminUserPlanVersion,
    MarzhelpAdminSettings,
    User,
    UserPlanAssignment,
    UserUsageResetLogs,
)
from app.models.admin_hierarchy import (
    PlanCategoryCreate,
    PlanCategoryResponse,
    PlanCategoryUpdate,
    PlanCreate,
    PlanResponse,
    PlanUpdate,
    PlanVersionInput,
)
from app.models.proxy import ProxyTypes
from app.models.user import UserCreate, UserDataLimitResetStrategy, UserStatus, UserStatusCreate
from app.utils import admin_hierarchy


def _can_manage_plans(db: Session, actor: Admin) -> bool:
    if admin_hierarchy.is_owner(db, actor):
        return True
    settings = db.get(MarzhelpAdminSettings, actor.id)
    return (
        admin_hierarchy.role_code(actor) == admin_hierarchy.SUPER_ADMIN
        and bool(settings and settings.can_manage_plans)
    )


def effective_categories_query(db: Session, actor: Admin):
    query = db.query(AdminPlanCategory).filter(AdminPlanCategory.archived_at.is_(None))
    if admin_hierarchy.is_owner(db, actor):
        return query
    assigned = exists().where(
        and_(
            AdminPlanCategoryAccess.category_id == AdminPlanCategory.id,
            AdminPlanCategoryAccess.admin_id == actor.id,
        )
    )
    return query.filter(or_(AdminPlanCategory.owner_admin_id == actor.id, assigned))


def category_response(
    db: Session,
    category: AdminPlanCategory,
    plan_count: int | None = None,
) -> PlanCategoryResponse:
    return PlanCategoryResponse(
        id=category.id,
        owner_admin_id=category.owner_admin_id,
        name=category.name,
        description=category.description,
        archived_at=category.archived_at,
        plan_count=plan_count if plan_count is not None else (
            db.query(func.count(AdminUserPlan.id))
            .filter(
                AdminUserPlan.category_id == category.id,
                AdminUserPlan.archived_at.is_(None),
            )
            .scalar()
            or 0
        ),
    )


def category_responses(
    db: Session,
    categories: list[AdminPlanCategory],
) -> list[PlanCategoryResponse]:
    category_ids = [category.id for category in categories]
    counts = (
        dict(
            db.query(AdminUserPlan.category_id, func.count(AdminUserPlan.id))
            .filter(
                AdminUserPlan.category_id.in_(category_ids),
                AdminUserPlan.archived_at.is_(None),
            )
            .group_by(AdminUserPlan.category_id)
            .all()
        )
        if category_ids
        else {}
    )
    return [
        category_response(db, category, int(counts.get(category.id, 0)))
        for category in categories
    ]


def create_category(
    db: Session,
    actor: Admin,
    values: PlanCategoryCreate,
) -> AdminPlanCategory:
    if not _can_manage_plans(db, actor):
        raise admin_hierarchy.HierarchyError("plan_management_forbidden", "Plan management is not enabled")
    category = AdminPlanCategory(
        owner_admin_id=actor.id,
        name=values.name.strip(),
        description=values.description,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def update_category(
    db: Session,
    actor: Admin,
    category: AdminPlanCategory,
    values: PlanCategoryUpdate,
) -> AdminPlanCategory:
    if not admin_hierarchy.is_owner(db, actor) and category.owner_admin_id != actor.id:
        raise admin_hierarchy.HierarchyError("category_update_forbidden", "Only category owner can update it")
    if not _can_manage_plans(db, actor):
        raise admin_hierarchy.HierarchyError("plan_management_forbidden", "Plan management is not enabled")
    category.name = values.name.strip()
    category.description = values.description
    db.commit()
    db.refresh(category)
    return category


def archive_category(db: Session, actor: Admin, category: AdminPlanCategory) -> None:
    if not admin_hierarchy.is_owner(db, actor) and category.owner_admin_id != actor.id:
        raise admin_hierarchy.HierarchyError("category_archive_forbidden", "Only category owner can archive it")
    active_plans = db.query(AdminUserPlan.id).filter(
        AdminUserPlan.category_id == category.id,
        AdminUserPlan.archived_at.is_(None),
    ).first()
    if active_plans:
        raise admin_hierarchy.HierarchyError(
            "category_in_use",
            "Archive or move active plans before archiving this category",
        )
    category.archived_at = admin_hierarchy.utc_now_naive()
    db.commit()


def admin_category_ids(db: Session, admin_id: int) -> list[int]:
    return [
        row[0]
        for row in db.query(AdminPlanCategoryAccess.category_id)
        .filter(AdminPlanCategoryAccess.admin_id == admin_id)
        .order_by(AdminPlanCategoryAccess.category_id)
        .all()
    ]


def admin_category_ids_map(db: Session, admin_ids: list[int]) -> dict[int, list[int]]:
    result = {admin_id: [] for admin_id in admin_ids}
    if not admin_ids:
        return result
    for admin_id, category_id in (
        db.query(AdminPlanCategoryAccess.admin_id, AdminPlanCategoryAccess.category_id)
        .filter(AdminPlanCategoryAccess.admin_id.in_(admin_ids))
        .order_by(AdminPlanCategoryAccess.admin_id, AdminPlanCategoryAccess.category_id)
        .all()
    ):
        result[admin_id].append(category_id)
    return result


def replace_admin_categories(
    db: Session,
    *,
    actor: Admin,
    target: Admin,
    category_ids: list[int],
) -> None:
    if not admin_hierarchy.admin_in_scope(db, actor, target.id):
        raise admin_hierarchy.HierarchyError("admin_scope_forbidden", "Administrator is outside actor scope")
    wanted = sorted(set(category_ids))
    available = {
        row[0]
        for row in effective_categories_query(db, actor)
        .with_entities(AdminPlanCategory.id)
        .filter(AdminPlanCategory.id.in_(wanted))
        .all()
    } if wanted else set()
    if available != set(wanted):
        raise admin_hierarchy.HierarchyError(
            "category_access_forbidden",
            "One or more plan categories are unavailable to the assigning administrator",
        )
    db.query(AdminPlanCategoryAccess).filter(
        AdminPlanCategoryAccess.admin_id == target.id
    ).delete(synchronize_session=False)
    db.add_all(
        AdminPlanCategoryAccess(
            category_id=category_id,
            admin_id=target.id,
            assigned_by_admin_id=actor.id,
        )
        for category_id in wanted
    )
    db.flush()


def _validate_category(db: Session, actor: Admin, category_id: int | None) -> None:
    if category_id is None:
        return
    category = effective_categories_query(db, actor).filter(AdminPlanCategory.id == category_id).first()
    if category is None:
        raise admin_hierarchy.HierarchyError("category_access_forbidden", "Plan category is unavailable")


def _validate_version(db: Session, actor: Admin, version: PlanVersionInput) -> None:
    settings = db.get(MarzhelpAdminSettings, actor.id)
    if settings is None:
        raise admin_hierarchy.HierarchyError("policy_missing", "Administrator policy is missing")
    if settings.max_user_duration_days and version.duration_days > settings.max_user_duration_days:
        raise admin_hierarchy.HierarchyError("duration_exceeded", "Plan duration exceeds administrator limit")
    if not settings.all_user_limits and version.concurrent_user_limit is not None:
        if version.concurrent_user_limit not in settings.allowed_user_limits:
            raise admin_hierarchy.HierarchyError("user_limit_forbidden", "Plan device limit is not allowed")
    if not settings.all_inbounds:
        unauthorized = set(version.inbounds) - set(settings.allowed_inbounds)
        if unauthorized:
            raise admin_hierarchy.HierarchyError(
                "inbound_forbidden", f"Plan contains unauthorized inbounds: {sorted(unauthorized)}"
            )
    unknown = set(version.inbounds) - set(xray.config.inbounds_by_tag)
    if unknown:
        raise admin_hierarchy.HierarchyError("unknown_inbound", f"Unknown inbounds: {sorted(unknown)}")
    available = admin_hierarchy.available_credit(db, settings)
    if version.data_limit == 0 and available is not None:
        raise admin_hierarchy.HierarchyError("unlimited_traffic_forbidden", "Finite credit cannot create unlimited plans")
    if available is not None and version.data_limit > available:
        raise admin_hierarchy.HierarchyError("credit_exhausted", "Plan volume exceeds available credit")


def _validate_access_targets(db: Session, actor: Admin, admin_ids: list[int]) -> None:
    existing = {
        row[0] for row in db.query(Admin.id).filter(Admin.id.in_(set(admin_ids))).all()
    } if admin_ids else set()
    if existing != set(admin_ids):
        raise admin_hierarchy.HierarchyError("admin_not_found", "One or more plan access targets do not exist")
    for admin_id in existing:
        if not admin_hierarchy.admin_in_scope(db, actor, admin_id):
            raise admin_hierarchy.HierarchyError("plan_access_scope_forbidden", "Plan access target is outside scope")


def _replace_access(
    db: Session,
    plan: AdminUserPlan,
    admin_ids: list[int],
    include_subtree: bool,
) -> None:
    db.query(AdminUserPlanAccess).filter(AdminUserPlanAccess.plan_id == plan.id).delete(
        synchronize_session=False
    )
    db.add_all(
        AdminUserPlanAccess(
            admin_id=admin_id,
            plan_id=plan.id,
            include_subtree=include_subtree,
        )
        for admin_id in sorted(set(admin_ids))
    )


def _add_version(
    db: Session,
    plan: AdminUserPlan,
    actor: Admin,
    values: PlanVersionInput,
) -> AdminUserPlanVersion:
    number = (
        db.query(func.max(AdminUserPlanVersion.version_number))
        .filter(AdminUserPlanVersion.plan_id == plan.id)
        .scalar()
        or 0
    ) + 1
    version = AdminUserPlanVersion(
        plan_id=plan.id,
        version_number=number,
        data_limit=values.data_limit,
        duration_days=values.duration_days,
        concurrent_user_limit=values.concurrent_user_limit,
        reset_strategy=values.reset_strategy,
        renewal_volume_strategy=values.renewal_volume_strategy,
        renewal_time_strategy=values.renewal_time_strategy,
        created_by_admin_id=actor.id,
    )
    db.add(version)
    db.flush()
    db.add_all(
        AdminUserPlanInbound(version_id=version.id, inbound_tag=tag)
        for tag in values.inbounds
    )
    plan.current_version_id = version.id
    return version


def create_plan(db: Session, actor: Admin, values: PlanCreate) -> AdminUserPlan:
    if not _can_manage_plans(db, actor):
        raise admin_hierarchy.HierarchyError("plan_management_forbidden", "Plan management is not enabled")
    _validate_version(db, actor, values.version)
    _validate_category(db, actor, values.category_id)
    _validate_access_targets(db, actor, values.allowed_admin_ids)
    plan = AdminUserPlan(
        owner_admin_id=actor.id,
        category_id=values.category_id,
        name=values.name.strip(),
        description=values.description,
    )
    try:
        db.add(plan)
        db.flush()
        _add_version(db, plan, actor, values.version)
        _replace_access(db, plan, values.allowed_admin_ids, values.include_subtree)
        db.commit()
        db.refresh(plan)
        return plan
    except Exception:
        db.rollback()
        raise


def update_plan(db: Session, actor: Admin, plan: AdminUserPlan, values: PlanUpdate) -> AdminUserPlan:
    if not admin_hierarchy.is_owner(db, actor) and plan.owner_admin_id != actor.id:
        raise admin_hierarchy.HierarchyError("plan_update_forbidden", "Only plan owner can update this plan")
    if not _can_manage_plans(db, actor):
        raise admin_hierarchy.HierarchyError("plan_management_forbidden", "Plan management is not enabled")
    _validate_version(db, actor, values.version)
    _validate_category(db, actor, values.category_id)
    _validate_access_targets(db, actor, values.allowed_admin_ids)
    plan = db.query(AdminUserPlan).filter(AdminUserPlan.id == plan.id).with_for_update().one()
    plan.description = values.description
    plan.category_id = values.category_id
    _add_version(db, plan, actor, values.version)
    _replace_access(db, plan, values.allowed_admin_ids, values.include_subtree)
    db.commit()
    db.refresh(plan)
    return plan


def effective_plans_query(db: Session, actor: Admin):
    query = db.query(AdminUserPlan).filter(AdminUserPlan.archived_at.is_(None))
    if admin_hierarchy.is_owner(db, actor):
        return query
    direct = exists().where(
        and_(
            AdminUserPlanAccess.plan_id == AdminUserPlan.id,
            AdminUserPlanAccess.admin_id == actor.id,
        )
    )
    inherited = exists().where(
        and_(
            AdminUserPlanAccess.plan_id == AdminUserPlan.id,
            AdminUserPlanAccess.include_subtree.is_(True),
            exists().where(
                and_(
                    AdminHierarchy.ancestor_id == AdminUserPlanAccess.admin_id,
                    AdminHierarchy.descendant_id == actor.id,
                )
            ),
        )
    )
    category_access = exists().where(
        and_(
            AdminPlanCategoryAccess.category_id == AdminUserPlan.category_id,
            AdminPlanCategoryAccess.admin_id == actor.id,
        )
    )
    return query.filter(
        or_(AdminUserPlan.owner_admin_id == actor.id, category_access, direct, inherited)
    )


def can_use_plan(db: Session, actor: Admin, plan_id: int) -> bool:
    return bool(effective_plans_query(db, actor).filter(AdminUserPlan.id == plan_id).first())


def plan_response(db: Session, plan: AdminUserPlan) -> PlanResponse:
    version = db.get(AdminUserPlanVersion, plan.current_version_id)
    if version is None:
        raise admin_hierarchy.HierarchyError("plan_version_missing", "Plan current version is missing")
    inbounds = [
        row[0]
        for row in db.query(AdminUserPlanInbound.inbound_tag)
        .filter(AdminUserPlanInbound.version_id == version.id)
        .order_by(AdminUserPlanInbound.inbound_tag)
        .all()
    ]
    access = (
        db.query(AdminUserPlanAccess)
        .filter(AdminUserPlanAccess.plan_id == plan.id)
        .order_by(AdminUserPlanAccess.admin_id)
        .all()
    )
    return PlanResponse(
        id=plan.id,
        owner_admin_id=plan.owner_admin_id,
        name=plan.name,
        description=plan.description,
        category_id=plan.category_id,
        category_name=plan.category.name if plan.category is not None else None,
        current_version_id=version.id,
        version_number=version.version_number,
        archived_at=plan.archived_at,
        version=PlanVersionInput(
            data_limit=version.data_limit,
            duration_days=version.duration_days,
            concurrent_user_limit=version.concurrent_user_limit,
            reset_strategy=version.reset_strategy,
            renewal_volume_strategy=version.renewal_volume_strategy,
            renewal_time_strategy=version.renewal_time_strategy,
            inbounds=inbounds,
        ),
        allowed_admin_ids=[row.admin_id for row in access],
        include_subtree=any(row.include_subtree for row in access),
    )


def _plan_user_payload(plan: AdminUserPlan, version: AdminUserPlanVersion, username: str, status, note):
    tags = []
    # Caller loaded these into the transient attribute to avoid an extra query here.
    tags.extend(getattr(version, "_inbound_tags", []))
    inbounds: dict[ProxyTypes, list[str]] = {}
    for tag in tags:
        protocol = xray.config.inbounds_by_tag[tag]["protocol"]
        proxy_type = ProxyTypes(protocol)
        inbounds.setdefault(proxy_type, []).append(tag)
    proxies = {proxy_type: {} for proxy_type in inbounds}
    expire = int((datetime.now(timezone.utc) + timedelta(days=version.duration_days)).timestamp())
    return UserCreate(
        username=username,
        status=UserStatusCreate(status),
        proxies=proxies,
        inbounds=inbounds,
        data_limit=version.data_limit,
        concurrent_user_limit=version.concurrent_user_limit,
        data_limit_reset_strategy=UserDataLimitResetStrategy(version.reset_strategy),
        expire=expire,
        note=note,
    )


def _assignment_replay(
    db: Session,
    *,
    actor: Admin,
    plan_id: int,
    username: str,
    operation_type: str,
    idempotency_key: str,
) -> tuple[User, UserPlanAssignment] | None:
    assignment = db.query(UserPlanAssignment).filter(
        UserPlanAssignment.idempotency_key == idempotency_key
    ).one_or_none()
    if assignment is None:
        return None
    user = db.get(User, assignment.user_id)
    if (
        user is None
        or assignment.actor_admin_id != actor.id
        or assignment.plan_id != plan_id
        or assignment.operation_type != operation_type
        or user.username != username
    ):
        raise admin_hierarchy.HierarchyError(
            "idempotency_conflict",
            "Idempotency key belongs to another plan operation",
        )
    if not admin_hierarchy.can_access_user(db, actor, user):
        raise admin_hierarchy.HierarchyError(
            "user_scope_forbidden",
            "The prior plan operation is outside actor scope",
        )
    return user, assignment


def create_user_from_plan(
    db: Session,
    *,
    actor: Admin,
    plan_id: int,
    username: str,
    status: str,
    note: str | None,
    idempotency_key: str,
) -> tuple[User, UserPlanAssignment, bool]:
    replay = _assignment_replay(
        db,
        actor=actor,
        plan_id=plan_id,
        username=username,
        operation_type="create",
        idempotency_key=idempotency_key,
    )
    if replay:
        return replay[0], replay[1], False
    if not can_use_plan(db, actor, plan_id):
        raise admin_hierarchy.HierarchyError("plan_access_forbidden", "Plan is unavailable in this scope")
    settings = db.get(MarzhelpAdminSettings, actor.id)
    if settings and settings.user_creation_mode_id not in (1, 2):
        raise admin_hierarchy.HierarchyError("invalid_creation_mode", "Unknown user creation mode")
    plan = db.get(AdminUserPlan, plan_id)
    version = db.get(AdminUserPlanVersion, plan.current_version_id)
    version._inbound_tags = [
        row[0]
        for row in db.query(AdminUserPlanInbound.inbound_tag)
        .filter(AdminUserPlanInbound.version_id == version.id)
        .all()
    ]
    payload = _plan_user_payload(plan, version, username, status, note)
    try:
        user = crud.create_user(db, payload, admin=actor, commit=False)
        assignment = UserPlanAssignment(
            user_id=user.id,
            plan_id=plan.id,
            version_id=version.id,
            actor_admin_id=actor.id,
            operation_type="create",
            idempotency_key=idempotency_key,
        )
        db.add(assignment)
        db.commit()
        db.refresh(user)
        db.refresh(assignment)
        return user, assignment, True
    except IntegrityError:
        db.rollback()
        replay = _assignment_replay(
            db,
            actor=actor,
            plan_id=plan_id,
            username=username,
            operation_type="create",
            idempotency_key=idempotency_key,
        )
        if replay:
            return replay[0], replay[1], False
        raise


def renew_user_from_plan(
    db: Session,
    *,
    actor: Admin,
    user: User,
    plan_id: int,
    idempotency_key: str,
) -> tuple[User, UserPlanAssignment, bool]:
    replay = _assignment_replay(
        db,
        actor=actor,
        plan_id=plan_id,
        username=user.username,
        operation_type="renew",
        idempotency_key=idempotency_key,
    )
    if replay:
        return replay[0], replay[1], False
    user = (
        db.query(User)
        .filter(User.id == user.id)
        .with_for_update()
        .one()
    )
    replay = _assignment_replay(
        db,
        actor=actor,
        plan_id=plan_id,
        username=user.username,
        operation_type="renew",
        idempotency_key=idempotency_key,
    )
    if replay:
        return replay[0], replay[1], False
    if not admin_hierarchy.can_access_user(db, actor, user):
        raise admin_hierarchy.HierarchyError("user_scope_forbidden", "User is outside actor scope")
    if not can_use_plan(db, actor, plan_id):
        raise admin_hierarchy.HierarchyError("plan_access_forbidden", "Plan is unavailable in this scope")
    plan = db.get(AdminUserPlan, plan_id)
    if plan.archived_at is not None:
        raise admin_hierarchy.HierarchyError("plan_archived", "Archived plan cannot be renewed")
    version = db.get(AdminUserPlanVersion, plan.current_version_id)
    settings = (
        db.query(MarzhelpAdminSettings)
        .filter(MarzhelpAdminSettings.admin_id == user.admin_id)
        .with_for_update()
        .one()
    )
    if not settings.renewal_enabled:
        raise admin_hierarchy.HierarchyError("renewal_disabled", "Renewal is disabled")
    if settings.renewal_remaining is not None and settings.renewal_remaining <= 0:
        raise admin_hierarchy.HierarchyError("renewal_quota_exhausted", "Renewal quota is exhausted")
    if settings.max_user_duration_days and version.duration_days > settings.max_user_duration_days:
        raise admin_hierarchy.HierarchyError("duration_exceeded", "Plan duration exceeds user owner limit")
    if (
        not settings.all_user_limits
        and version.concurrent_user_limit is not None
        and version.concurrent_user_limit not in settings.allowed_user_limits
    ):
        raise admin_hierarchy.HierarchyError("user_limit_forbidden", "Plan device limit is not allowed")
    version_inbounds = {
        row[0]
        for row in db.query(AdminUserPlanInbound.inbound_tag)
        .filter(AdminUserPlanInbound.version_id == version.id)
        .all()
    }
    if not settings.all_inbounds and not version_inbounds.issubset(set(settings.allowed_inbounds)):
        raise admin_hierarchy.HierarchyError("inbound_forbidden", "Plan contains inbounds forbidden for user owner")
    available = admin_hierarchy.available_credit(db, settings)
    if version.data_limit == 0 and available is not None:
        raise admin_hierarchy.HierarchyError("unlimited_traffic_forbidden", "Finite credit cannot renew unlimited")
    if available is not None and version.data_limit > available:
        raise admin_hierarchy.HierarchyError("credit_exhausted", "Renewal exceeds available credit")

    if user.used_traffic:
        db.add(UserUsageResetLogs(user_id=user.id, used_traffic_at_reset=user.used_traffic))
    user.used_traffic = 0
    user.data_limit = version.data_limit or None
    user.status = UserStatus.active
    user.concurrent_user_limit = version.concurrent_user_limit
    user.data_limit_reset_strategy = UserDataLimitResetStrategy(version.reset_strategy)
    now_ts = int(datetime.now(timezone.utc).timestamp())
    user.expire = max(now_ts, int(user.expire or 0)) + version.duration_days * 86400
    if (settings.calculate_volume or "used_traffic") == "created_traffic":
        settings.used_traffic = int(settings.used_traffic or 0) + int(version.data_limit or 0)
    if settings.renewal_remaining is not None:
        settings.renewal_remaining -= 1
    settings.renewals_used = int(settings.renewals_used or 0) + 1
    assignment = UserPlanAssignment(
        user_id=user.id,
        plan_id=plan.id,
        version_id=version.id,
        actor_admin_id=actor.id,
        operation_type="renew",
        idempotency_key=idempotency_key,
    )
    try:
        db.add(assignment)
        db.commit()
        db.refresh(user)
        db.refresh(assignment)
        return user, assignment, True
    except IntegrityError:
        db.rollback()
        replay = _assignment_replay(
            db,
            actor=actor,
            plan_id=plan_id,
            username=user.username,
            operation_type="renew",
            idempotency_key=idempotency_key,
        )
        if replay:
            return replay[0], replay[1], False
        raise
