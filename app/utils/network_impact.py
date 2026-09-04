"""Impact analysis for transactional proxy-host changes."""

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.db.models import (
    AdminUserPlan,
    AdminUserPlanHost,
    AdminUserPlanVersion,
    ProxyHost,
    User,
    UserPlanAssignment,
)
from app.models.proxy import HostUpdateImpact, ProxyHost as ProxyHostModify
from app.models.user import UserStatus


_HOST_FIELDS = (
    "remark", "address", "port", "path", "sni", "host", "security", "alpn",
    "fingerprint", "allowinsecure", "is_disabled", "mux_enable",
    "fragment_setting", "noise_setting", "random_user_agent", "use_sni_as_host",
)


def _changed(existing: ProxyHost, proposed: ProxyHostModify) -> bool:
    return any(getattr(existing, field) != getattr(proposed, field) for field in _HOST_FIELDS)


def analyze_host_update(
    db: Session,
    modified_hosts: dict[str, list[ProxyHostModify]],
) -> HostUpdateImpact:
    tags = sorted(modified_hosts)
    existing = (
        db.query(ProxyHost)
        .filter(ProxyHost.inbound_tag.in_(tags))
        .order_by(ProxyHost.inbound_tag, ProxyHost.id)
        .all()
        if tags
        else []
    )
    existing_by_id = {host.id: host for host in existing}
    proposed_ids = {
        host.id
        for hosts in modified_hosts.values()
        for host in hosts
        if host.id is not None
    }
    removed_ids = sorted(set(existing_by_id) - proposed_ids)
    changed_ids = sorted(
        host.id
        for hosts in modified_hosts.values()
        for host in hosts
        if host.id is not None
        and host.id in existing_by_id
        and _changed(existing_by_id[host.id], host)
    )
    affected_host_ids = sorted(set(removed_ids) | set(changed_ids))
    if not affected_host_ids:
        return HostUpdateImpact(
            affected_plan_count=0,
            affected_plan_version_count=0,
            active_user_count=0,
            affected_plan_ids=[],
            affected_version_ids=[],
            invalid_plan_ids=[],
            changed_host_ids=changed_ids,
            removed_host_ids=removed_ids,
        )

    version_rows = (
        db.query(AdminUserPlanHost.version_id)
        .filter(AdminUserPlanHost.host_id.in_(affected_host_ids))
        .distinct()
        .all()
    )
    version_ids = sorted(row[0] for row in version_rows)
    plan_rows = (
        db.query(AdminUserPlanVersion.plan_id)
        .filter(AdminUserPlanVersion.id.in_(version_ids))
        .distinct()
        .all()
        if version_ids
        else []
    )
    plan_ids = sorted(row[0] for row in plan_rows)

    latest_assignment = (
        db.query(
            UserPlanAssignment.user_id.label("user_id"),
            func.max(UserPlanAssignment.id).label("assignment_id"),
        )
        .group_by(UserPlanAssignment.user_id)
        .subquery()
    )
    active_user_count = (
        db.query(func.count(User.id))
        .join(latest_assignment, latest_assignment.c.user_id == User.id)
        .join(UserPlanAssignment, UserPlanAssignment.id == latest_assignment.c.assignment_id)
        .filter(
            User.status == UserStatus.active,
            UserPlanAssignment.version_id.in_(version_ids),
        )
        .scalar()
        or 0
        if version_ids
        else 0
    )

    unavailable_ids = set(removed_ids) | {
        host.id
        for hosts in modified_hosts.values()
        for host in hosts
        if host.id is not None and host.is_disabled
    }
    invalid_plan_ids = sorted(
        row[0]
        for row in (
            db.query(AdminUserPlan.id)
            .join(AdminUserPlanVersion, AdminUserPlan.current_version_id == AdminUserPlanVersion.id)
            .join(AdminUserPlanHost, AdminUserPlanHost.version_id == AdminUserPlanVersion.id)
            .filter(AdminUserPlan.id.in_(plan_ids))
            .group_by(AdminUserPlan.id, AdminUserPlanHost.inbound_tag)
            .having(func.sum(case(
                (AdminUserPlanHost.host_id.notin_(unavailable_ids), 1),
                else_=0,
            )) == 0)
            .all()
            if unavailable_ids
            else []
        )
    )
    return HostUpdateImpact(
        affected_plan_count=len(plan_ids),
        affected_plan_version_count=len(version_ids),
        active_user_count=int(active_user_count),
        affected_plan_ids=plan_ids,
        affected_version_ids=version_ids,
        invalid_plan_ids=invalid_plan_ids,
        changed_host_ids=changed_ids,
        removed_host_ids=removed_ids,
    )
