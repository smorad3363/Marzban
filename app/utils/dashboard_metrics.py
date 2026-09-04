"""Bounded, scope-aware aggregate queries for the Stage 9 dashboard."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, case, exists, func
from sqlalchemy.orm import Query, Session

from app.db import crud
from app.db.models import Admin, AdminHierarchy, MarzhelpAdminSettings, User
from app.models.system import (
    DashboardBillingModeMetric,
    DashboardOverview,
    DashboardWeekTrend,
)
from app.models.user import UserStatus
from app.utils import admin_hierarchy, marzhelp_policy
from app.utils.admin_billing import BillingMode


MODES = tuple(mode.value for mode in BillingMode)


def _week_bounds(now: datetime, offset_minutes: int) -> tuple[datetime, datetime, datetime]:
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    else:
        now = now.astimezone(timezone.utc)
    local_now = now + timedelta(minutes=offset_minutes)
    local_week_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(
        days=local_now.weekday()
    )
    current = (local_week_start - timedelta(minutes=offset_minutes)).replace(tzinfo=None)
    previous = current - timedelta(days=7)
    following = current + timedelta(days=7)
    return previous, current, following


def _visible_users(
    db: Session,
    actor: Admin,
    *,
    hierarchy_on: bool,
    actor_is_owner: bool,
    allowed_inbounds: set[str] | None,
) -> Query:
    query = db.query(User)
    if hierarchy_on and not actor_is_owner:
        query = query.filter(
            exists().where(
                and_(
                    AdminHierarchy.ancestor_id == actor.id,
                    AdminHierarchy.descendant_id == User.admin_id,
                )
            )
        )
    elif not hierarchy_on and not actor.is_sudo:
        query = query.filter(User.admin_id == actor.id)
    return crud.apply_inbound_access_filter(
        query,
        allowed_inbounds,
    )


def _visible_admins(
    db: Session,
    actor: Admin,
    *,
    hierarchy_on: bool,
    actor_is_owner: bool,
) -> Query:
    query = db.query(Admin)
    if hierarchy_on and not actor_is_owner:
        query = query.filter(
            exists().where(
                and_(
                    AdminHierarchy.ancestor_id == actor.id,
                    AdminHierarchy.descendant_id == Admin.id,
                )
            )
        )
    elif not hierarchy_on and not actor.is_sudo:
        query = query.filter(Admin.id == actor.id)
    return query


def overview(
    db: Session,
    actor: Admin,
    *,
    timezone_offset_minutes: int,
    now: datetime | None = None,
) -> DashboardOverview:
    generated_at = now or datetime.now(timezone.utc)
    normalized_now = (
        generated_at.replace(tzinfo=timezone.utc)
        if generated_at.tzinfo is None
        else generated_at.astimezone(timezone.utc)
    )
    previous_week, current_week, next_week = _week_bounds(
        normalized_now, timezone_offset_minutes
    )
    hierarchy_on = admin_hierarchy.hierarchy_enabled(db)
    actor_is_owner = (
        bool(actor.is_sudo)
        if not hierarchy_on
        else (
            admin_hierarchy.role_code(actor) == admin_hierarchy.OWNER
            and actor.id == admin_hierarchy.owner_id(db)
        )
    )
    allowed_inbounds = marzhelp_policy.allowed_inbound_tags(db, actor)
    visible = _visible_users(
        db,
        actor,
        hierarchy_on=hierarchy_on,
        actor_is_owner=actor_is_owner,
        allowed_inbounds=allowed_inbounds,
    )
    actor_billing_mode = (
        db.query(MarzhelpAdminSettings.billing_mode)
        .filter(MarzhelpAdminSettings.admin_id == actor.id)
        .scalar()
    )
    usage_visible = bool(
        actor_is_owner
        or actor_billing_mode is None
        or BillingMode(actor_billing_mode or BillingMode.LEGACY_COMPAT.value)
        not in {BillingMode.SEAT_CREDIT, BillingMode.USER_CREDIT}
    )
    aggregate = visible.with_entities(
        func.count(User.id),
        func.coalesce(func.sum(case((User.status == UserStatus.active, 1), else_=0)), 0),
        func.coalesce(func.sum(case((User.status == UserStatus.disabled, 1), else_=0)), 0),
        func.coalesce(func.sum(case((User.status == UserStatus.expired, 1), else_=0)), 0),
        func.coalesce(func.sum(case((User.status == UserStatus.limited, 1), else_=0)), 0),
        func.coalesce(func.sum(case((User.status == UserStatus.on_hold, 1), else_=0)), 0),
        func.coalesce(
            func.sum(
                case(
                    (
                        and_(User.online_at.is_not(None), User.online_at >= normalized_now.replace(tzinfo=None) - timedelta(hours=24)),
                        1,
                    ),
                    else_=0,
                )
            ),
            0,
        ),
        func.coalesce(func.sum(User.used_traffic), 0),
        func.coalesce(func.sum(User.data_limit), 0),
        func.coalesce(
            func.sum(case((and_(User.created_at >= current_week, User.created_at < next_week), 1), else_=0)),
            0,
        ),
        func.coalesce(
            func.sum(case((and_(User.created_at >= previous_week, User.created_at < current_week), 1), else_=0)),
            0,
        ),
    ).one()

    mode_expression = func.coalesce(MarzhelpAdminSettings.billing_mode, BillingMode.LEGACY_COMPAT.value)
    admin_rows = (
        _visible_admins(
            db,
            actor,
            hierarchy_on=hierarchy_on,
            actor_is_owner=actor_is_owner,
        )
        .join(MarzhelpAdminSettings, MarzhelpAdminSettings.admin_id == Admin.id)
        .with_entities(mode_expression.label("mode"), func.count(Admin.id))
        .group_by(mode_expression)
        .all()
    )
    admin_counts = {str(mode): int(count) for mode, count in admin_rows}

    user_rows = (
        _visible_users(
            db,
            actor,
            hierarchy_on=hierarchy_on,
            actor_is_owner=actor_is_owner,
            allowed_inbounds=allowed_inbounds,
        )
        .join(MarzhelpAdminSettings, MarzhelpAdminSettings.admin_id == User.admin_id)
        .with_entities(
            mode_expression.label("mode"),
            func.count(User.id),
            func.coalesce(func.sum(case((User.status == UserStatus.active, 1), else_=0)), 0),
            func.coalesce(func.sum(User.used_traffic), 0),
            func.coalesce(func.sum(User.data_limit), 0),
        )
        .group_by(mode_expression)
        .all()
    )
    user_by_mode = {
        str(mode): (int(count), int(active), int(used), int(allocated))
        for mode, count, active, used, allocated in user_rows
    }
    current_new = int(aggregate[9])
    previous_new = int(aggregate[10])
    change_percent = (
        round(((current_new - previous_new) * 100) / previous_new, 2)
        if previous_new
        else (0.0 if current_new == 0 else None)
    )
    generated = generated_at
    if generated.tzinfo is not None:
        generated = generated.astimezone(timezone.utc).replace(tzinfo=None)
    return DashboardOverview(
        generated_at=generated,
        timezone_offset_minutes=timezone_offset_minutes,
        current_week_start=current_week,
        previous_week_start=previous_week,
        total_users=int(aggregate[0]),
        active_users=int(aggregate[1]),
        disabled_users=int(aggregate[2]),
        expired_users=int(aggregate[3]),
        limited_users=int(aggregate[4]),
        on_hold_users=int(aggregate[5]),
        online_users=int(aggregate[6]),
        current_used_traffic=int(aggregate[7]) if usage_visible else None,
        allocated_quota=int(aggregate[8]),
        new_users=DashboardWeekTrend(
            current=current_new,
            previous=previous_new,
            change_percent=change_percent,
        ),
        billing_modes=[
            DashboardBillingModeMetric(
                billing_mode=mode,
                admin_count=admin_counts.get(mode, 0),
                user_count=user_by_mode.get(mode, (0, 0, 0, 0))[0],
                active_users=user_by_mode.get(mode, (0, 0, 0, 0))[1],
                current_used_traffic=(
                    user_by_mode.get(mode, (0, 0, 0, 0))[2]
                    if usage_visible
                    else None
                ),
                allocated_quota=user_by_mode.get(mode, (0, 0, 0, 0))[3],
            )
            for mode in MODES
        ],
    )
