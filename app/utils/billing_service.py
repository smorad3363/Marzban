"""Explicit billing-mode transitions and allocated-traffic refund workflow."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import (
    Admin,
    AdminCreditTransfer,
    AdminUserPlan,
    AdminUserPlanVersion,
    AllocatedTrafficRefundEvent,
    AllocatedTrafficRefundRequest,
    MarzhelpAccountingTransaction,
    MarzhelpAdminSettings,
    User,
    UserPlanAssignment,
)
from app.utils import admin_billing, admin_hierarchy


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _operation_key(kind: str, value: str) -> str:
    return f"{kind}:{hashlib.sha256(value.encode()).hexdigest()}"


def _expire_datetime(value: int | None) -> datetime | None:
    return datetime.fromtimestamp(value, timezone.utc).replace(tzinfo=None) if value else None


def assign_billing_mode(
    db: Session,
    *,
    actor: Admin,
    target: Admin,
    mode: admin_billing.BillingMode,
    idempotency_key: str,
    reason: str,
) -> tuple[MarzhelpAdminSettings, bool]:
    """Owner-only explicit assignment; never reinterpret a non-empty legacy account."""

    if not admin_hierarchy.is_owner(db, actor):
        raise admin_hierarchy.HierarchyError("owner_required", "Only Owner can assign billing modes")
    operation_key = _operation_key("billing-mode", idempotency_key)
    existing = db.query(MarzhelpAccountingTransaction).filter(
        MarzhelpAccountingTransaction.operation_key == operation_key
    ).one_or_none()
    if existing is not None:
        details = existing.details or {}
        if (
            existing.admin_id != target.id
            or details.get("mode") != mode.value
            or details.get("reason") != reason
        ):
            raise admin_hierarchy.HierarchyError(
                "idempotency_conflict", "Idempotency key belongs to another billing-mode assignment"
            )
        return db.get(MarzhelpAdminSettings, target.id), False

    settings = db.query(MarzhelpAdminSettings).filter(
        MarzhelpAdminSettings.admin_id == target.id
    ).with_for_update().one_or_none()
    if settings is None:
        raise admin_hierarchy.HierarchyError("policy_missing", "Target billing policy is missing")
    previous = admin_billing.billing_mode(settings)
    if previous != mode:
        has_users = bool(db.query(User.id).filter(User.admin_id == target.id).first())
        has_economic_state = any(
            int(value or 0) != 0
            for value in (
                settings.used_traffic,
                settings.capacity_used,
                settings.delegated_traffic,
                settings.renewals_used,
            )
        )
        if has_users or has_economic_state:
            raise admin_hierarchy.HierarchyError(
                "billing_mode_transition_requires_settlement",
                "Existing users or balances must be explicitly settled before changing billing mode",
            )
        settings.billing_mode = mode.value
    db.add(
        MarzhelpAccountingTransaction(
            operation_key=operation_key,
            operation_type="billing_mode",
            admin_id=target.id,
            result="consumed",
            details={
                "previous_mode": previous.value,
                "mode": mode.value,
                "reason": reason,
                "actor_admin_id": actor.id,
            },
        )
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return assign_billing_mode(
            db,
            actor=actor,
            target=target,
            mode=mode,
            idempotency_key=idempotency_key,
            reason=reason,
        )
    db.refresh(settings)
    return settings, True


def _authorized_reviewer(db: Session, account: Admin) -> int:
    if account.parent_admin_id is not None:
        return int(account.parent_admin_id)
    owner = admin_hierarchy.owner_id(db)
    if owner is None:
        raise admin_hierarchy.HierarchyError("owner_missing", "Owner is not configured")
    return int(owner)


def create_refund_request(
    db: Session,
    *,
    actor: Admin,
    user: User,
    requested_refund_amount: int,
    request_reason: str,
    request_note: str | None,
    correlation_id: str,
    idempotency_key: str,
) -> tuple[AllocatedTrafficRefundRequest, bool]:
    existing = db.query(AllocatedTrafficRefundRequest).filter(
        AllocatedTrafficRefundRequest.idempotency_key == idempotency_key
    ).one_or_none()
    if existing is not None:
        if (
            existing.requester_admin_id != actor.id
            or existing.target_user_id != user.id
            or existing.requested_refund_amount != requested_refund_amount
            or existing.request_reason != request_reason
            or existing.request_note != request_note
            or existing.correlation_id != correlation_id
        ):
            raise admin_hierarchy.HierarchyError(
                "idempotency_conflict", "Idempotency key belongs to another refund request"
            )
        return existing, False
    if not admin_hierarchy.can_access_user(db, actor, user):
        raise admin_hierarchy.HierarchyError("user_scope_forbidden", "User is outside actor scope")
    if user.admin_id is None:
        raise admin_hierarchy.HierarchyError("user_owner_missing", "User has no owning administrator")
    account = db.get(Admin, user.admin_id)
    settings = db.query(MarzhelpAdminSettings).filter(
        MarzhelpAdminSettings.admin_id == user.admin_id
    ).with_for_update().one_or_none()
    if account is None or settings is None:
        raise admin_hierarchy.HierarchyError("policy_missing", "User owner billing policy is missing")
    if admin_billing.billing_mode(settings) != admin_billing.BillingMode.ALLOCATED_TRAFFIC:
        raise admin_hierarchy.HierarchyError(
            "refund_mode_forbidden", "Refund requests are only valid for ALLOCATED_TRAFFIC"
        )
    current_quota = int(user.data_limit or 0)
    used = int(user.used_traffic or 0)
    remaining = max(current_quota - used, 0)
    if requested_refund_amount > remaining:
        raise admin_hierarchy.HierarchyError(
            "refund_exceeds_remaining", "Requested refund exceeds snapshot remaining traffic"
        )
    assignment = db.query(UserPlanAssignment).filter(
        UserPlanAssignment.user_id == user.id
    ).order_by(UserPlanAssignment.id.desc()).first()
    plan = db.get(AdminUserPlan, assignment.plan_id) if assignment is not None else None
    version = db.get(AdminUserPlanVersion, assignment.version_id) if assignment is not None else None
    row = AllocatedTrafficRefundRequest(
        requester_admin_id=actor.id,
        account_admin_id=account.id,
        reviewer_admin_id=_authorized_reviewer(db, account),
        target_user_id=user.id,
        target_username=user.username,
        snapshot_billing_mode=admin_billing.BillingMode.ALLOCATED_TRAFFIC.value,
        snapshot_plan_id=assignment.plan_id if assignment else None,
        snapshot_plan_version_id=assignment.version_id if assignment else None,
        snapshot_plan_name=plan.name if plan else None,
        snapshot_allocated_quota=int(version.data_limit or 0) if version else current_quota,
        snapshot_current_quota=current_quota,
        snapshot_used_traffic=used,
        snapshot_remaining_traffic=remaining,
        snapshot_user_created_at=user.created_at,
        snapshot_user_expire_at=_expire_datetime(user.expire),
        snapshot_pre_delete_status=str(user.status.value if hasattr(user.status, "value") else user.status),
        requested_refund_amount=requested_refund_amount,
        request_reason=request_reason,
        request_note=request_note,
        correlation_id=correlation_id,
        idempotency_key=idempotency_key,
        status="PENDING",
        requested_at=_now(),
    )
    db.add(row)
    try:
        db.flush()
        db.add(
            AllocatedTrafficRefundEvent(
                request_id=row.id,
                actor_admin_id=actor.id,
                from_status=None,
                to_status="PENDING",
                explanation=request_reason,
                operation_key=_operation_key("refund-request", idempotency_key),
                correlation_id=correlation_id,
                created_at=_now(),
            )
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        replay = db.query(AllocatedTrafficRefundRequest).filter(
            AllocatedTrafficRefundRequest.idempotency_key == idempotency_key
        ).one_or_none()
        if replay is not None:
            return replay, False
        raise
    db.refresh(row)
    return row, True


def decide_refund_request(
    db: Session,
    *,
    actor: Admin,
    request_id: int,
    decision: str,
    idempotency_key: str,
    explanation: str | None,
) -> tuple[AllocatedTrafficRefundRequest, bool]:
    operation_key = _operation_key(f"refund-{decision.lower()}", idempotency_key)
    prior_event = db.query(AllocatedTrafficRefundEvent).filter(
        AllocatedTrafficRefundEvent.operation_key == operation_key
    ).one_or_none()
    if prior_event is not None:
        if prior_event.request_id != request_id or prior_event.to_status != decision:
            raise admin_hierarchy.HierarchyError(
                "idempotency_conflict", "Idempotency key belongs to another refund decision"
            )
        return db.get(AllocatedTrafficRefundRequest, request_id), False
    row = db.query(AllocatedTrafficRefundRequest).filter(
        AllocatedTrafficRefundRequest.id == request_id
    ).with_for_update().one_or_none()
    if row is None:
        raise admin_hierarchy.HierarchyError("refund_request_not_found", "Refund request was not found")
    owner = admin_hierarchy.is_owner(db, actor)
    if decision in {"APPROVED", "REJECTED"}:
        if not owner and actor.id != row.reviewer_admin_id:
            raise admin_hierarchy.HierarchyError(
                "refund_decision_forbidden", "Only the authorized parent or Owner can decide"
            )
    elif decision == "CANCELLED":
        if actor.id != row.requester_admin_id and not owner:
            raise admin_hierarchy.HierarchyError(
                "refund_cancel_forbidden", "Only requester or Owner can cancel"
            )
    else:
        raise admin_hierarchy.HierarchyError("invalid_refund_status", "Unsupported refund decision")
    if row.status != "PENDING":
        raise admin_hierarchy.HierarchyError("refund_already_finalized", "Refund request is finalized")

    ledger = None
    if decision == "APPROVED":
        settings = db.query(MarzhelpAdminSettings).filter(
            MarzhelpAdminSettings.admin_id == row.account_admin_id
        ).with_for_update().one()
        if admin_billing.billing_mode(settings) != admin_billing.BillingMode.ALLOCATED_TRAFFIC:
            raise admin_hierarchy.HierarchyError(
                "refund_mode_changed", "Account is no longer in ALLOCATED_TRAFFIC mode"
            )
        before = int(settings.used_traffic or 0)
        if row.requested_refund_amount > before:
            raise admin_hierarchy.HierarchyError(
                "refund_exceeds_allocated_spend", "Refund exceeds current allocated spend"
            )
        after = before - row.requested_refund_amount
        settings.used_traffic = after
        ledger = AdminCreditTransfer(
            from_admin_id=None,
            to_admin_id=row.account_admin_id,
            actor_admin_id=actor.id,
            adjusted_admin_id=row.account_admin_id,
            resource="allocated_refund",
            amount=row.requested_refund_amount,
            delta=-row.requested_refund_amount,
            balance_before=before,
            balance_after=after,
            operation_type="allocated_refund",
            idempotency_key=operation_key,
            note=explanation,
        )
        db.add(ledger)
        db.flush()
        row.ledger_transfer_id = ledger.id
    row.status = decision
    row.decided_at = _now()
    row.decided_by_admin_id = actor.id
    row.decision_explanation = explanation
    db.add(
        AllocatedTrafficRefundEvent(
            request_id=row.id,
            actor_admin_id=actor.id,
            from_status="PENDING",
            to_status=decision,
            explanation=explanation,
            operation_key=operation_key,
            correlation_id=row.correlation_id,
            created_at=_now(),
        )
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        prior_event = db.query(AllocatedTrafficRefundEvent).filter(
            AllocatedTrafficRefundEvent.operation_key == operation_key
        ).one_or_none()
        if prior_event is not None and prior_event.request_id == request_id:
            return db.get(AllocatedTrafficRefundRequest, request_id), False
        raise
    db.refresh(row)
    return row, True


def refund_requests_query(db: Session, actor: Admin):
    query = db.query(AllocatedTrafficRefundRequest)
    if admin_hierarchy.is_owner(db, actor):
        return query
    return query.filter(
        or_(
            AllocatedTrafficRefundRequest.requester_admin_id == actor.id,
            AllocatedTrafficRefundRequest.reviewer_admin_id == actor.id,
            AllocatedTrafficRefundRequest.account_admin_id == actor.id,
        )
    )
