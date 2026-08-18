from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from sqlalchemy import exists, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import noload

from app import xray
from app.db import Session, crud, get_db
from app.db.models import (
    Admin as DBAdmin,
    AdminAccountStatus,
    AdminApiToken,
    AdminAuditLog,
    AdminCreditTransfer,
    AdminHierarchy,
    AdminRole,
    AdminSuspensionReason,
    AdminUserCreationMode,
    AdminUserPlan,
    MarzhelpAdminSettings,
    User,
)
from app.models.admin import Admin, AdminCreate
from app.models.admin_hierarchy import (
    AccountSummary,
    ApiTokenCreate,
    ApiTokenCreated,
    ApiTokenSummary,
    BulkDisableRequest,
    CreditTransferRequest,
    CreditTransferResponse,
    ExternalApiPolicy,
    HierarchyAdminNode,
    HierarchyChildCreate,
    PlanCreate,
    PlanRenewRequest,
    PlanResponse,
    PlanUpdate,
    PlanUserCreate,
    RenewalPolicyUpdate,
    ReparentRequest,
    SuspendRequest,
    UserCreationModeUpdate,
)
from app.models.user import UserResponse
from app.utils import admin_hierarchy, admin_plans, responses
from app.utils.audit import AuditLogService, get_client_ip


router = APIRouter(
    tags=["Admin hierarchy"],
    prefix="/api",
    responses={401: responses._401, 403: responses._403},
)


def _db_actor(db: Session, admin: Admin) -> DBAdmin:
    actor = crud.get_admin(db, admin.username)
    if actor is None:
        raise HTTPException(status_code=401, detail="Database administrator record is required")
    return actor


def _target(db: Session, username: str) -> DBAdmin:
    target = crud.get_admin(db, username)
    if target is None:
        raise HTTPException(status_code=404, detail="Admin not found")
    return target


def _raise_domain(exc: Exception):
    if isinstance(exc, admin_hierarchy.HierarchyError):
        code = 404 if exc.code.endswith("not_found") else 409 if "conflict" in exc.code else 403
        if exc.code.startswith("invalid_") or exc.code in {
            "cycle_detected",
            "credit_exhausted",
            "reclaim_exceeds_available",
            "renewal_quota_exhausted",
            "renewal_disabled",
            "plan_archived",
        }:
            code = 400
        raise HTTPException(status_code=code, detail={"code": exc.code, "message": str(exc)})
    raise exc


def _restart_runtime() -> None:
    startup_config = xray.config.include_db_users()
    if xray.core.started:
        xray.core.restart(startup_config)
    for node_id, node in list(xray.nodes.items()):
        if node.connected:
            xray.operations.restart_node(node_id, startup_config)


def _node_response(
    db: Session,
    row: DBAdmin,
    depth: int,
    settings: MarzhelpAdminSettings | None = None,
    status: str | None = None,
    role: str | None = None,
    preloaded: bool = False,
) -> HierarchyAdminNode:
    if settings is None and not preloaded:
        settings = db.get(MarzhelpAdminSettings, row.id)
    if status is None and settings is not None and not preloaded:
        status = db.query(AdminAccountStatus.code).filter(
            AdminAccountStatus.id == settings.account_status_id
        ).scalar()
    spend = admin_hierarchy.own_credit_spend(db, settings) if settings else 0
    return HierarchyAdminNode(
        id=row.id,
        username=row.username,
        role=role or admin_hierarchy.role_code(row),
        parent_admin_id=row.parent_admin_id,
        depth=depth,
        external_api_enabled=bool(row.external_api_enabled),
        account_status=status or admin_hierarchy.ACTIVE,
        total_traffic=settings.total_traffic if settings else None,
        delegated_traffic=int(settings.delegated_traffic or 0) if settings else 0,
        own_spend=spend,
        available_traffic=admin_hierarchy.available_credit(db, settings) if settings else None,
    )


@router.get("/admin-management/tree", response_model=list[HierarchyAdminNode])
def get_admin_tree(
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
):
    actor = _db_actor(db, admin)
    if not admin_hierarchy.hierarchy_enabled(db):
        nodes = [_node_response(db, actor, 0)]
    else:
        rows = (
            db.query(
                DBAdmin,
                AdminHierarchy.depth,
                MarzhelpAdminSettings,
                AdminAccountStatus.code,
                AdminRole.code,
            )
            .join(AdminHierarchy, AdminHierarchy.descendant_id == DBAdmin.id)
            .outerjoin(MarzhelpAdminSettings, MarzhelpAdminSettings.admin_id == DBAdmin.id)
            .outerjoin(
                AdminAccountStatus,
                AdminAccountStatus.id == MarzhelpAdminSettings.account_status_id,
            )
            .outerjoin(AdminRole, AdminRole.id == DBAdmin.role_id)
            .options(
                noload(MarzhelpAdminSettings.inbound_permissions),
                noload(MarzhelpAdminSettings.user_limit_permissions),
                noload(MarzhelpAdminSettings.subscription_mode_permissions),
            )
            .filter(AdminHierarchy.ancestor_id == actor.id)
            .order_by(AdminHierarchy.depth, DBAdmin.username)
            .all()
        )
        nodes = [
            _node_response(db, row, depth, settings, status, role, preloaded=True)
            for row, depth, settings, status, role in rows
        ]
    by_id = {node.id: node for node in nodes}
    roots: list[HierarchyAdminNode] = []
    for node in nodes:
        if node.parent_admin_id in by_id:
            by_id[node.parent_admin_id].children.append(node)
        else:
            roots.append(node)
    return roots


@router.post("/admin-management/{username}/children", response_model=HierarchyAdminNode)
def create_child(
    username: str,
    values: HierarchyChildCreate,
    request: Request,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
):
    actor = _db_actor(db, admin)
    parent = _target(db, username)
    try:
        child = crud.create_admin(
            db,
            AdminCreate(username=values.username, password=values.password, is_sudo=False),
            commit=False,
        )
        admin_hierarchy.attach_new_child(
            db,
            actor=actor,
            parent=parent,
            child=child,
            child_role=values.role,
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Admin already exists")
    except Exception as exc:
        db.rollback()
        _raise_domain(exc)
    AuditLogService.log(
        db,
        actor,
        "admin.child_create",
        "admin",
        f"Admin {actor.username} created {values.role} {child.username}",
        target_id=child.id,
        target_name=child.username,
        details={"parent_admin_id": parent.id, "role": values.role},
        request=request,
    )
    return _node_response(db, child, 1)


@router.put("/admin-management/{username}/parent")
def reparent_admin(
    username: str,
    values: ReparentRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
):
    actor = _db_actor(db, admin)
    target = _target(db, username)
    parent = _target(db, values.parent_username)
    previous_parent = target.parent_admin_id
    try:
        admin_hierarchy.reparent_subtree(db, actor, target, parent)
    except Exception as exc:
        _raise_domain(exc)
    AuditLogService.log(
        db,
        actor,
        "admin.reparent",
        "admin",
        f"Owner {actor.username} reparented {target.username}",
        target_id=target.id,
        target_name=target.username,
        previous_value={"parent_admin_id": previous_parent},
        new_value={"parent_admin_id": parent.id},
        request=request,
    )
    return {"detail": "Admin subtree reparented"}


def _credit_move(
    username: str,
    values: CreditTransferRequest,
    operation: str,
    request: Request,
    db: Session,
    admin: Admin,
):
    actor = _db_actor(db, admin)
    child = _target(db, username)
    parent = db.get(DBAdmin, child.parent_admin_id) if child.parent_admin_id else None
    if parent is None:
        raise HTTPException(status_code=400, detail="Target has no parent credit account")
    try:
        row = admin_hierarchy.transfer_credit(
            db,
            actor=actor,
            source=parent,
            target=child,
            amount=values.amount,
            operation_type=operation,
            idempotency_key=values.idempotency_key,
            note=values.note,
        )
    except Exception as exc:
        _raise_domain(exc)
    AuditLogService.log(
        db,
        actor,
        f"credit.{operation}",
        "admin_credit",
        f"Admin {actor.username} {operation} {values.amount} bytes for {child.username}",
        target_id=child.id,
        target_name=child.username,
        details={"transfer_id": row.id, "idempotency_key": values.idempotency_key},
        request=request,
    )
    return row


@router.post("/admin-management/{username}/credit/grant", response_model=CreditTransferResponse)
def grant_credit(
    username: str,
    values: CreditTransferRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
):
    return _credit_move(username, values, "grant", request, db, admin)


@router.post("/admin-management/{username}/credit/reclaim", response_model=CreditTransferResponse)
def reclaim_credit(
    username: str,
    values: CreditTransferRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
):
    return _credit_move(username, values, "reclaim", request, db, admin)


@router.get("/admin-management/{username}/credit/ledger", response_model=list[CreditTransferResponse])
def credit_ledger(
    username: str,
    before_id: int | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
):
    actor = _db_actor(db, admin)
    target = _target(db, username)
    if not admin_hierarchy.admin_in_scope(db, actor, target.id):
        raise HTTPException(status_code=403, detail="Admin is outside your scope")
    query = db.query(AdminCreditTransfer).filter(
        (AdminCreditTransfer.from_admin_id == target.id)
        | (AdminCreditTransfer.to_admin_id == target.id)
    )
    if before_id is not None:
        query = query.filter(AdminCreditTransfer.id < before_id)
    return query.order_by(AdminCreditTransfer.id.desc()).limit(limit).all()


@router.put("/admin-management/{username}/external-api")
def set_external_api(
    username: str,
    values: ExternalApiPolicy,
    request: Request,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
):
    actor = _db_actor(db, admin)
    target = _target(db, username)
    try:
        if not admin_hierarchy.is_owner(db, actor):
            raise admin_hierarchy.HierarchyError("owner_required", "Only Owner can change external API")
        revoked = 0
        if values.enabled:
            target.external_api_enabled = True
            target.external_api_updated_by = actor.id
            target.external_api_updated_at = admin_hierarchy.utc_now_naive()
            db.commit()
        else:
            revoked = admin_hierarchy.revoke_api_access(db, actor, target)
    except Exception as exc:
        _raise_domain(exc)
    AuditLogService.log(
        db,
        actor,
        "admin.external_api",
        "admin",
        f"Owner {actor.username} set external API for {target.username} to {values.enabled}",
        target_id=target.id,
        target_name=target.username,
        details={"enabled": values.enabled, "revoked_tokens": revoked},
        request=request,
    )
    return {"enabled": values.enabled, "revoked_tokens": revoked}


@router.post("/admin-management/{username}/api-tokens", response_model=ApiTokenCreated)
def create_api_token(
    username: str,
    values: ApiTokenCreate,
    request: Request,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
):
    actor = _db_actor(db, admin)
    target = _target(db, username)
    try:
        row, plaintext = admin_hierarchy.issue_api_token(
            db,
            owner=actor,
            target=target,
            name=values.name,
            scopes=values.scopes,
            expires_at=values.expires_at,
        )
    except Exception as exc:
        _raise_domain(exc)
    AuditLogService.log(
        db,
        actor,
        "admin.api_token_create",
        "admin_api_token",
        f"Owner {actor.username} created an automation token for {target.username}",
        target_id=row.id,
        target_name=target.username,
        details={"scopes": sorted(row.scopes), "expires_at": row.expires_at},
        request=request,
    )
    return ApiTokenCreated(
        id=row.id,
        name=row.name,
        scopes=row.scopes,
        expires_at=row.expires_at,
        token=plaintext,
    )


@router.get("/admin-management/{username}/api-tokens", response_model=list[ApiTokenSummary])
def list_api_tokens(
    username: str,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
):
    actor = _db_actor(db, admin)
    target = _target(db, username)
    if not admin_hierarchy.is_owner(db, actor):
        raise HTTPException(status_code=403, detail="Only Owner can list automation tokens")
    return db.query(AdminApiToken).filter(AdminApiToken.admin_id == target.id).order_by(
        AdminApiToken.id.desc()
    ).all()


@router.delete("/admin-management/{username}/api-tokens/{token_id}")
def revoke_api_token(
    username: str,
    token_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
):
    actor = _db_actor(db, admin)
    target = _target(db, username)
    if not admin_hierarchy.is_owner(db, actor):
        raise HTTPException(status_code=403, detail="Only Owner can revoke automation tokens")
    token = db.query(AdminApiToken).filter(
        AdminApiToken.id == token_id,
        AdminApiToken.admin_id == target.id,
    ).one_or_none()
    if token is None:
        raise HTTPException(status_code=404, detail="API token not found")
    token.revoked_at = admin_hierarchy.utc_now_naive()
    db.commit()
    AuditLogService.log(
        db,
        actor,
        "admin.api_token_revoke",
        "admin_api_token",
        f"Owner {actor.username} revoked an automation token for {target.username}",
        target_id=token.id,
        target_name=target.username,
        details={"token_name": token.name},
        request=request,
    )
    return {"detail": "API token revoked"}


def _parent_or_owner(db: Session, actor: DBAdmin, target: DBAdmin) -> bool:
    return admin_hierarchy.is_owner(db, actor) or target.parent_admin_id == actor.id


@router.put("/admin-management/{username}/renewal-policy")
def update_renewal_policy(
    username: str,
    values: RenewalPolicyUpdate,
    request: Request,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
):
    actor = _db_actor(db, admin)
    target = _target(db, username)
    if not _parent_or_owner(db, actor, target):
        raise HTTPException(status_code=403, detail="Only parent or Owner can set renewal policy")
    settings = db.get(MarzhelpAdminSettings, target.id)
    previous = {
        "enabled": settings.renewal_enabled,
        "remaining": settings.renewal_remaining,
    }
    settings.renewal_enabled = values.enabled
    settings.renewal_remaining = values.remaining
    settings.renewal_limit = values.remaining
    settings.renewals_used = 0
    db.commit()
    AuditLogService.log(
        db,
        actor,
        "admin.renewal_policy_update",
        "admin",
        f"Admin {actor.username} updated renewal policy for {target.username}",
        target_id=target.id,
        target_name=target.username,
        previous_value=previous,
        new_value={"enabled": values.enabled, "remaining": values.remaining},
        request=request,
    )
    return {"enabled": values.enabled, "remaining": values.remaining}


@router.put("/admin-management/{username}/user-creation-mode")
def update_user_creation_mode(
    username: str,
    values: UserCreationModeUpdate,
    request: Request,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
):
    actor = _db_actor(db, admin)
    target = _target(db, username)
    if not _parent_or_owner(db, actor, target):
        raise HTTPException(status_code=403, detail="Only parent or Owner can set creation mode")
    settings = db.get(MarzhelpAdminSettings, target.id)
    previous = {
        "user_creation_mode_id": settings.user_creation_mode_id,
        "can_manage_plans": settings.can_manage_plans,
    }
    settings.user_creation_mode_id = admin_hierarchy.USER_CREATION_MODE_IDS[values.mode]
    settings.can_manage_plans = values.can_manage_plans
    db.commit()
    AuditLogService.log(
        db,
        actor,
        "admin.user_creation_mode_update",
        "admin",
        f"Admin {actor.username} updated creation mode for {target.username}",
        target_id=target.id,
        target_name=target.username,
        previous_value=previous,
        new_value={"mode": values.mode, "can_manage_plans": values.can_manage_plans},
        request=request,
    )
    return {"mode": values.mode, "can_manage_plans": values.can_manage_plans}


@router.post("/admin-management/{username}/suspend")
def suspend_admin(
    username: str,
    values: SuspendRequest,
    request: Request,
    bg: BackgroundTasks,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
):
    actor = _db_actor(db, admin)
    target = _target(db, username)
    try:
        event = admin_hierarchy.suspend_admin(
            db,
            actor=actor,
            target=target,
            reason_id=values.reason_id,
            include_subtree=values.include_subtree,
        )
    except Exception as exc:
        _raise_domain(exc)
    AuditLogService.log(
        db,
        actor,
        "admin.suspend",
        "admin",
        f"Admin {actor.username} suspended {target.username}",
        target_id=target.id,
        target_name=target.username,
        details={"event_id": event.id, "reason_id": values.reason_id, "include_subtree": values.include_subtree},
        request=request,
    )
    bg.add_task(_restart_runtime)
    return {"event_id": event.id, "status": event.status}


@router.post("/admin-management/{username}/resume")
def resume_admin(
    username: str,
    request: Request,
    bg: BackgroundTasks,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
):
    actor = _db_actor(db, admin)
    target = _target(db, username)
    try:
        restored = admin_hierarchy.resume_admin(db, actor=actor, target=target)
    except Exception as exc:
        _raise_domain(exc)
    AuditLogService.log(
        db,
        actor,
        "admin.resume",
        "admin",
        f"Admin {actor.username} resumed {target.username}",
        target_id=target.id,
        target_name=target.username,
        details={"restored_users": restored},
        request=request,
    )
    bg.add_task(_restart_runtime)
    return {"restored_users": restored}


@router.post("/admin-management/{username}/users/disable")
def disable_users_job(
    username: str,
    values: BulkDisableRequest,
    request: Request,
    bg: BackgroundTasks,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
):
    actor = _db_actor(db, admin)
    target = _target(db, username)
    try:
        job = admin_hierarchy.run_disable_job(
            db,
            actor=actor,
            target=target,
            include_subtree=values.include_subtree,
            idempotency_key=values.idempotency_key,
            batch_size=values.batch_size,
        )
    except Exception as exc:
        _raise_domain(exc)
    AuditLogService.log(
        db,
        actor,
        "admin.users_disable_bulk",
        "admin_bulk_job",
        f"Admin {actor.username} disabled users for {target.username}",
        target_id=job.id,
        target_name=target.username,
        details={
            "include_subtree": values.include_subtree,
            "total_count": job.total_count,
            "processed_count": job.processed_count,
            "idempotency_key": values.idempotency_key,
        },
        request=request,
    )
    bg.add_task(_restart_runtime)
    return {
        "job_id": job.id,
        "status": job.status,
        "total_count": job.total_count,
        "processed_count": job.processed_count,
    }


@router.get("/account/summary", response_model=AccountSummary)
def account_summary(
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
):
    actor = _db_actor(db, admin)
    settings = db.get(MarzhelpAdminSettings, actor.id)
    account_status = admin_hierarchy.account_status_code(db, actor.id)
    reason = (
        db.query(AdminSuspensionReason.code)
        .filter(AdminSuspensionReason.id == settings.suspended_reason_id)
        .scalar()
        if settings and settings.suspended_reason_id
        else None
    )
    own_users = db.query(func.count(User.id)).filter(User.admin_id == actor.id).scalar() or 0
    subtree_users = (
        db.query(func.count(User.id))
        .filter(
            exists().where(
                (AdminHierarchy.ancestor_id == actor.id)
                & (AdminHierarchy.descendant_id == User.admin_id)
            )
        )
        .scalar()
        or own_users
    )
    mode = (
        db.query(AdminUserCreationMode.code)
        .filter(AdminUserCreationMode.id == settings.user_creation_mode_id)
        .scalar()
        if settings
        else admin_hierarchy.FREE_FORM
    )
    return AccountSummary(
        username=actor.username,
        role=admin_hierarchy.role_code(actor),
        account_status=account_status,
        suspended_reason=reason,
        suspended_at=settings.suspended_at if settings else None,
        own_users=own_users,
        subtree_users=subtree_users,
        total_traffic=settings.total_traffic if settings else None,
        delegated_traffic=int(settings.delegated_traffic or 0) if settings else 0,
        own_spend=admin_hierarchy.own_credit_spend(db, settings) if settings else 0,
        available_traffic=admin_hierarchy.available_credit(db, settings) if settings else None,
        renewal_enabled=bool(settings.renewal_enabled) if settings else True,
        renewal_remaining=settings.renewal_remaining if settings else None,
        user_creation_mode=mode or admin_hierarchy.FREE_FORM,
        can_manage_plans=bool(settings.can_manage_plans) if settings else False,
    )


@router.get("/account/activity")
def account_activity(
    before_id: int | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
):
    actor = _db_actor(db, admin)
    query = db.query(AdminAuditLog)
    if not admin_hierarchy.is_owner(db, actor):
        query = query.filter(
            exists().where(
                (AdminHierarchy.ancestor_id == actor.id)
                & (AdminHierarchy.descendant_id == AdminAuditLog.admin_id)
            )
        )
    if before_id is not None:
        query = query.filter(AdminAuditLog.id < before_id)
    rows = query.order_by(AdminAuditLog.id.desc()).limit(limit).all()
    return [
        {
            "id": row.id,
            "admin_username": row.admin_username,
            "action": row.action,
            "target_type": row.target_type,
            "target_id": row.target_id,
            "target_name": row.target_name,
            "description": row.description,
            "status": row.status,
            "created_at": row.created_at,
        }
        for row in rows
    ]


@router.get("/user-plans", response_model=list[PlanResponse])
def get_user_plans(
    before_id: int | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
):
    actor = _db_actor(db, admin)
    query = admin_plans.effective_plans_query(db, actor)
    if before_id is not None:
        query = query.filter(AdminUserPlan.id < before_id)
    plans = query.order_by(AdminUserPlan.id.desc()).limit(limit).all()
    return [admin_plans.plan_response(db, plan) for plan in plans]


@router.post("/user-plans", response_model=PlanResponse)
def create_user_plan(
    values: PlanCreate,
    request: Request,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
):
    actor = _db_actor(db, admin)
    try:
        plan = admin_plans.create_plan(db, actor, values)
        result = admin_plans.plan_response(db, plan)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Plan name already exists in this owner scope")
    except Exception as exc:
        _raise_domain(exc)
    AuditLogService.log(
        db,
        actor,
        "plan.create",
        "admin_user_plan",
        f"Admin {actor.username} created plan {plan.name}",
        target_id=plan.id,
        target_name=plan.name,
        details={"version_id": plan.current_version_id},
        request=request,
    )
    return result


@router.put("/user-plans/{plan_id}", response_model=PlanResponse)
def update_user_plan(
    plan_id: int,
    values: PlanUpdate,
    request: Request,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
):
    actor = _db_actor(db, admin)
    plan = db.get(AdminUserPlan, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    previous_version_id = plan.current_version_id
    try:
        updated = admin_plans.update_plan(db, actor, plan, values)
        result = admin_plans.plan_response(db, updated)
    except Exception as exc:
        _raise_domain(exc)
    AuditLogService.log(
        db,
        actor,
        "plan.version_create",
        "admin_user_plan",
        f"Admin {actor.username} created a new version of plan {plan.name}",
        target_id=plan.id,
        target_name=plan.name,
        previous_value={"version_id": previous_version_id},
        new_value={"version_id": updated.current_version_id},
        request=request,
    )
    return result


@router.delete("/user-plans/{plan_id}")
def archive_user_plan(
    plan_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
):
    actor = _db_actor(db, admin)
    plan = db.get(AdminUserPlan, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    if not admin_hierarchy.is_owner(db, actor) and plan.owner_admin_id != actor.id:
        raise HTTPException(status_code=403, detail="Only plan owner can archive this plan")
    plan.archived_at = admin_hierarchy.utc_now_naive()
    db.commit()
    AuditLogService.log(
        db,
        actor,
        "plan.archive",
        "admin_user_plan",
        f"Admin {actor.username} archived plan {plan.name}",
        target_id=plan.id,
        target_name=plan.name,
        request=request,
    )
    return {"detail": "Plan archived"}


@router.post("/users/from-plan", response_model=UserResponse)
def create_user_from_plan(
    values: PlanUserCreate,
    request: Request,
    bg: BackgroundTasks,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
):
    actor = _db_actor(db, admin)
    try:
        user, _, created = admin_plans.create_user_from_plan(
            db,
            actor=actor,
            plan_id=values.plan_id,
            username=values.username,
            status=values.status,
            note=values.note,
            idempotency_key=values.idempotency_key,
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="User already exists")
    except Exception as exc:
        _raise_domain(exc)
    if created:
        AuditLogService.log(
            db,
            actor,
            "user.create_from_plan",
            "user",
            f"Admin {actor.username} created user {user.username} from plan",
            target_id=user.id,
            target_name=user.username,
            details={"plan_id": values.plan_id, "idempotency_key": values.idempotency_key},
            request=request,
        )
        bg.add_task(xray.operations.add_user_by_id, user_id=user.id)
    return UserResponse.model_validate(user)


@router.post("/users/{username}/renew-from-plan", response_model=UserResponse)
def renew_user_from_plan(
    username: str,
    values: PlanRenewRequest,
    request: Request,
    bg: BackgroundTasks,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
):
    actor = _db_actor(db, admin)
    user = crud.get_user(db, username)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        user, _, renewed = admin_plans.renew_user_from_plan(
            db,
            actor=actor,
            user=user,
            plan_id=values.plan_id,
            idempotency_key=values.idempotency_key,
        )
    except Exception as exc:
        _raise_domain(exc)
    if renewed:
        AuditLogService.log(
            db,
            actor,
            "user.renew_from_plan",
            "user",
            f"Admin {actor.username} renewed user {user.username} from plan",
            target_id=user.id,
            target_name=user.username,
            details={"plan_id": values.plan_id, "idempotency_key": values.idempotency_key},
            request=request,
        )
        bg.add_task(xray.operations.update_user_by_id, user_id=user.id)
    return UserResponse.model_validate(user)
