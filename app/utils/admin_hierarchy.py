"""Central role, hierarchy, scope, credit, and account-state services."""

from __future__ import annotations

import hashlib
import secrets
import time
from collections import Counter
from datetime import date, datetime, timezone
from typing import Iterable

from sqlalchemy import and_, exists, or_
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.db.models import (
    Admin,
    AdminAccountStatus,
    AdminApiToken,
    AdminBulkJob,
    AdminCreditTransfer,
    AdminHierarchy,
    AdminHierarchySettings,
    AdminRole,
    AdminSuspensionEvent,
    AdminSuspensionUser,
    MarzhelpAdminSettings,
    SystemOwner,
    User,
)
from app.models.user import UserStatus
from app.utils import marzhelp_policy


OWNER = "OWNER"
SUPER_ADMIN = "SUPER_ADMIN"
ADMIN = "ADMIN"
ROLE_IDS = {OWNER: 1, SUPER_ADMIN: 2, ADMIN: 3}

ACTIVE = "ACTIVE"
SUSPENDED = "SUSPENDED"
DISABLED = "DISABLED"
ACCOUNT_STATUS_IDS = {ACTIVE: 1, SUSPENDED: 2, DISABLED: 3}

FREE_FORM = "FREE_FORM"
PLAN_ONLY = "PLAN_ONLY"
USER_CREATION_MODE_IDS = {FREE_FORM: 1, PLAN_ONLY: 2}

ALLOWED_API_SCOPES = frozenset(
    {
        "account:read",
        "users:read",
        "users:write",
        "admins:read",
        "plans:read",
        "plans:write",
        "audit:read",
    }
)


def utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class HierarchyError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def hierarchy_settings(db: Session, *, lock: bool = False) -> AdminHierarchySettings | None:
    query = db.query(AdminHierarchySettings).filter(AdminHierarchySettings.id == 1)
    if lock:
        query = query.with_for_update()
    return query.one_or_none()


def hierarchy_enabled(db: Session) -> bool:
    settings = hierarchy_settings(db)
    return bool(settings and settings.enabled)


def owner_id(db: Session) -> int | None:
    return db.query(SystemOwner.admin_id).filter(SystemOwner.id == 1).scalar()


def role_code(admin: Admin | object) -> str:
    role = getattr(admin, "role", None)
    code = getattr(role, "code", None)
    if code:
        return str(code)
    role_id = getattr(admin, "role_id", None)
    for candidate, candidate_id in ROLE_IDS.items():
        if role_id == candidate_id:
            return candidate
    return OWNER if bool(getattr(admin, "is_sudo", False)) else ADMIN


def is_owner(db: Session, admin: Admin | object) -> bool:
    if not hierarchy_enabled(db):
        return bool(getattr(admin, "is_sudo", False))
    return role_code(admin) == OWNER and getattr(admin, "id", None) == owner_id(db)


def can_manage_children(db: Session, admin: Admin | object) -> bool:
    if not hierarchy_enabled(db):
        return bool(getattr(admin, "is_sudo", False))
    return role_code(admin) in {OWNER, SUPER_ADMIN}


def account_status_code(db: Session, admin_id: int) -> str:
    value = (
        db.query(AdminAccountStatus.code)
        .join(MarzhelpAdminSettings, MarzhelpAdminSettings.account_status_id == AdminAccountStatus.id)
        .filter(MarzhelpAdminSettings.admin_id == admin_id)
        .scalar()
    )
    return str(value or ACTIVE)


def require_active_account(db: Session, admin: Admin | object) -> None:
    admin_id = getattr(admin, "id", None)
    if admin_id is None or not hierarchy_enabled(db):
        return
    state = account_status_code(db, int(admin_id))
    if state != ACTIVE:
        raise HierarchyError("account_read_only", f"Administrative account is {state.lower()}")


def admin_in_scope(db: Session, actor: Admin | object, target_admin_id: int) -> bool:
    actor_id = getattr(actor, "id", None)
    if actor_id is None:
        return bool(getattr(actor, "is_sudo", False)) and not hierarchy_enabled(db)
    if is_owner(db, actor):
        return True
    if not hierarchy_enabled(db):
        return int(actor_id) == int(target_admin_id)
    return bool(
        db.query(AdminHierarchy.ancestor_id)
        .filter(
            AdminHierarchy.ancestor_id == int(actor_id),
            AdminHierarchy.descendant_id == int(target_admin_id),
        )
        .first()
    )


def can_access_user(db: Session, actor: Admin | object, user: User) -> bool:
    if user.admin_id is None or not admin_in_scope(db, actor, user.admin_id):
        return False
    if is_owner(db, actor):
        return True
    allowed = marzhelp_policy.allowed_inbound_tags(db, actor)
    return allowed is None or marzhelp_policy.user_inbound_tags(user).issubset(allowed)


def scope_admin_column(query, db: Session, actor: Admin | object, column):
    """Apply subtree scope in SQL; never materialize an unbounded Python ID list."""

    actor_id = getattr(actor, "id", None)
    if is_owner(db, actor):
        return query
    if actor_id is None or not hierarchy_enabled(db):
        return query.filter(column == actor_id)
    scoped = exists().where(
        and_(
            AdminHierarchy.ancestor_id == int(actor_id),
            AdminHierarchy.descendant_id == column,
        )
    )
    return query.filter(scoped)


def subtree_admin_ids_query(db: Session, root_admin_id: int):
    return db.query(AdminHierarchy.descendant_id).filter(
        AdminHierarchy.ancestor_id == root_admin_id
    )


def _parent_cycle_nodes(admins: Iterable[Admin]) -> set[int]:
    parent_by_id = {item.id: item.parent_admin_id for item in admins}
    cycle_nodes: set[int] = set()
    for start in parent_by_id:
        seen: dict[int, int] = {}
        current = start
        while current in parent_by_id and parent_by_id[current] is not None:
            if current in seen:
                cycle_nodes.update(list(seen)[seen[current] :])
                break
            seen[current] = len(seen)
            current = parent_by_id[current]
    return cycle_nodes


def _rebuild_closure(db: Session, admins: list[Admin], max_depth: int) -> int:
    by_id = {item.id: item for item in admins}
    rows: list[AdminHierarchy] = []
    for descendant in admins:
        rows.append(AdminHierarchy(ancestor_id=descendant.id, descendant_id=descendant.id, depth=0))
        current = descendant
        visited = {descendant.id}
        depth = 0
        while current.parent_admin_id is not None:
            depth += 1
            if depth > max_depth:
                raise HierarchyError("max_depth_exceeded", f"Hierarchy exceeds maximum depth {max_depth}")
            parent_id = int(current.parent_admin_id)
            if parent_id in visited or parent_id not in by_id:
                raise HierarchyError("closure_invalid_parent", "Hierarchy contains a cycle or missing parent")
            visited.add(parent_id)
            rows.append(
                AdminHierarchy(
                    ancestor_id=parent_id,
                    descendant_id=descendant.id,
                    depth=depth,
                )
            )
            current = by_id[parent_id]
    db.query(AdminHierarchy).delete(synchronize_session=False)
    db.add_all(rows)
    db.flush()
    return len(rows)


def set_owner(db: Session, username: str) -> dict:
    """Atomically select Owner, repair legacy parentage, and enable hierarchy."""

    try:
        settings = hierarchy_settings(db, lock=True)
        if settings is None:
            raise HierarchyError("schema_not_ready", "Admin hierarchy migration is not installed")
        admins = db.query(Admin).order_by(Admin.id).with_for_update().all()
        selected = next((item for item in admins if item.username == username), None)
        if selected is None:
            raise HierarchyError("admin_not_found", f"Admin {username!r} does not exist")

        original_sudo = {item.id: bool(item.is_sudo) for item in admins}
        role_by_id = {item.id: role_code(item) for item in admins}
        reason_counts: Counter[str] = Counter()
        cycle_nodes = _parent_cycle_nodes(admins)
        valid_ids = {item.id for item in admins}

        selected.role_id = ROLE_IDS[OWNER]
        selected.parent_admin_id = None
        selected.is_sudo = True

        for item in admins:
            if item.id == selected.id:
                continue
            if original_sudo[item.id] or role_by_id[item.id] in {OWNER, SUPER_ADMIN}:
                item.role_id = ROLE_IDS[SUPER_ADMIN]
            else:
                item.role_id = ROLE_IDS[ADMIN]
            item.is_sudo = False
            item.external_api_enabled = False

            parent_id = item.parent_admin_id
            if item.id in cycle_nodes:
                item.parent_admin_id = selected.id
                reason_counts["cycle_broken_attached_to_owner"] += 1
            elif parent_id == item.id:
                item.parent_admin_id = selected.id
                reason_counts["self_parent_attached_to_owner"] += 1
            elif parent_id is not None and parent_id not in valid_ids:
                item.parent_admin_id = selected.id
                reason_counts["missing_parent_attached_to_owner"] += 1
            elif parent_id is None or parent_id == selected.id:
                item.parent_admin_id = selected.id
                reason_counts[
                    "legacy_sudo_attached_to_owner"
                    if original_sudo[item.id]
                    else "legacy_admin_missing_parent_attached_to_owner"
                ] += 1
            else:
                reason_counts["existing_valid_parent_preserved"] += 1

        # A node with children must be able to manage them.
        parent_ids = {item.parent_admin_id for item in admins if item.parent_admin_id is not None}
        for item in admins:
            if item.id in parent_ids and item.id != selected.id and item.role_id == ROLE_IDS[ADMIN]:
                item.role_id = ROLE_IDS[SUPER_ADMIN]

        db.flush()
        closure_rows = _rebuild_closure(db, admins, int(settings.max_depth or 64))

        owner_row = db.query(SystemOwner).filter(SystemOwner.id == 1).with_for_update().one_or_none()
        if owner_row is None:
            owner_row = SystemOwner(id=1, admin_id=selected.id, assigned_at=utc_now_naive())
            db.add(owner_row)
        else:
            owner_row.admin_id = selected.id
            owner_row.assigned_at = utc_now_naive()

        null_users = db.query(User).filter(User.admin_id.is_(None)).update(
            {User.admin_id: selected.id}, synchronize_session=False
        )
        reason_counts["null_user_owner_attached_to_owner"] += int(null_users or 0)

        existing_settings = {
            row.admin_id: row
            for row in db.query(MarzhelpAdminSettings)
            .filter(MarzhelpAdminSettings.admin_id.in_(valid_ids))
            .with_for_update()
            .all()
        }
        for item in admins:
            policy = existing_settings.get(item.id)
            if policy is None:
                policy = MarzhelpAdminSettings(
                    admin_id=item.id,
                    calculate_volume="created_traffic",
                    renewal_enabled=True,
                    user_creation_mode_id=USER_CREATION_MODE_IDS[FREE_FORM],
                    account_status_id=ACCOUNT_STATUS_IDS[ACTIVE],
                )
                db.add(policy)
            else:
                # Compatibility conversion happens only at the explicit cutover.
                # Legacy zero meant unlimited; canonical hierarchy uses NULL for it.
                if policy.total_traffic is not None and int(policy.total_traffic) <= 0:
                    policy.total_traffic = None
                policy.used_traffic = max(
                    int(policy.used_traffic or 0),
                    marzhelp_policy.allocated_credit_baseline(db, item.id),
                )
                policy.calculate_volume = "created_traffic"

            if item.id == selected.id:
                policy.total_traffic = None

        settings.enabled = True
        settings.updated_at = utc_now_naive()
        db.flush()

        owner_count = db.query(SystemOwner).count()
        orphan_count = db.query(Admin).filter(
            Admin.id != selected.id,
            or_(Admin.parent_admin_id.is_(None), ~Admin.parent_admin_id.in_(valid_ids)),
        ).count()
        if owner_count != 1 or orphan_count:
            raise HierarchyError("backfill_verification_failed", "Owner/parent invariants failed")

        db.commit()
        return {
            "owner": selected.username,
            "owner_id": selected.id,
            "admin_count": len(admins),
            "closure_rows": closure_rows,
            "reason_counts": dict(sorted(reason_counts.items())),
        }
    except Exception:
        db.rollback()
        raise


def reparent_subtree(db: Session, actor: Admin, target: Admin, new_parent: Admin) -> None:
    if not is_owner(db, actor):
        raise HierarchyError("owner_required", "Only Owner can reparent a subtree")
    if target.id == actor.id or target.id == new_parent.id:
        raise HierarchyError("invalid_parent", "Owner/self reparent is not allowed")
    if role_code(new_parent) == ADMIN:
        raise HierarchyError("invalid_parent_role", "An Admin cannot have child administrators")
    if db.query(AdminHierarchy).filter(
        AdminHierarchy.ancestor_id == target.id,
        AdminHierarchy.descendant_id == new_parent.id,
    ).first():
        raise HierarchyError("cycle_detected", "The new parent is inside the target subtree")
    admins = db.query(Admin).order_by(Admin.id).with_for_update().all()
    target.parent_admin_id = new_parent.id
    settings = hierarchy_settings(db, lock=True)
    _rebuild_closure(db, admins, int(settings.max_depth if settings else 64))
    db.commit()


def attach_new_child(
    db: Session,
    *,
    actor: Admin,
    parent: Admin,
    child: Admin,
    child_role: str,
    commit: bool = True,
) -> None:
    if not can_manage_children(db, actor) or not admin_in_scope(db, actor, parent.id):
        raise HierarchyError("admin_create_forbidden", "Parent administrator is outside actor scope")
    if role_code(parent) == ADMIN:
        raise HierarchyError("invalid_parent_role", "An Admin cannot have child administrators")
    if child_role not in {SUPER_ADMIN, ADMIN}:
        raise HierarchyError("invalid_role", "Only Super Admin or Admin children can be created")
    child.role_id = ROLE_IDS[child_role]
    child.parent_admin_id = parent.id
    child.is_sudo = False
    child.external_api_enabled = False
    policy = db.get(MarzhelpAdminSettings, child.id)
    if policy is not None:
        policy.renewal_enabled = True
        policy.user_creation_mode_id = USER_CREATION_MODE_IDS[FREE_FORM]
        policy.account_status_id = ACCOUNT_STATUS_IDS[ACTIVE]
    admins = db.query(Admin).order_by(Admin.id).with_for_update().all()
    settings = hierarchy_settings(db, lock=True)
    _rebuild_closure(db, admins, int(settings.max_depth if settings else 64))
    if commit:
        db.commit()
    else:
        db.flush()


def own_credit_spend(db: Session, settings: MarzhelpAdminSettings) -> int:
    if (settings.calculate_volume or "used_traffic") == "created_traffic":
        return int(settings.used_traffic or 0)
    return marzhelp_policy.used_traffic_spend(db, settings.admin_id)


def available_credit(db: Session, settings: MarzhelpAdminSettings) -> int | None:
    if settings.total_traffic is None:
        return None
    admin = db.get(Admin, settings.admin_id)
    if admin is not None and is_owner(db, admin):
        return None
    return max(
        int(settings.total_traffic or 0)
        - own_credit_spend(db, settings)
        - int(settings.delegated_traffic or 0),
        0,
    )


def automatic_suspension_reason(
    db: Session,
    settings: MarzhelpAdminSettings,
    *,
    today: date | None = None,
) -> int | None:
    if settings.expiry_date is not None and settings.expiry_date < (today or date.today()):
        return 3
    if settings.total_traffic is not None and available_credit(db, settings) <= 0:
        return 2
    return None


def transfer_credit(
    db: Session,
    *,
    actor: Admin,
    source: Admin,
    target: Admin,
    amount: int,
    operation_type: str,
    idempotency_key: str,
    note: str | None = None,
) -> AdminCreditTransfer:
    if amount <= 0:
        raise HierarchyError("invalid_amount", "Credit amount must be positive")
    if operation_type not in {"grant", "reclaim", "owner_adjustment", "migration"}:
        raise HierarchyError("invalid_operation", "Unsupported credit operation")
    if not idempotency_key or len(idempotency_key) > 128:
        raise HierarchyError("invalid_idempotency_key", "A bounded idempotency key is required")
    if not is_owner(db, actor) and actor.id != source.id:
        raise HierarchyError("credit_scope_forbidden", "Only source admin or Owner can transfer credit")
    if operation_type in {"grant", "reclaim"} and target.parent_admin_id != source.id:
        raise HierarchyError("direct_child_required", "Credit moves only between a parent and direct child")

    ledger_from_id = target.id if operation_type == "reclaim" else source.id
    ledger_to_id = source.id if operation_type == "reclaim" else target.id

    for attempt in range(3):
        try:
            existing = db.query(AdminCreditTransfer).filter(
                AdminCreditTransfer.idempotency_key == idempotency_key
            ).one_or_none()
            if existing is not None:
                if (
                    existing.from_admin_id != ledger_from_id
                    or existing.to_admin_id != ledger_to_id
                    or existing.actor_admin_id != actor.id
                    or int(existing.amount) != amount
                    or existing.operation_type != operation_type
                ):
                    raise HierarchyError(
                        "idempotency_conflict",
                        "Idempotency key belongs to another credit operation",
                    )
                return existing

            ids = sorted({source.id, target.id})
            wallets = {
                item.admin_id: item
                for item in db.query(MarzhelpAdminSettings)
                .filter(MarzhelpAdminSettings.admin_id.in_(ids))
                .order_by(MarzhelpAdminSettings.admin_id)
                .with_for_update()
                .all()
            }
            if set(wallets) != set(ids):
                raise HierarchyError("wallet_missing", "Both administrators need credit settings")
            source_wallet = wallets[source.id]
            target_wallet = wallets[target.id]

            if operation_type == "reclaim":
                reclaimable = available_credit(db, target_wallet)
                if reclaimable is not None and amount > reclaimable:
                    raise HierarchyError("reclaim_exceeds_available", "Reclaim exceeds child available credit")
                target_wallet.total_traffic = int(target_wallet.total_traffic or 0) - amount
                source_wallet.delegated_traffic = max(int(source_wallet.delegated_traffic or 0) - amount, 0)
            else:
                available = available_credit(db, source_wallet)
                if available is not None and amount > available:
                    raise HierarchyError("credit_exhausted", "Parent has insufficient delegatable credit")
                source_wallet.delegated_traffic = int(source_wallet.delegated_traffic or 0) + amount
                target_wallet.total_traffic = int(target_wallet.total_traffic or 0) + amount

            transfer = AdminCreditTransfer(
                from_admin_id=ledger_from_id,
                to_admin_id=ledger_to_id,
                actor_admin_id=actor.id,
                amount=amount,
                operation_type=operation_type,
                idempotency_key=idempotency_key,
                note=note,
            )
            db.add(transfer)
            db.commit()
            db.refresh(transfer)
            return transfer
        except OperationalError as exc:
            db.rollback()
            mysql_code = getattr(getattr(exc, "orig", None), "args", [None])[0]
            if mysql_code != 1213 or attempt == 2:
                raise
            time.sleep(0.02 * (attempt + 1))
        except IntegrityError:
            db.rollback()
            existing = db.query(AdminCreditTransfer).filter(
                AdminCreditTransfer.idempotency_key == idempotency_key
            ).one_or_none()
            if existing is not None:
                return existing
            raise
    raise AssertionError("unreachable")


def issue_api_token(
    db: Session,
    *,
    owner: Admin,
    target: Admin,
    name: str,
    scopes: set[str],
    expires_at: datetime,
) -> tuple[AdminApiToken, str]:
    if not is_owner(db, owner):
        raise HierarchyError("owner_required", "Only Owner can issue automation tokens")
    invalid = scopes - ALLOWED_API_SCOPES
    if invalid or not scopes:
        raise HierarchyError("invalid_scopes", f"Invalid API scopes: {sorted(invalid)}")
    if expires_at.tzinfo is not None:
        expires_at = expires_at.astimezone(timezone.utc).replace(tzinfo=None)
    if expires_at <= utc_now_naive():
        raise HierarchyError("invalid_expiry", "Token expiry must be in the future")
    if not target.external_api_enabled:
        raise HierarchyError("external_api_disabled", "External API is disabled for this admin")
    plaintext = "mzapi_" + secrets.token_urlsafe(36)
    row = AdminApiToken(
        admin_id=target.id,
        token_hash=hashlib.sha256(plaintext.encode()).digest(),
        name=name.strip(),
        scopes=sorted(scopes),
        expires_at=expires_at,
        created_by_admin_id=owner.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row, plaintext


def authenticate_api_token(db: Session, plaintext: str) -> tuple[Admin, set[str]] | None:
    if not plaintext.startswith("mzapi_"):
        return None
    digest = hashlib.sha256(plaintext.encode()).digest()
    now = utc_now_naive()
    row = (
        db.query(AdminApiToken)
        .join(Admin, Admin.id == AdminApiToken.admin_id)
        .filter(
            AdminApiToken.token_hash == digest,
            AdminApiToken.revoked_at.is_(None),
            AdminApiToken.expires_at > now,
            Admin.external_api_enabled.is_(True),
        )
        .one_or_none()
    )
    if row is None:
        return None
    row.last_used_at = now
    db.commit()
    return db.get(Admin, row.admin_id), set(row.scopes or [])


def revoke_api_access(db: Session, owner: Admin, target: Admin) -> int:
    if not is_owner(db, owner):
        raise HierarchyError("owner_required", "Only Owner can revoke external API access")
    now = utc_now_naive()
    target.external_api_enabled = False
    target.external_api_updated_by = owner.id
    target.external_api_updated_at = now
    count = db.query(AdminApiToken).filter(
        AdminApiToken.admin_id == target.id,
        AdminApiToken.revoked_at.is_(None),
    ).update({AdminApiToken.revoked_at: now}, synchronize_session=False)
    db.commit()
    return int(count or 0)


def _target_user_query(db: Session, target_admin_id: int, include_subtree: bool):
    query = db.query(User)
    if include_subtree:
        query = query.filter(
            exists().where(
                and_(
                    AdminHierarchy.ancestor_id == target_admin_id,
                    AdminHierarchy.descendant_id == User.admin_id,
                )
            )
        )
    else:
        query = query.filter(User.admin_id == target_admin_id)
    return query


def suspend_admin(
    db: Session,
    *,
    actor: Admin,
    target: Admin,
    reason_id: int = 1,
    include_subtree: bool = True,
    batch_size: int = 500,
) -> AdminSuspensionEvent:
    if not admin_in_scope(db, actor, target.id) or actor.id == target.id:
        raise HierarchyError("suspension_scope_forbidden", "Target admin is outside actor scope")
    event = AdminSuspensionEvent(
        admin_id=target.id,
        actor_admin_id=actor.id,
        reason_id=reason_id,
        status="processing",
    )
    db.add(event)
    db.flush()
    last_id = 0
    while True:
        batch = (
            _target_user_query(db, target.id, include_subtree)
            .filter(
                User.id > last_id,
                User.status.in_((UserStatus.active, UserStatus.on_hold)),
            )
            .order_by(User.id)
            .limit(max(1, min(batch_size, 2000)))
            .with_for_update()
            .all()
        )
        if not batch:
            break
        for user in batch:
            db.add(
                AdminSuspensionUser(
                    event_id=event.id,
                    user_id=user.id,
                    previous_status=user.status.value,
                    applied_status=UserStatus.disabled.value,
                    sync_status="applied",
                )
            )
            user.status = UserStatus.disabled
            last_id = user.id
        db.flush()

    settings_query = db.query(MarzhelpAdminSettings)
    if include_subtree:
        settings_query = settings_query.filter(
            MarzhelpAdminSettings.admin_id.in_(subtree_admin_ids_query(db, target.id))
        )
    else:
        settings_query = settings_query.filter(MarzhelpAdminSettings.admin_id == target.id)
    settings_query.update(
        {
            MarzhelpAdminSettings.account_status_id: ACCOUNT_STATUS_IDS[SUSPENDED],
            MarzhelpAdminSettings.suspended_reason_id: reason_id,
            MarzhelpAdminSettings.suspended_at: utc_now_naive(),
            MarzhelpAdminSettings.suspended_by_admin_id: actor.id,
            MarzhelpAdminSettings.suspension_event_id: event.id,
        },
        synchronize_session=False,
    )
    event.status = "complete"
    db.commit()
    db.refresh(event)
    return event


def resume_admin(db: Session, *, actor: Admin, target: Admin) -> int:
    if not admin_in_scope(db, actor, target.id) or actor.id == target.id:
        raise HierarchyError("resume_scope_forbidden", "Target admin is outside actor scope")
    settings = db.get(MarzhelpAdminSettings, target.id)
    if settings is None or settings.suspension_event_id is None:
        raise HierarchyError("no_active_suspension", "Admin has no resumable suspension event")
    event_id = int(settings.suspension_event_id)
    rows = (
        db.query(AdminSuspensionUser, User)
        .join(User, User.id == AdminSuspensionUser.user_id)
        .filter(
            AdminSuspensionUser.event_id == event_id,
            AdminSuspensionUser.sync_status == "applied",
        )
        .order_by(User.id)
        .with_for_update()
        .all()
    )
    restored = 0
    for snapshot, user in rows:
        if user.status == UserStatus.disabled:
            user.status = UserStatus(snapshot.previous_status)
            restored += 1
        snapshot.sync_status = "restored"
    subtree_settings = db.query(MarzhelpAdminSettings).filter(
        MarzhelpAdminSettings.suspension_event_id == event_id
    )
    subtree_settings.update(
        {
            MarzhelpAdminSettings.account_status_id: ACCOUNT_STATUS_IDS[ACTIVE],
            MarzhelpAdminSettings.suspended_reason_id: None,
            MarzhelpAdminSettings.suspended_at: None,
            MarzhelpAdminSettings.suspended_by_admin_id: None,
            MarzhelpAdminSettings.suspension_event_id: None,
        },
        synchronize_session=False,
    )
    event = db.get(AdminSuspensionEvent, event_id)
    if event:
        event.status = "resolved"
        event.resolved_at = utc_now_naive()
    db.commit()
    return restored


def run_disable_job(
    db: Session,
    *,
    actor: Admin,
    target: Admin,
    include_subtree: bool,
    idempotency_key: str,
    batch_size: int = 500,
) -> AdminBulkJob:
    existing = db.query(AdminBulkJob).filter(
        AdminBulkJob.idempotency_key == idempotency_key
    ).one_or_none()
    if existing and existing.status == "complete":
        return existing
    if existing and (
        existing.actor_admin_id != actor.id
        or existing.target_admin_id != target.id
        or bool(existing.include_subtree) != bool(include_subtree)
    ):
        raise HierarchyError("idempotency_conflict", "Idempotency key belongs to another bulk job")
    if not admin_in_scope(db, actor, target.id):
        raise HierarchyError("bulk_scope_forbidden", "Target is outside actor scope")
    query = _target_user_query(db, target.id, include_subtree).filter(
        User.status.in_((UserStatus.active, UserStatus.on_hold))
    )
    if existing is None:
        job = AdminBulkJob(
            actor_admin_id=actor.id,
            target_admin_id=target.id,
            operation="disable",
            include_subtree=include_subtree,
            status="processing",
            total_count=query.count(),
            idempotency_key=idempotency_key,
        )
        db.add(job)
        db.commit()
        db.refresh(job)
    else:
        job = existing
    last_id = int(job.last_user_id or 0)
    while True:
        ids = [
            row[0]
            for row in query.with_entities(User.id)
            .filter(User.id > last_id)
            .order_by(User.id)
            .limit(max(1, min(batch_size, 2000)))
            .all()
        ]
        if not ids:
            break
        db.query(User).filter(User.id.in_(ids)).update(
            {User.status: UserStatus.disabled}, synchronize_session=False
        )
        last_id = ids[-1]
        job.last_user_id = last_id
        job.processed_count = int(job.processed_count or 0) + len(ids)
        db.commit()
    job.status = "complete"
    db.commit()
    db.refresh(job)
    return job
