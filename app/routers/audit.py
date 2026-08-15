from datetime import date, datetime, time, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_

from app.db import Session, get_db
from app.db.models import AdminAuditLog
from app.models.admin import Admin
from app.models.audit import AuditLogList, AuditLogOptions


router = APIRouter(
    tags=["Audit"],
    prefix="/api",
)


TEHRAN_TIMEZONE = ZoneInfo("Asia/Tehran")


def _utc_naive(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _tehran_date_boundary(value: Optional[date], end: bool = False) -> Optional[datetime]:
    if value is None:
        return None
    local_value = datetime.combine(value, time.max if end else time.min, TEHRAN_TIMEZONE)
    return local_value.astimezone(timezone.utc).replace(tzinfo=None)


@router.get("/audit-logs/options", response_model=AuditLogOptions)
def get_audit_log_options(
    db: Session = Depends(get_db),
    _: Admin = Depends(Admin.check_sudo_admin),
):
    admins = [
        value
        for (value,) in db.query(AdminAuditLog.admin_username)
        .distinct()
        .order_by(AdminAuditLog.admin_username.asc())
        .all()
    ]
    actions = [
        value
        for (value,) in db.query(AdminAuditLog.action)
        .distinct()
        .order_by(AdminAuditLog.action.asc())
        .all()
    ]
    return AuditLogOptions(admins=admins, actions=actions)


@router.get("/audit-logs", response_model=AuditLogList)
def get_audit_logs(
    offset: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=100),
    admin_username: Optional[str] = None,
    action: Optional[str] = None,
    target: Optional[str] = None,
    search: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    sort: str = Query("newest", pattern="^(newest|oldest)$"),
    db: Session = Depends(get_db),
    _: Admin = Depends(Admin.check_sudo_admin),
):
    query = db.query(AdminAuditLog)
    if admin_username:
        query = query.filter(
            AdminAuditLog.admin_username == admin_username
        )
    if action:
        query = query.filter(AdminAuditLog.action == action)
    if target:
        value = f"%{target.strip()}%"
        query = query.filter(
            or_(
                AdminAuditLog.target_name.ilike(value),
                AdminAuditLog.target_id.ilike(value),
            )
        )
    if search:
        value = f"%{search.strip()}%"
        query = query.filter(
            or_(
                AdminAuditLog.description.ilike(value),
                AdminAuditLog.admin_username.ilike(value),
                AdminAuditLog.action.ilike(value),
                AdminAuditLog.target_name.ilike(value),
                AdminAuditLog.target_id.ilike(value),
            )
        )
    normalized_from = _tehran_date_boundary(date_from)
    normalized_to = _tehran_date_boundary(date_to, end=True)
    if normalized_from:
        query = query.filter(AdminAuditLog.created_at >= normalized_from)
    if normalized_to:
        query = query.filter(AdminAuditLog.created_at <= normalized_to)

    total = query.count()
    order = (
        AdminAuditLog.created_at.asc()
        if sort == "oldest"
        else AdminAuditLog.created_at.desc()
    )
    logs = (
        query.order_by(order, AdminAuditLog.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return AuditLogList(
        logs=logs,
        total=total,
        offset=offset,
        limit=limit,
    )
