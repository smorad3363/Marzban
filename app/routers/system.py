from typing import Dict, List, Union

from fastapi import APIRouter, Depends, HTTPException, Request

from app import __version__, xray
from app.db import Session, crud, get_db
from app.db.models import MarzhelpMetadata
from app.models.admin import Admin
from app.models.proxy import ProxyHost, ProxyInbound, ProxyTypes
from app.models.system import SystemStats
from app.models.user import UserStatus
from app.utils import marzhelp_policy, responses
from app.utils.audit import AuditLogService
from app.utils.system import cpu_usage, memory_usage, realtime_bandwidth

router = APIRouter(tags=["System"], prefix="/api", responses={401: responses._401})


@router.get("/marzhelp/compatibility")
def get_marzhelp_compatibility(db: Session = Depends(get_db)):
    """Public installer preflight backed by the migrated database marker."""

    rows = db.query(MarzhelpMetadata).all()
    metadata = {row.key: row.value for row in rows}
    if metadata.get("source_id") != "smorad3363-marzban" or metadata.get("schema_version") != "1":
        raise HTTPException(status_code=409, detail="MarzHelp schema compatibility marker is missing")
    return {
        "compatible": True,
        "source_id": metadata["source_id"],
        "schema_version": int(metadata["schema_version"]),
        "minimum_marzhelp_version": metadata.get("minimum_marzhelp_version", "2"),
        "marzban_version": __version__,
    }


@router.get("/system", response_model=SystemStats)
def get_system_stats(
    db: Session = Depends(get_db), admin: Admin = Depends(Admin.get_current)
):
    """Fetch system stats including memory, CPU, and user metrics."""
    mem = memory_usage()
    cpu = cpu_usage()
    system = crud.get_system_usage(db)
    dbadmin: Union[Admin, None] = crud.get_admin(db, admin.username)
    effective_admin = dbadmin or admin
    allowed_inbounds = marzhelp_policy.allowed_inbound_tags(db, effective_admin)

    total_user = crud.get_users_count(
        db,
        admin=dbadmin if not admin.is_sudo else None,
        allowed_inbounds=allowed_inbounds,
    )
    users_active = crud.get_users_count(
        db, status=UserStatus.active, admin=dbadmin if not admin.is_sudo else None,
        allowed_inbounds=allowed_inbounds,
    )
    users_disabled = crud.get_users_count(
        db, status=UserStatus.disabled, admin=dbadmin if not admin.is_sudo else None,
        allowed_inbounds=allowed_inbounds,
    )
    users_on_hold = crud.get_users_count(
        db, status=UserStatus.on_hold, admin=dbadmin if not admin.is_sudo else None,
        allowed_inbounds=allowed_inbounds,
    )
    users_expired = crud.get_users_count(
        db, status=UserStatus.expired, admin=dbadmin if not admin.is_sudo else None,
        allowed_inbounds=allowed_inbounds,
    )
    users_limited = crud.get_users_count(
        db, status=UserStatus.limited, admin=dbadmin if not admin.is_sudo else None,
        allowed_inbounds=allowed_inbounds,
    )
    online_users = crud.count_online_users(
        db,
        24,
        admin=dbadmin if not admin.is_sudo else None,
        allowed_inbounds=allowed_inbounds,
    )
    realtime_bandwidth_stats = realtime_bandwidth()

    return SystemStats(
        version=__version__,
        mem_total=mem.total,
        mem_used=mem.used,
        cpu_cores=cpu.cores,
        cpu_usage=cpu.percent,
        total_user=total_user,
        online_users=online_users,
        users_active=users_active,
        users_disabled=users_disabled,
        users_expired=users_expired,
        users_limited=users_limited,
        users_on_hold=users_on_hold,
        incoming_bandwidth=system.uplink if admin.is_sudo else 0,
        outgoing_bandwidth=system.downlink if admin.is_sudo else 0,
        incoming_bandwidth_speed=realtime_bandwidth_stats.incoming_bytes if admin.is_sudo else 0,
        outgoing_bandwidth_speed=realtime_bandwidth_stats.outgoing_bytes if admin.is_sudo else 0,
    )


@router.get("/inbounds", response_model=Dict[ProxyTypes, List[ProxyInbound]])
def get_inbounds(
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
):
    """Retrieve inbound configurations grouped by protocol."""
    dbadmin = crud.get_admin(db, admin.username)
    allowed = marzhelp_policy.allowed_inbound_tags(db, dbadmin or admin)
    if allowed is None:
        return xray.config.inbounds_by_protocol
    return {
        protocol: [inbound for inbound in inbounds if inbound["tag"] in allowed]
        for protocol, inbounds in xray.config.inbounds_by_protocol.items()
        if any(inbound["tag"] in allowed for inbound in inbounds)
    }


@router.get(
    "/hosts", response_model=Dict[str, List[ProxyHost]], responses={403: responses._403}
)
def get_hosts(
    db: Session = Depends(get_db), admin: Admin = Depends(Admin.check_sudo_admin)
):
    """Get a list of proxy hosts grouped by inbound tag."""
    hosts = {tag: crud.get_hosts(db, tag) for tag in xray.config.inbounds_by_tag}
    return hosts


@router.put(
    "/hosts", response_model=Dict[str, List[ProxyHost]], responses={403: responses._403}
)
def modify_hosts(
    request: Request,
    modified_hosts: Dict[str, List[ProxyHost]],
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.check_sudo_admin),
):
    """Modify proxy hosts and update the configuration."""
    for inbound_tag in modified_hosts:
        if inbound_tag not in xray.config.inbounds_by_tag:
            raise HTTPException(
                status_code=400, detail=f"Inbound {inbound_tag} doesn't exist"
            )

    for inbound_tag, hosts in modified_hosts.items():
        crud.update_hosts(db, inbound_tag, hosts)

    xray.hosts.update()

    AuditLogService.log(
        db,
        admin,
        "settings.hosts_update",
        "proxy_hosts",
        f"Admin {admin.username} updated proxy hosts",
        details={
            "inbounds": {
                inbound_tag: len(hosts)
                for inbound_tag, hosts in modified_hosts.items()
            },
            "host_values_stored": False,
        },
        request=request,
    )

    return {tag: crud.get_hosts(db, tag) for tag in xray.config.inbounds_by_tag}
