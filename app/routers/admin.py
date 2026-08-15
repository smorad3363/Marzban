from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from app import xray
from app.db import Session, crud, get_db
from app.dependencies import get_admin_by_username, validate_admin
from app.db.models import MarzhelpAdminSettings, User
from app.models.admin import (
    Admin,
    AdminCapabilities,
    AdminCreate,
    AdminModify,
    ManagedAdmin,
    ManagedAdminCreate,
    ManagedAdminList,
    ManagedAdminModify,
    MarzhelpAdminPolicy,
    Token,
)
from app.models.user import UserStatus
from app.utils import marzhelp_policy, report, responses
from app.utils.audit import (
    AuditLogService,
    AuditStatus,
    admin_audit_state,
    get_client_ip,
    summarize_targets,
)
from app.utils.jwt import create_admin_token
from config import LOGIN_NOTIFY_WHITE_LIST

router = APIRouter(tags=["Admin"], prefix="/api", responses={401: responses._401})


def managed_admin_response(
    dbadmin,
    settings=None,
    user_count: int = 0,
    capacity_used: int = 0,
) -> ManagedAdmin:
    policy = (
        MarzhelpAdminPolicy.model_validate(settings)
        if settings is not None
        else MarzhelpAdminPolicy()
    )
    return ManagedAdmin(
        username=dbadmin.username,
        is_sudo=dbadmin.is_sudo,
        telegram_id=dbadmin.telegram_id,
        discord_webhook=dbadmin.discord_webhook,
        users_usage=dbadmin.users_usage,
        user_count=user_count,
        capacity_used=capacity_used,
        policy=policy,
    )


@router.post("/admin/token", response_model=Token)
def admin_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Authenticate an admin and issue a token."""
    client_ip = get_client_ip(request) or "Unknown"

    authenticated_admin = validate_admin(db, form_data.username, form_data.password)
    if not authenticated_admin:
        report.login(form_data.username, form_data.password, client_ip, False)
        AuditLogService.log(
            db,
            form_data.username,
            "auth.login",
            "admin",
            f"Failed login attempt for admin {form_data.username}",
            target_name=form_data.username,
            request=request,
            status=AuditStatus.failed,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if client_ip not in LOGIN_NOTIFY_WHITE_LIST:
        report.login(form_data.username, "🔒", client_ip, True)

    dbadmin = crud.get_admin(db, authenticated_admin.username)
    AuditLogService.log(
        db,
        authenticated_admin,
        "auth.login",
        "admin",
        f"Admin {authenticated_admin.username} logged in",
        target_id=dbadmin.id if dbadmin is not None else None,
        target_name=authenticated_admin.username,
        request=request,
    )
    return Token(
        access_token=create_admin_token(
            authenticated_admin.username,
            authenticated_admin.is_sudo,
        )
    )


@router.post("/admin/logout")
def admin_logout(
    request: Request,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
):
    """Record a client-side logout before its token is discarded."""
    AuditLogService.log(
        db,
        admin,
        "auth.logout",
        "admin",
        f"Admin {admin.username} logged out",
        target_name=admin.username,
        request=request,
    )
    return {"detail": "Logout recorded"}


@router.post(
    "/admin",
    response_model=Admin,
    responses={403: responses._403, 409: responses._409},
)
def create_admin(
    request: Request,
    new_admin: AdminCreate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.check_sudo_admin),
):
    """Create a new admin if the current admin has sudo privileges."""
    try:
        dbadmin = crud.create_admin(db, new_admin)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Admin already exists")

    AuditLogService.log(
        db,
        admin,
        "admin.create",
        "admin",
        f"Admin {admin.username} created admin {dbadmin.username}",
        target_id=dbadmin.id,
        target_name=dbadmin.username,
        new_value=admin_audit_state(dbadmin),
        request=request,
    )
    return dbadmin


@router.put(
    "/admin/{username}",
    response_model=Admin,
    responses={403: responses._403},
)
def modify_admin(
    request: Request,
    modified_admin: AdminModify,
    dbadmin: Admin = Depends(get_admin_by_username),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(Admin.check_sudo_admin),
):
    """Modify an existing admin's details."""
    if (dbadmin.username != current_admin.username) and dbadmin.is_sudo:
        raise HTTPException(
            status_code=403,
            detail="You're not allowed to edit another sudoer's account. Use marzban-cli instead.",
        )

    previous_value = admin_audit_state(dbadmin)
    updated_admin = crud.update_admin(db, dbadmin, modified_admin)
    AuditLogService.log(
        db,
        current_admin,
        "admin.update",
        "admin",
        f"Admin {current_admin.username} updated admin {updated_admin.username}",
        target_id=updated_admin.id,
        target_name=updated_admin.username,
        previous_value=previous_value,
        new_value=admin_audit_state(updated_admin),
        details={"password_changed": modified_admin.password is not None},
        request=request,
    )

    return updated_admin


@router.delete(
    "/admin/{username}",
    responses={403: responses._403},
)
def remove_admin(
    request: Request,
    dbadmin: Admin = Depends(get_admin_by_username),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(Admin.check_sudo_admin),
):
    """Remove an admin from the database."""
    if dbadmin.is_sudo:
        raise HTTPException(
            status_code=403,
            detail="You're not allowed to delete sudo accounts. Use marzban-cli instead.",
        )

    target_id = dbadmin.id
    target_name = dbadmin.username
    previous_value = admin_audit_state(dbadmin)
    crud.remove_admin(db, dbadmin)
    AuditLogService.log(
        db,
        current_admin,
        "admin.delete",
        "admin",
        f"Admin {current_admin.username} deleted admin {target_name}",
        target_id=target_id,
        target_name=target_name,
        previous_value=previous_value,
        request=request,
    )
    return {"detail": "Admin removed successfully"}


@router.get("/admin", response_model=Admin)
def get_current_admin(admin: Admin = Depends(Admin.get_current)):
    """Retrieve the current authenticated admin."""
    return admin


@router.get("/admin/capabilities", response_model=AdminCapabilities)
def get_admin_capabilities(
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
):
    """Return effective inbound, device-limit, and weighted-capacity rules."""

    dbadmin = crud.get_admin(db, admin.username)
    if admin.is_sudo or dbadmin is None:
        return AdminCapabilities()
    settings = db.get(MarzhelpAdminSettings, dbadmin.id)
    if settings is None:
        return AdminCapabilities()
    used = marzhelp_policy.capacity_used(db, dbadmin.id)
    maximum = settings.max_users
    return AdminCapabilities(
        all_inbounds=settings.all_inbounds,
        allowed_inbounds=settings.allowed_inbounds,
        all_user_limits=settings.all_user_limits,
        allowed_user_limits=settings.allowed_user_limits,
        capacity_used=used,
        capacity_limit=maximum,
        capacity_remaining=(max(int(maximum) - used, 0) if maximum is not None else None),
    )


@router.get(
    "/admins",
    response_model=List[Admin],
    responses={403: responses._403},
)
def get_admins(
    offset: Optional[int] = None,
    limit: Optional[int] = None,
    username: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.check_sudo_admin),
):
    """Fetch a list of admins with optional filters for pagination and username."""
    return crud.get_admins(db, offset, limit, username)


@router.get(
    "/admin-management",
    response_model=ManagedAdminList,
    responses={403: responses._403},
)
def get_managed_admins(
    offset: int = 0,
    limit: int = 20,
    username: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.check_sudo_admin),
):
    """Return a stable, paginated view of admins and their MarzHelp limits."""
    limit = max(1, min(limit, 100))
    offset = max(offset, 0)
    dbadmins, total = crud.get_admins_with_count(db, offset, limit, username)
    settings_by_admin = (
        {
            row.admin_id: row
            for row in db.query(MarzhelpAdminSettings)
            .filter(MarzhelpAdminSettings.admin_id.in_([item.id for item in dbadmins]))
            .all()
        }
        if dbadmins
        else {}
    )
    user_counts = (
        dict(
            db.query(User.admin_id, func.count(User.id))
            .filter(User.admin_id.in_([item.id for item in dbadmins]))
            .group_by(User.admin_id)
            .all()
        )
        if dbadmins
        else {}
    )
    return ManagedAdminList(
        admins=[
            managed_admin_response(
                item,
                settings_by_admin.get(item.id),
                user_counts.get(item.id, 0),
                marzhelp_policy.capacity_used(db, item.id),
            )
            for item in dbadmins
        ],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.post(
    "/admin-management",
    response_model=ManagedAdmin,
    responses={403: responses._403, 409: responses._409},
)
def create_managed_admin(
    request: Request,
    new_admin: ManagedAdminCreate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.check_sudo_admin),
):
    """Create an admin and its MarzHelp policy in one transaction."""
    try:
        dbadmin = crud.create_admin(db, new_admin, commit=False)
        settings = crud.upsert_marzhelp_admin_policy(
            db, dbadmin.id, new_admin.policy, commit=False
        )
        db.commit()
        db.refresh(dbadmin)
        db.refresh(settings)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Admin already exists")
    response = managed_admin_response(dbadmin, settings, 0, 0)
    AuditLogService.log(
        db,
        admin,
        "admin.create",
        "admin",
        f"Admin {admin.username} created managed admin {dbadmin.username}",
        target_id=dbadmin.id,
        target_name=dbadmin.username,
        new_value=admin_audit_state(dbadmin, response.policy),
        request=request,
    )
    return response


@router.put(
    "/admin-management/{username}",
    response_model=ManagedAdmin,
    responses={403: responses._403, 404: responses._404},
)
def modify_managed_admin(
    request: Request,
    modified_admin: ManagedAdminModify,
    dbadmin: Admin = Depends(get_admin_by_username),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(Admin.check_sudo_admin),
):
    """Update an admin account and its MarzHelp policy atomically."""
    if (dbadmin.username != current_admin.username) and dbadmin.is_sudo:
        raise HTTPException(
            status_code=403,
            detail="You're not allowed to edit another sudoer's account. Use marzban-cli instead.",
        )

    current_settings = db.get(MarzhelpAdminSettings, dbadmin.id)
    previous_value = admin_audit_state(
        dbadmin,
        MarzhelpAdminPolicy.model_validate(current_settings)
        if current_settings is not None
        else MarzhelpAdminPolicy(),
    )
    dbadmin = crud.update_admin(db, dbadmin, modified_admin, commit=False)
    settings = crud.upsert_marzhelp_admin_policy(
        db, dbadmin.id, modified_admin.policy, commit=False
    )
    db.commit()
    db.refresh(dbadmin)
    db.refresh(settings)
    user_count = db.query(func.count(User.id)).filter(User.admin_id == dbadmin.id).scalar() or 0
    response = managed_admin_response(
        dbadmin,
        settings,
        user_count,
        marzhelp_policy.capacity_used(db, dbadmin.id),
    )
    AuditLogService.log(
        db,
        current_admin,
        "admin.update",
        "admin",
        f"Admin {current_admin.username} updated managed admin {dbadmin.username}",
        target_id=dbadmin.id,
        target_name=dbadmin.username,
        previous_value=previous_value,
        new_value=admin_audit_state(dbadmin, response.policy),
        details={"password_changed": modified_admin.password is not None},
        request=request,
    )
    return response


@router.post("/admin/{username}/users/disable", responses={403: responses._403, 404: responses._404})
def disable_all_active_users(
    request: Request,
    dbadmin: Admin = Depends(get_admin_by_username),
    db: Session = Depends(get_db), admin: Admin = Depends(Admin.check_sudo_admin)
):
    """Disable all active users under a specific admin"""
    usernames = [
        row[0]
        for row in db.query(User.username)
        .filter(
            User.admin_id == dbadmin.id,
            User.status.in_((UserStatus.active, UserStatus.on_hold)),
        )
        .all()
    ]
    crud.disable_all_active_users(db=db, admin=dbadmin)
    startup_config = xray.config.include_db_users()
    xray.core.restart(startup_config)
    for node_id, node in list(xray.nodes.items()):
        if node.connected:
            xray.operations.restart_node(node_id, startup_config)
    AuditLogService.log(
        db,
        admin,
        "bulk.deactivate",
        "admin_users",
        f"Admin {admin.username} disabled {len(usernames)} users owned by {dbadmin.username}",
        target_id=dbadmin.id,
        target_name=dbadmin.username,
        details=summarize_targets(usernames),
        request=request,
    )
    return {"detail": "Users successfully disabled"}


@router.post("/admin/{username}/users/activate", responses={403: responses._403, 404: responses._404})
def activate_all_disabled_users(
    request: Request,
    dbadmin: Admin = Depends(get_admin_by_username),
    db: Session = Depends(get_db), admin: Admin = Depends(Admin.check_sudo_admin)
):
    """Activate all disabled users under a specific admin"""
    usernames = [
        row[0]
        for row in db.query(User.username)
        .filter(
            User.admin_id == dbadmin.id,
            User.status == UserStatus.disabled,
        )
        .all()
    ]
    crud.activate_all_disabled_users(db=db, admin=dbadmin)
    startup_config = xray.config.include_db_users()
    xray.core.restart(startup_config)
    for node_id, node in list(xray.nodes.items()):
        if node.connected:
            xray.operations.restart_node(node_id, startup_config)
    AuditLogService.log(
        db,
        admin,
        "bulk.activate",
        "admin_users",
        f"Admin {admin.username} activated {len(usernames)} users owned by {dbadmin.username}",
        target_id=dbadmin.id,
        target_name=dbadmin.username,
        details=summarize_targets(usernames),
        request=request,
    )
    return {"detail": "Users successfully activated"}


@router.post(
    "/admin/usage/reset/{username}",
    response_model=Admin,
    responses={403: responses._403},
)
def reset_admin_usage(
    request: Request,
    dbadmin: Admin = Depends(get_admin_by_username),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(Admin.check_sudo_admin)
):
    """Resets usage of admin."""
    previous_value = {"users_usage": dbadmin.users_usage}
    updated_admin = crud.reset_admin_usage(db, dbadmin)
    AuditLogService.log(
        db,
        current_admin,
        "admin.usage_reset",
        "admin",
        f"Admin {current_admin.username} reset usage for admin {dbadmin.username}",
        target_id=dbadmin.id,
        target_name=dbadmin.username,
        previous_value=previous_value,
        new_value={"users_usage": updated_admin.users_usage},
        request=request,
    )
    return updated_admin


@router.get(
    "/admin/usage/{username}",
    response_model=int,
    responses={403: responses._403},
)
def get_admin_usage(
    dbadmin: Admin = Depends(get_admin_by_username),
    current_admin: Admin = Depends(Admin.check_sudo_admin)
):
    """Retrieve the usage of given admin."""
    return dbadmin.users_usage
