from typing import List

from sqlalchemy.exc import IntegrityError
from fastapi import Depends, HTTPException, APIRouter, Request

from app.db import Session, crud, get_db
from app.models.admin import Admin
from app.models.user_template import (UserTemplateCreate, UserTemplateModify,
                                      UserTemplateResponse)
from app.dependencies import get_user_template
from app.utils.audit import AuditLogService, sanitize_audit_value

router = APIRouter(tags=['User Template'], prefix='/api')

@router.post("/user_template", response_model=UserTemplateResponse)
def add_user_template(
    request: Request,
    new_user_template: UserTemplateCreate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.check_sudo_admin)
):
    """
    Add a new user template

    - **name** can be up to 64 characters
    - **data_limit** must be in bytes and larger or equal to 0
    - **expire_duration** must be in seconds and larger or equat to 0
    - **inbounds** dictionary of protocol:inbound_tags, empty means all inbounds
    """
    try:
        template = crud.create_user_template(db, new_user_template)
        AuditLogService.log(
            db,
            admin,
            "template.create",
            "user_template",
            f"Admin {admin.username} created user template {template.name}",
            target_id=template.id,
            target_name=template.name,
            new_value=sanitize_audit_value(new_user_template),
            request=request,
        )
        return template
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Template by this name already exists")


@router.get("/user_template/{template_id}", response_model=UserTemplateResponse)
def get_user_template_endpoint(
    dbuser_template: UserTemplateResponse = Depends(get_user_template),
    admin: Admin = Depends(Admin.get_current)):
    """Get User Template information with id"""
    return dbuser_template


@router.put("/user_template/{template_id}", response_model=UserTemplateResponse)
def modify_user_template(
    request: Request,
    modify_user_template: UserTemplateModify,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.check_sudo_admin),
    dbuser_template: UserTemplateResponse = Depends(get_user_template)
):
    """
    Modify User Template

    - **name** can be up to 64 characters
    - **data_limit** must be in bytes and larger or equal to 0
    - **expire_duration** must be in seconds and larger or equat to 0
    - **inbounds** dictionary of protocol:inbound_tags, empty means all inbounds
    """
    try:
        previous_value = sanitize_audit_value(dbuser_template)
        template = crud.update_user_template(db, dbuser_template, modify_user_template)
        AuditLogService.log(
            db,
            admin,
            "template.update",
            "user_template",
            f"Admin {admin.username} updated user template {template.name}",
            target_id=template.id,
            target_name=template.name,
            previous_value=previous_value,
            new_value=sanitize_audit_value(template),
            request=request,
        )
        return template
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Template by this name already exists")


@router.delete("/user_template/{template_id}")
def remove_user_template(
    request: Request,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.check_sudo_admin),
    dbuser_template: UserTemplateResponse = Depends(get_user_template)
):
    """Remove a User Template by its ID"""
    target_id = dbuser_template.id
    target_name = dbuser_template.name
    previous_value = sanitize_audit_value(dbuser_template)
    result = crud.remove_user_template(db, dbuser_template)
    AuditLogService.log(
        db,
        admin,
        "template.delete",
        "user_template",
        f"Admin {admin.username} deleted user template {target_name}",
        target_id=target_id,
        target_name=target_name,
        previous_value=previous_value,
        request=request,
    )
    return result


@router.get("/user_template", response_model=List[UserTemplateResponse])
def get_user_templates(
    offset: int = None,
    limit: int = None,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current)
):
    """Get a list of User Templates with optional pagination"""
    return crud.get_user_templates(db, offset, limit)
