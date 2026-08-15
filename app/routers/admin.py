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
    AdminCreate,
    AdminModify,
    ManagedAdmin,
    ManagedAdminCreate,
    ManagedAdminList,
    ManagedAdminModify,
    MarzhelpAdminPolicy,
    Token,
)
from app.utils import report, responses
from app.utils.jwt import create_admin_token
from config import LOGIN_NOTIFY_WHITE_LIST

router = APIRouter(tags=["Admin"], prefix="/api", responses={401: responses._401})


def managed_admin_response(dbadmin, settings=None, user_count: int = 0) -> ManagedAdmin:
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
        policy=policy,
    )


def get_client_ip(request: Request) -> str:
    """Extract the client's IP address from the request headers or client."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "Unknown"


@router.post("/admin/token", response_model=Token)
def admin_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Authenticate an admin and issue a token."""
    client_ip = get_client_ip(request)

    dbadmin = validate_admin(db, form_data.username, form_data.password)
    if not dbadmin:
        report.login(form_data.username, form_data.password, client_ip, False)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if client_ip not in LOGIN_NOTIFY_WHITE_LIST:
        report.login(form_data.username, "🔒", client_ip, True)

    return Token(access_token=create_admin_token(form_data.username, dbadmin.is_sudo))


@router.post(
    "/admin",
    response_model=Admin,
    responses={403: responses._403, 409: responses._409},
)
def create_admin(
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

    return dbadmin


@router.put(
    "/admin/{username}",
    response_model=Admin,
    responses={403: responses._403},
)
def modify_admin(
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

    updated_admin = crud.update_admin(db, dbadmin, modified_admin)

    return updated_admin


@router.delete(
    "/admin/{username}",
    responses={403: responses._403},
)
def remove_admin(
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

    crud.remove_admin(db, dbadmin)
    return {"detail": "Admin removed successfully"}


@router.get("/admin", response_model=Admin)
def get_current_admin(admin: Admin = Depends(Admin.get_current)):
    """Retrieve the current authenticated admin."""
    return admin


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
                item, settings_by_admin.get(item.id), user_counts.get(item.id, 0)
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
    return managed_admin_response(dbadmin, settings, 0)


@router.put(
    "/admin-management/{username}",
    response_model=ManagedAdmin,
    responses={403: responses._403, 404: responses._404},
)
def modify_managed_admin(
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

    dbadmin = crud.update_admin(db, dbadmin, modified_admin, commit=False)
    settings = crud.upsert_marzhelp_admin_policy(
        db, dbadmin.id, modified_admin.policy, commit=False
    )
    db.commit()
    db.refresh(dbadmin)
    db.refresh(settings)
    user_count = db.query(func.count(User.id)).filter(User.admin_id == dbadmin.id).scalar() or 0
    return managed_admin_response(dbadmin, settings, user_count)


@router.post("/admin/{username}/users/disable", responses={403: responses._403, 404: responses._404})
def disable_all_active_users(
    dbadmin: Admin = Depends(get_admin_by_username),
    db: Session = Depends(get_db), admin: Admin = Depends(Admin.check_sudo_admin)
):
    """Disable all active users under a specific admin"""
    crud.disable_all_active_users(db=db, admin=dbadmin)
    startup_config = xray.config.include_db_users()
    xray.core.restart(startup_config)
    for node_id, node in list(xray.nodes.items()):
        if node.connected:
            xray.operations.restart_node(node_id, startup_config)
    return {"detail": "Users successfully disabled"}


@router.post("/admin/{username}/users/activate", responses={403: responses._403, 404: responses._404})
def activate_all_disabled_users(
    dbadmin: Admin = Depends(get_admin_by_username),
    db: Session = Depends(get_db), admin: Admin = Depends(Admin.check_sudo_admin)
):
    """Activate all disabled users under a specific admin"""
    crud.activate_all_disabled_users(db=db, admin=dbadmin)
    startup_config = xray.config.include_db_users()
    xray.core.restart(startup_config)
    for node_id, node in list(xray.nodes.items()):
        if node.connected:
            xray.operations.restart_node(node_id, startup_config)
    return {"detail": "Users successfully activated"}


@router.post(
    "/admin/usage/reset/{username}",
    response_model=Admin,
    responses={403: responses._403},
)
def reset_admin_usage(
    dbadmin: Admin = Depends(get_admin_by_username),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(Admin.check_sudo_admin)
):
    """Resets usage of admin."""
    return crud.reset_admin_usage(db, dbadmin)


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
