"""First-class Trial quota and cleanup operations."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256

from sqlalchemy import and_, exists, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import (
    Admin,
    AdminCreditTransfer,
    AdminHierarchy,
    MarzhelpAdminSettings,
    TrialCleanupOperation,
    User,
    UserPlanAssignment,
)
from app.utils import admin_hierarchy, marzhelp_policy


MAX_CLEANUP_BATCH = 500


def adjust_quota(
    db: Session,
    *,
    actor: Admin,
    target: Admin,
    amount: int,
    operation: str,
    idempotency_key: str,
    note: str | None,
) -> tuple[AdminCreditTransfer, bool]:
    if not admin_hierarchy.is_owner(db, actor):
        raise admin_hierarchy.HierarchyError(
            "owner_required", "Only Owner can grant or reclaim Trial quota"
        )
    if operation not in {"grant", "reclaim"} or amount <= 0:
        raise admin_hierarchy.HierarchyError("invalid_trial_adjustment", "Invalid Trial adjustment")
    reason = (note or f"system:trial_{operation}").strip()
    operation_type = f"trial_{operation}"
    settings = (
        db.query(MarzhelpAdminSettings)
        .filter(MarzhelpAdminSettings.admin_id == target.id)
        .with_for_update()
        .one_or_none()
    )
    if settings is None:
        raise admin_hierarchy.HierarchyError("policy_missing", "Target policy is missing")
    existing = (
        db.query(AdminCreditTransfer)
        .filter(AdminCreditTransfer.idempotency_key == idempotency_key)
        .with_for_update()
        .one_or_none()
    )
    if existing is not None:
        if (
            existing.actor_admin_id != actor.id
            or existing.adjusted_admin_id != target.id
            or existing.resource != "trial_quota"
            or existing.operation_type != operation_type
            or int(existing.amount) != amount
            or existing.note != reason
        ):
            raise admin_hierarchy.HierarchyError(
                "idempotency_conflict", "Idempotency key belongs to another Trial adjustment"
            )
        return existing, False
    before = int(settings.trial_quota or 0)
    if operation == "reclaim" and amount > before:
        raise admin_hierarchy.HierarchyError(
            "trial_reclaim_exceeds_available", "Reclaim exceeds remaining Trial quota"
        )
    after = before + amount if operation == "grant" else before - amount
    settings.trial_quota = after
    limit_before = int(settings.trial_quota_limit or 0)
    settings.trial_quota_limit = (
        limit_before + amount if operation == "grant" else max(limit_before - amount, 0)
    )
    row = AdminCreditTransfer(
        from_admin_id=actor.id if operation == "grant" else target.id,
        to_admin_id=target.id if operation == "grant" else actor.id,
        actor_admin_id=actor.id,
        adjusted_admin_id=target.id,
        resource="trial_quota",
        amount=amount,
        delta=amount if operation == "grant" else -amount,
        balance_before=before,
        balance_after=after,
        operation_type=operation_type,
        idempotency_key=idempotency_key,
        note=reason,
    )
    db.add(row)
    db.flush()
    return row, True


def reset_quota(
    db: Session,
    *,
    actor: Admin,
    target: Admin,
    idempotency_key: str,
    note: str | None,
) -> tuple[AdminCreditTransfer, bool]:
    if actor.id == target.id or (
        not admin_hierarchy.is_owner(db, actor)
        and not (
            admin_hierarchy.can_manage_children(db, actor)
            and admin_hierarchy.admin_in_scope(db, actor, target.id)
        )
    ):
        raise admin_hierarchy.HierarchyError(
            "trial_reset_forbidden", "Only an authorized parent can reset Trial quota"
        )
    reason = (note or "system:trial_quota_reset").strip()
    existing = (
        db.query(AdminCreditTransfer)
        .filter(AdminCreditTransfer.idempotency_key == idempotency_key)
        .with_for_update()
        .one_or_none()
    )
    if existing is not None:
        if (
            existing.actor_admin_id != actor.id
            or existing.adjusted_admin_id != target.id
            or existing.operation_type != "trial_reset"
            or existing.note != reason
        ):
            raise admin_hierarchy.HierarchyError(
                "idempotency_conflict", "Idempotency key belongs to another Trial operation"
            )
        return existing, False
    settings = (
        db.query(MarzhelpAdminSettings)
        .filter(MarzhelpAdminSettings.admin_id == target.id)
        .with_for_update()
        .one_or_none()
    )
    if settings is None:
        raise admin_hierarchy.HierarchyError("policy_missing", "Target policy is missing")
    before = int(settings.trial_quota or 0)
    after = int(settings.trial_quota_limit or 0)
    if after <= 0:
        raise admin_hierarchy.HierarchyError(
            "trial_quota_unconfigured", "Trial quota limit is not configured"
        )
    settings.trial_quota = after
    settings.trials_used = 0
    row = AdminCreditTransfer(
        from_admin_id=actor.id,
        to_admin_id=target.id,
        actor_admin_id=actor.id,
        adjusted_admin_id=target.id,
        resource="trial_quota",
        # `amount` is the positive reset entitlement. `delta` records the
        # actual balance change and may correctly be zero on an idempotent-like
        # manual reset while the quota is already full.
        amount=after,
        delta=after - before,
        balance_before=before,
        balance_after=after,
        operation_type="trial_reset",
        idempotency_key=idempotency_key,
        note=reason,
    )
    db.add(row)
    db.flush()
    return row, True


def _normalized_cutoff(value: datetime) -> datetime:
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def cleanup_query(db: Session, actor: Admin, expired_before: datetime):
    cutoff = _normalized_cutoff(expired_before)
    query = db.query(User).join(
        UserPlanAssignment,
        and_(
            UserPlanAssignment.user_id == User.id,
            UserPlanAssignment.operation_type == "create",
            UserPlanAssignment.is_trial.is_(True),
        ),
    ).filter(
        User.expire.is_not(None),
        User.expire <= int(cutoff.replace(tzinfo=timezone.utc).timestamp()),
    )
    if not admin_hierarchy.is_owner(db, actor):
        query = query.filter(
            or_(
                User.admin_id == actor.id,
                exists().where(
                    (AdminHierarchy.ancestor_id == actor.id)
                    & (AdminHierarchy.descendant_id == User.admin_id)
                ),
            )
        )
    # Ordering by the equality-filtered Trial index's final column lets MySQL
    # start from the small Trial set instead of scanning the full users table.
    return query.order_by(UserPlanAssignment.user_id)


def cleanup_preview(db: Session, actor: Admin, expired_before: datetime) -> tuple[int, list[str]]:
    query = cleanup_query(db, actor, expired_before)
    count = query.count()
    usernames = [row[0] for row in query.with_entities(User.username).limit(MAX_CLEANUP_BATCH).all()]
    return count, usernames


def cleanup(
    db: Session,
    *,
    actor: Admin,
    expired_before: datetime,
    idempotency_key: str,
) -> tuple[TrialCleanupOperation, bool]:
    cutoff = _normalized_cutoff(expired_before)
    fingerprint = sha256(f"{actor.id}:{cutoff.isoformat()}".encode()).hexdigest()
    existing = (
        db.query(TrialCleanupOperation)
        .filter(TrialCleanupOperation.idempotency_key == idempotency_key)
        .one_or_none()
    )
    if existing is not None:
        if existing.actor_admin_id != actor.id or existing.payload_fingerprint != fingerprint:
            raise admin_hierarchy.HierarchyError(
                "idempotency_conflict", "Idempotency key belongs to another Trial cleanup"
            )
        return existing, False

    operation = TrialCleanupOperation(
        actor_admin_id=actor.id,
        expired_before=cutoff,
        payload_fingerprint=fingerprint,
        idempotency_key=idempotency_key,
        deleted_count=0,
        deleted_usernames=[],
    )
    db.add(operation)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        existing = db.query(TrialCleanupOperation).filter(
            TrialCleanupOperation.idempotency_key == idempotency_key
        ).one_or_none()
        if existing is None:
            raise
        if existing.actor_admin_id != actor.id or existing.payload_fingerprint != fingerprint:
            raise admin_hierarchy.HierarchyError(
                "idempotency_conflict", "Idempotency key belongs to another Trial cleanup"
            )
        return existing, False

    users = cleanup_query(db, actor, cutoff).limit(MAX_CLEANUP_BATCH + 1).with_for_update().all()
    if len(users) > MAX_CLEANUP_BATCH:
        raise admin_hierarchy.HierarchyError(
            "trial_cleanup_batch_too_large",
            f"Trial cleanup is limited to {MAX_CLEANUP_BATCH} users per operation",
        )
    usernames = [user.username for user in users]
    for user in users:
        marzhelp_policy.capture_delete(db, user)
        db.delete(user)
    operation.deleted_count = len(usernames)
    operation.deleted_usernames = usernames
    db.flush()
    return operation, True
