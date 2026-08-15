from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum
from ipaddress import ip_address
from typing import Any, Iterable, Mapping, Optional

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.db.models import Admin as DBAdmin
from app.db.models import AdminAuditLog


REDACTED = "[REDACTED]"
SENSITIVE_KEY_PARTS = (
    "password",
    "token",
    "secret",
    "api_key",
    "authorization",
    "cookie",
    "certificate",
    "private_key",
    "webhook",
    "proxy",
    "subscription_url",
)
MAX_COLLECTION_ITEMS = 100
MAX_STRING_LENGTH = 4096


class AuditStatus(str, Enum):
    success = "success"
    failed = "failed"


def get_client_ip(request: Optional[Request]) -> Optional[str]:
    if request is None:
        return None
    forwarded_for = request.headers.get("X-Forwarded-For")
    value = (
        forwarded_for.split(",")[0].strip()
        if forwarded_for
        else request.client.host if request.client else None
    )
    if not value:
        return None
    try:
        return str(ip_address(value))
    except ValueError:
        return value[:64]


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return any(part in normalized for part in SENSITIVE_KEY_PARTS)


def sanitize_audit_value(value: Any, key: str = "") -> Any:
    """Return a bounded JSON value with credentials and secrets removed."""

    if key and _is_sensitive_key(key):
        return REDACTED
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, str):
        return value[:MAX_STRING_LENGTH]
    if hasattr(value, "model_dump"):
        value = value.model_dump()
    if isinstance(value, Mapping):
        result = {}
        for index, (child_key, child_value) in enumerate(value.items()):
            if index >= MAX_COLLECTION_ITEMS:
                result["_truncated"] = len(value) - MAX_COLLECTION_ITEMS
                break
            string_key = str(child_key)[:128]
            result[string_key] = sanitize_audit_value(child_value, string_key)
        return result
    if isinstance(value, Iterable):
        values = list(value)
        result = [
            sanitize_audit_value(item)
            for item in values[:MAX_COLLECTION_ITEMS]
        ]
        if len(values) > MAX_COLLECTION_ITEMS:
            result.append(
                {"_truncated": len(values) - MAX_COLLECTION_ITEMS}
            )
        return result
    return sanitize_audit_value(jsonable_encoder(value), key)


def user_audit_state(user: Any) -> dict[str, Any]:
    return sanitize_audit_value(
        {
            "username": getattr(user, "username", None),
            "status": getattr(user, "status", None),
            "data_limit": getattr(user, "data_limit", None),
            "used_traffic": getattr(user, "used_traffic", None),
            "expire": getattr(user, "expire", None),
            "data_limit_reset_strategy": getattr(
                user, "data_limit_reset_strategy", None
            ),
            "admin": getattr(
                getattr(user, "admin", None),
                "username",
                None,
            ),
            "note": getattr(user, "note", None),
            "on_hold_expire_duration": getattr(
                user, "on_hold_expire_duration", None
            ),
            "auto_delete_in_days": getattr(
                user, "auto_delete_in_days", None
            ),
        }
    )


def admin_audit_state(admin: Any, policy: Any = None) -> dict[str, Any]:
    """Return an audit-safe admin snapshot without credentials or webhooks."""

    policy_value = policy.model_dump() if hasattr(policy, "model_dump") else policy
    return sanitize_audit_value(
        {
            "username": getattr(admin, "username", None),
            "is_sudo": getattr(admin, "is_sudo", None),
            "telegram_id": getattr(admin, "telegram_id", None),
            "users_usage": getattr(admin, "users_usage", None),
            "password_changed": bool(
                getattr(admin, "password_reset_at", None)
            ),
            "policy": policy_value,
        }
    )


def summarize_targets(values: Iterable[str]) -> dict[str, Any]:
    usernames = list(dict.fromkeys(str(value) for value in values))
    return {
        "count": len(usernames),
        "usernames": usernames[:MAX_COLLECTION_ITEMS],
        "omitted": max(0, len(usernames) - MAX_COLLECTION_ITEMS),
    }


def changed_fields(
    previous_value: Mapping[str, Any],
    new_value: Mapping[str, Any],
) -> list[str]:
    return sorted(
        key
        for key in set(previous_value) | set(new_value)
        if previous_value.get(key) != new_value.get(key)
    )


def classify_user_change(
    previous_value: Mapping[str, Any],
    new_value: Mapping[str, Any],
) -> str:
    changed = changed_fields(previous_value, new_value)
    if changed == ["status"]:
        if new_value.get("status") == "active":
            return "user.activate"
        if new_value.get("status") == "disabled":
            return "user.deactivate"

    old_data = previous_value.get("data_limit")
    new_data = new_value.get("data_limit")
    old_expire = previous_value.get("expire")
    new_expire = new_value.get("expire")
    data_increased = (
        "data_limit" in changed
        and new_data is not None
        and (old_data is None or new_data > old_data)
    )
    expire_increased = (
        "expire" in changed
        and new_expire is not None
        and (old_expire is None or new_expire > old_expire)
    )
    if data_increased and expire_increased:
        return "user.renew"
    if changed == ["data_limit"]:
        return (
            "user.traffic_add"
            if data_increased
            else "user.traffic_subtract"
        )
    if changed == ["expire"]:
        return (
            "user.expiration_add"
            if expire_increased
            else "user.expiration_subtract"
        )
    if "status" in changed:
        if new_value.get("status") == "active":
            return "user.activate"
        if new_value.get("status") == "disabled":
            return "user.deactivate"
    if data_increased or expire_increased:
        return "user.renew"
    return "user.update"


class AuditLogService:
    @staticmethod
    def log(
        db: Session,
        actor: Any,
        action: str,
        target_type: str,
        description: str,
        *,
        target_id: Any = None,
        target_name: Optional[str] = None,
        previous_value: Any = None,
        new_value: Any = None,
        details: Any = None,
        request: Optional[Request] = None,
        status: AuditStatus | str = AuditStatus.success,
        commit: bool = True,
    ) -> AdminAuditLog:
        authenticated_username = getattr(actor, "username", None)
        username = authenticated_username or str(actor or "unknown")
        dbadmin = (
            db.query(DBAdmin)
            .filter(DBAdmin.username == username)
            .first()
            if authenticated_username
            else None
        )
        entry = AdminAuditLog(
            admin_id=dbadmin.id if dbadmin else None,
            admin_username=username[:34],
            action=action[:64],
            target_type=target_type[:64],
            target_id=(
                str(target_id)[:128]
                if target_id is not None
                else None
            ),
            target_name=target_name[:256] if target_name else None,
            description=description[:MAX_STRING_LENGTH],
            previous_value=sanitize_audit_value(previous_value),
            new_value=sanitize_audit_value(new_value),
            details=sanitize_audit_value(details),
            ip_address=get_client_ip(request),
            status=(
                status.value if isinstance(status, AuditStatus) else str(status)
            )[:16],
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        db.add(entry)
        if commit:
            db.commit()
            db.refresh(entry)
        else:
            db.flush()
        return entry
