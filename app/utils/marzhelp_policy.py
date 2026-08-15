"""Transactional Marzhelp policy and quota accounting.

All enforcement lives here so API, Telegram, CLI, jobs, and direct CRUD callers
apply the same rules. Marzhelp only edits the canonical settings rows.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import case, func, or_, update
from sqlalchemy.orm import Session

from app import xray
from app.db.models import (
    Admin,
    MarzhelpAccountingTransaction,
    MarzhelpAdminSettings,
    MarzhelpDeletedUser,
    User,
    UserUsageResetLogs,
)


class MarzhelpPolicyError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def calculate_delete_refund(data_limit: int | None, actual_used_traffic: int | None) -> int:
    """Return only unused finite traffic. Never return a negative value."""

    if data_limit is None:
        return 0
    return max(int(data_limit) - max(int(actual_used_traffic or 0), 0), 0)


def _settings(db: Session, admin_id: int | None, lock: bool = False) -> MarzhelpAdminSettings | None:
    if admin_id is None:
        return None
    query = db.query(MarzhelpAdminSettings).filter(MarzhelpAdminSettings.admin_id == admin_id)
    if lock:
        query = query.with_for_update()
    return query.first()


def _effective_data_limit(value: Any) -> int | None:
    if value in (None, 0):
        return None
    return int(value)


def _effective_expire(value: Any) -> int | None:
    if value in (None, 0):
        return None
    return int(value)


def capacity_weight(concurrent_user_limit: int | None) -> int:
    """Map one account to active capacity units.

    Legacy/unlimited accounts predate weighted quotas and keep their former
    one-row cost. New finite values consume their exact positive limit.
    """

    if concurrent_user_limit is None:
        return 1
    value = int(concurrent_user_limit)
    if value < 1:
        raise MarzhelpPolicyError(
            "invalid_user_limit",
            "MarzHelp: concurrent user limit must be a positive integer",
        )
    return value


def capacity_used(db: Session, admin_id: int, excluded_user_id: int | None = None) -> int:
    filters = [User.admin_id == admin_id]
    if excluded_user_id is not None:
        filters.append(User.id != excluded_user_id)
    weight = case(
        (User.concurrent_user_limit.is_(None), 1),
        (User.concurrent_user_limit < 1, 1),
        else_=User.concurrent_user_limit,
    )
    return int(db.query(func.coalesce(func.sum(weight), 0)).filter(*filters).scalar() or 0)


def allowed_inbound_tags(db: Session, admin: Admin) -> set[str] | None:
    """Return None for unrestricted access, otherwise exact allowed tags."""

    if admin.is_sudo:
        return None
    settings = _settings(db, admin.id)
    if settings is None or settings.all_inbounds:
        return None
    return set(settings.allowed_inbounds)


def allowed_user_limits(db: Session, admin: Admin) -> set[int] | None:
    if admin.is_sudo:
        return None
    settings = _settings(db, admin.id)
    if settings is None or settings.all_user_limits:
        return None
    return set(settings.allowed_user_limits)


def user_inbound_tags(dbuser: User) -> set[str]:
    return {tag for tags in dbuser.inbounds.values() for tag in tags}


def can_access_user(db: Session, admin: Admin, dbuser: User) -> bool:
    if admin.is_sudo:
        return True
    if dbuser.admin_id != admin.id:
        return False
    allowed = allowed_inbound_tags(db, admin)
    return allowed is None or user_inbound_tags(dbuser).issubset(allowed)


def _requested_inbound_tags(user: Any) -> set[str] | None:
    inbounds = getattr(user, "inbounds", None)
    if inbounds is None:
        return None
    return {tag for tags in inbounds.values() for tag in tags}


def _validate_inbounds(settings: MarzhelpAdminSettings, inbound_tags: set[str] | None) -> None:
    if settings.all_inbounds or inbound_tags is None:
        return
    unauthorized = sorted(inbound_tags - set(settings.allowed_inbounds))
    if unauthorized:
        raise MarzhelpPolicyError(
            "inbound_forbidden",
            "MarzHelp: unauthorized inbound(s): " + ", ".join(unauthorized),
        )


def _validate_concurrent_user_limit(
    settings: MarzhelpAdminSettings,
    concurrent_user_limit: int | None,
) -> None:
    if settings.all_user_limits:
        capacity_weight(concurrent_user_limit)
        return
    if concurrent_user_limit is None or int(concurrent_user_limit) not in settings.allowed_user_limits:
        raise MarzhelpPolicyError(
            "user_limit_forbidden",
            "MarzHelp: this concurrent user limit is not allowed for the admin",
        )


def _adjust_capacity(
    db: Session,
    settings: MarzhelpAdminSettings,
    delta: int,
) -> None:
    if delta == 0:
        return

    # Optimistic compare-and-swap complements SELECT FOR UPDATE and also keeps
    # SQLite tests safe, where row-level FOR UPDATE is unavailable.
    for _ in range(3):
        db.expire(settings, ["capacity_used"])
        stored = int(settings.capacity_used or 0)
        actual = capacity_used(db, settings.admin_id)
        baseline = max(stored, actual)
        target = max(baseline + delta, 0)
        if settings.max_users is not None and target > int(settings.max_users):
            remaining = max(int(settings.max_users) - baseline, 0)
            raise MarzhelpPolicyError(
                "weighted_capacity_exceeded",
                (
                    "MarzHelp: insufficient user capacity; "
                    f"requested {max(delta, 0)}, remaining {remaining}"
                ),
            )
        result = db.execute(
            update(MarzhelpAdminSettings)
            .where(
                MarzhelpAdminSettings.admin_id == settings.admin_id,
                MarzhelpAdminSettings.capacity_used == stored,
                or_(
                    MarzhelpAdminSettings.max_users.is_(None),
                    target <= MarzhelpAdminSettings.max_users,
                ),
            )
            .values(capacity_used=target, updated_at=func.now())
        )
        if result.rowcount == 1:
            settings.capacity_used = target
            return
        db.expire(settings, ["capacity_used", "max_users"])

    raise MarzhelpPolicyError(
        "capacity_conflict",
        "MarzHelp: user capacity changed concurrently; retry the request",
    )


def _validate_account(settings: MarzhelpAdminSettings) -> None:
    if settings.expiry_date is not None and settings.expiry_date < date.today():
        raise MarzhelpPolicyError("admin_expired", "MarzHelp: admin account is expired")


def _validate_data_limit(settings: MarzhelpAdminSettings, data_limit: int | None) -> None:
    if settings.prevent_unlimited_traffic and data_limit is None:
        raise MarzhelpPolicyError(
            "unlimited_traffic_forbidden",
            "MarzHelp: unlimited traffic is not allowed for this admin",
        )


def _validate_expiration(
    settings: MarzhelpAdminSettings,
    expire: int | None,
    on_hold_duration: int | None = None,
    now: datetime | None = None,
) -> None:
    maximum_days = settings.max_user_duration_days
    if maximum_days is None or maximum_days <= 0:
        return

    maximum_seconds = int(maximum_days) * 86400
    if on_hold_duration not in (None, 0):
        if int(on_hold_duration) > maximum_seconds:
            raise MarzhelpPolicyError(
                "duration_exceeded",
                f"MarzHelp: account duration cannot exceed {maximum_days} days",
            )
        return

    if expire is None:
        raise MarzhelpPolicyError(
            "unlimited_expiration_forbidden",
            "MarzHelp: no-expiry accounts are not allowed for this admin",
        )

    now_timestamp = int((now or datetime.now(timezone.utc)).timestamp())
    if int(expire) - now_timestamp > maximum_seconds:
        raise MarzhelpPolicyError(
            "duration_exceeded",
            f"MarzHelp: account duration cannot exceed {maximum_days} days",
        )


def _current_spend(db: Session, admin_id: int, mode: str, excluded_user_id: int | None = None) -> int:
    user_filter = [User.admin_id == admin_id]
    if excluded_user_id is not None:
        user_filter.append(User.id != excluded_user_id)

    if mode == "created_traffic":
        current_allocation = (
            db.query(func.coalesce(func.sum(func.coalesce(User.data_limit, User.used_traffic)), 0))
            .filter(*user_filter)
            .scalar()
            or 0
        )
        unlimited_reset_usage = (
            db.query(func.coalesce(func.sum(UserUsageResetLogs.used_traffic_at_reset), 0))
            .join(User, User.id == UserUsageResetLogs.user_id)
            .filter(*user_filter, User.data_limit.is_(None))
            .scalar()
            or 0
        )
        current = int(current_allocation) + int(unlimited_reset_usage)
    else:
        current_usage = db.query(func.coalesce(func.sum(User.used_traffic), 0)).filter(*user_filter).scalar() or 0
        reset_usage = (
            db.query(func.coalesce(func.sum(UserUsageResetLogs.used_traffic_at_reset), 0))
            .join(User, User.id == UserUsageResetLogs.user_id)
            .filter(*user_filter)
            .scalar()
            or 0
        )
        current = int(current_usage) + int(reset_usage)

    deleted = (
        db.query(func.coalesce(func.sum(MarzhelpDeletedUser.used_traffic_total), 0))
        .filter(MarzhelpDeletedUser.admin_id == admin_id)
        .scalar()
        or 0
    )
    return int(current) + int(deleted)


def _validate_traffic_credit(
    db: Session,
    settings: MarzhelpAdminSettings,
    data_limit: int | None,
    excluded_user_id: int | None = None,
) -> None:
    if settings.total_traffic is None or settings.total_traffic <= 0:
        return

    mode = settings.calculate_volume or "used_traffic"
    # Replacing a finite package must exclude the old allocation. Usage-based
    # accounting, however, still includes the user's already-consumed traffic.
    spend_exclusion = excluded_user_id if mode == "created_traffic" else None
    spent = _current_spend(db, settings.admin_id, mode, spend_exclusion)
    if mode == "created_traffic":
        if data_limit is None:
            raise MarzhelpPolicyError(
                "unlimited_traffic_forbidden",
                "MarzHelp: unlimited traffic is not allowed with finite admin credit",
            )
        spent += int(data_limit)

    if spent > int(settings.total_traffic) or (
        mode == "used_traffic" and spent >= int(settings.total_traffic)
    ):
        raise MarzhelpPolicyError("traffic_exhausted", "MarzHelp: admin traffic credit is exhausted")


def _consume_allowance(db: Session, settings: MarzhelpAdminSettings) -> None:
    if settings.user_limit is None:
        return
    result = db.execute(
        update(MarzhelpAdminSettings)
        .where(
            MarzhelpAdminSettings.admin_id == settings.admin_id,
            MarzhelpAdminSettings.user_limit > 0,
        )
        .values(user_limit=MarzhelpAdminSettings.user_limit - 1, updated_at=func.now())
    )
    if result.rowcount != 1:
        raise MarzhelpPolicyError(
            "operation_allowance_exhausted",
            "MarzHelp: admin create/renew allowance is exhausted",
        )


def _record(
    db: Session,
    operation_key: str,
    operation_type: str,
    admin_id: int,
    user_id: int | None,
    username: str | None,
    traffic_delta: int = 0,
    allowance_delta: int = 0,
    details: dict[str, Any] | None = None,
) -> None:
    db.add(
        MarzhelpAccountingTransaction(
            operation_key=operation_key,
            operation_type=operation_type,
            admin_id=admin_id,
            user_id=user_id,
            username=username,
            traffic_delta=traffic_delta,
            allowance_delta=allowance_delta,
            details=details,
        )
    )


def validate_create(db: Session, admin_id: int | None, user: Any) -> MarzhelpAdminSettings | None:
    settings = _settings(db, admin_id, lock=True)
    if settings is None:
        return None
    _validate_account(settings)
    if settings.prevent_user_creation:
        raise MarzhelpPolicyError(
            "creation_forbidden", "MarzHelp: user creation is disabled for this admin"
        )

    concurrent_user_limit = getattr(user, "concurrent_user_limit", None)
    _validate_inbounds(settings, _requested_inbound_tags(user))
    _validate_concurrent_user_limit(settings, concurrent_user_limit)
    _adjust_capacity(db, settings, capacity_weight(concurrent_user_limit))

    data_limit = _effective_data_limit(user.data_limit)
    expire = _effective_expire(user.expire)
    _validate_data_limit(settings, data_limit)
    _validate_expiration(settings, expire, getattr(user, "on_hold_expire_duration", None))
    _validate_traffic_credit(db, settings, data_limit)

    next_plan = getattr(user, "next_plan", None)
    if next_plan is not None:
        _validate_data_limit(settings, _effective_data_limit(next_plan.data_limit))
        _validate_expiration(settings, _effective_expire(next_plan.expire))

    _consume_allowance(db, settings)
    return settings


def record_create(db: Session, dbuser: User, allowance_consumed: bool) -> None:
    if not allowance_consumed or dbuser.admin_id is None:
        return
    _record(
        db,
        f"create:{dbuser.id}",
        "create",
        dbuser.admin_id,
        dbuser.id,
        dbuser.username,
        allowance_delta=-1,
        details={"data_limit": dbuser.data_limit, "expire": dbuser.expire},
    )


def _is_renewal(dbuser: User, modify: Any) -> bool:
    if modify.data_limit is not None:
        old_limit = _effective_data_limit(dbuser.data_limit)
        new_limit = _effective_data_limit(modify.data_limit)
        if (new_limit is None and old_limit is not None) or (
            new_limit is not None and old_limit is not None and new_limit > old_limit
        ):
            return True
    if modify.expire is not None:
        old_expire = _effective_expire(dbuser.expire)
        new_expire = _effective_expire(modify.expire)
        if (new_expire is None and old_expire is not None) or (
            new_expire is not None and old_expire is not None and new_expire > old_expire
        ):
            return True
    return False


def validate_update(db: Session, dbuser: User, modify: Any) -> tuple[bool, bool]:
    settings = _settings(db, dbuser.admin_id, lock=True)
    if settings is None:
        return False, False

    renewal = _is_renewal(dbuser, modify)
    fields_set = getattr(modify, "model_fields_set", set())
    concurrent_limit_changed = (
        "concurrent_user_limit" in fields_set
        and getattr(modify, "concurrent_user_limit", None) != dbuser.concurrent_user_limit
    )
    inbound_changed = bool(getattr(modify, "inbounds", None)) or bool(getattr(modify, "proxies", None))
    plan_change = (
        renewal
        or modify.data_limit is not None
        or modify.expire is not None
        or modify.next_plan is not None
        or concurrent_limit_changed
        or inbound_changed
    )
    if not plan_change:
        return False, False

    _validate_account(settings)
    concurrent_user_limit = (
        getattr(modify, "concurrent_user_limit", None)
        if concurrent_limit_changed
        else dbuser.concurrent_user_limit
    )
    final_inbounds = {key: list(value) for key, value in dbuser.inbounds.items()}
    modified_proxies = getattr(modify, "proxies", None) or {}
    modified_inbounds = getattr(modify, "inbounds", None) or {}
    if modified_proxies:
        final_inbounds = {
            proxy_type: modified_inbounds.get(
                proxy_type,
                final_inbounds.get(
                    proxy_type,
                    [item["tag"] for item in xray.config.inbounds_by_protocol.get(proxy_type, [])],
                ),
            )
            for proxy_type in modified_proxies
        }
    else:
        final_inbounds.update(modified_inbounds)
    _validate_inbounds(
        settings,
        {tag for tags in final_inbounds.values() for tag in tags},
    )
    _validate_concurrent_user_limit(settings, concurrent_user_limit)
    old_capacity = capacity_weight(dbuser.concurrent_user_limit)
    new_capacity = capacity_weight(concurrent_user_limit)
    _adjust_capacity(db, settings, new_capacity - old_capacity)
    data_limit = (
        _effective_data_limit(modify.data_limit)
        if modify.data_limit is not None
        else dbuser.data_limit
    )
    expire = _effective_expire(modify.expire) if modify.expire is not None else dbuser.expire
    on_hold_duration = (
        modify.on_hold_expire_duration
        if modify.on_hold_expire_duration is not None
        else dbuser.on_hold_expire_duration
    )
    _validate_data_limit(settings, data_limit)
    _validate_expiration(settings, expire, on_hold_duration)
    _validate_traffic_credit(db, settings, data_limit, excluded_user_id=dbuser.id)

    if modify.next_plan is not None:
        _validate_data_limit(settings, _effective_data_limit(modify.next_plan.data_limit))
        _validate_expiration(settings, _effective_expire(modify.next_plan.expire))

    if renewal:
        _consume_allowance(db, settings)
    return renewal, settings.user_limit is not None


def record_renewal(db: Session, dbuser: User, allowance_consumed: bool) -> None:
    if not allowance_consumed or dbuser.admin_id is None:
        return
    # Absolute plan updates are naturally idempotent: retrying an already-applied
    # value is not classified as another renewal.
    key = f"renew:{dbuser.id}:{uuid4().hex}"
    _record(
        db,
        key,
        "renew",
        dbuser.admin_id,
        dbuser.id,
        dbuser.username,
        allowance_delta=-1,
        details={"data_limit": dbuser.data_limit, "expire": dbuser.expire},
    )


def resulting_next_plan_data_limit(dbuser: User) -> int | None:
    remaining = 0
    if not dbuser.next_plan.add_remaining_traffic:
        remaining = max(
            int(dbuser.data_limit or 0) - int(dbuser.used_traffic or 0),
            0,
        )
    result = int(dbuser.next_plan.data_limit or 0) + remaining
    return result or None


def validate_next_plan_activation(db: Session, dbuser: User) -> bool:
    if dbuser.next_plan is None:
        return False
    settings = _settings(db, dbuser.admin_id, lock=True)
    if settings is None:
        return False
    _validate_account(settings)
    data_limit = resulting_next_plan_data_limit(dbuser)
    expire = _effective_expire(dbuser.next_plan.expire)
    _validate_data_limit(settings, data_limit)
    _validate_expiration(settings, expire)
    _validate_traffic_credit(db, settings, data_limit, excluded_user_id=dbuser.id)
    _consume_allowance(db, settings)
    return settings.user_limit is not None


def validate_reset(db: Session, dbuser: User) -> None:
    settings = _settings(db, dbuser.admin_id, lock=True)
    if settings is not None and settings.prevent_user_reset:
        raise MarzhelpPolicyError("reset_forbidden", "MarzHelp: resetting user traffic is disabled")


def validate_revoke(db: Session, dbuser: User) -> None:
    settings = _settings(db, dbuser.admin_id, lock=True)
    if settings is not None and settings.prevent_revoke_subscription:
        raise MarzhelpPolicyError("revoke_forbidden", "MarzHelp: revoking subscriptions is disabled")


def validate_activation(db: Session, dbuser: User) -> None:
    """Revalidate the effective plan before any alternate activation path."""

    settings = _settings(db, dbuser.admin_id, lock=True)
    if settings is None:
        return
    _validate_account(settings)
    _validate_data_limit(settings, dbuser.data_limit)
    _validate_expiration(
        settings,
        dbuser.expire,
        dbuser.on_hold_expire_duration,
    )
    _validate_traffic_credit(
        db,
        settings,
        dbuser.data_limit,
        excluded_user_id=dbuser.id,
    )


def validate_start_expiration(db: Session, dbuser: User, expire: int) -> None:
    settings = _settings(db, dbuser.admin_id, lock=True)
    if settings is None:
        return
    _validate_account(settings)
    _validate_expiration(settings, expire)


def validate_transfer(db: Session, dbuser: User, new_admin_id: int) -> None:
    owner_changes = dbuser.admin_id != new_admin_id
    settings = _settings(db, new_admin_id, lock=True)
    if settings is not None:
        _validate_account(settings)
        _validate_inbounds(settings, user_inbound_tags(dbuser))
        _validate_concurrent_user_limit(settings, dbuser.concurrent_user_limit)
        _validate_data_limit(settings, dbuser.data_limit)
        _validate_expiration(settings, dbuser.expire, dbuser.on_hold_expire_duration)
        _validate_traffic_credit(db, settings, dbuser.data_limit)
        if owner_changes:
            _adjust_capacity(db, settings, capacity_weight(dbuser.concurrent_user_limit))
    previous_settings = _settings(db, dbuser.admin_id, lock=True)
    if owner_changes and previous_settings is not None:
        _adjust_capacity(db, previous_settings, -capacity_weight(dbuser.concurrent_user_limit))


def capture_delete(db: Session, dbuser: User) -> int:
    if dbuser.admin_id is None:
        return 0
    settings = _settings(db, dbuser.admin_id, lock=True)
    if settings is not None and settings.prevent_user_deletion:
        raise MarzhelpPolicyError("deletion_forbidden", "MarzHelp: user deletion is disabled")
    existing = (
        db.query(MarzhelpDeletedUser)
        .filter(MarzhelpDeletedUser.user_id == dbuser.id)
        .first()
    )
    if existing is not None:
        return 0

    if settings is not None:
        _adjust_capacity(db, settings, -capacity_weight(dbuser.concurrent_user_limit))

    used = max(int(dbuser.lifetime_used_traffic or 0), 0)
    refund = calculate_delete_refund(dbuser.data_limit, used)
    ledger = MarzhelpDeletedUser(
        user_id=dbuser.id,
        admin_id=dbuser.admin_id,
        username=dbuser.username,
        used_traffic_total=used,
        allocated_traffic=dbuser.data_limit,
        refunded_traffic=refund,
    )
    db.add(ledger)
    _record(
        db,
        f"delete:{dbuser.id}",
        "delete_refund",
        dbuser.admin_id,
        dbuser.id,
        dbuser.username,
        traffic_delta=refund,
        details={
            "allocated_traffic": dbuser.data_limit,
            "actual_used_traffic": used,
            "refundable_traffic": refund,
        },
    )
    return refund
