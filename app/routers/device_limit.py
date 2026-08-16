from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from app import xray
from app.db import Session, crud, get_db
from app.db.models import (
    DeviceLimitIncident,
    DeviceLimitPenaltyStage,
    DeviceLimitSettings,
    DeviceLimitUserState,
    DeviceSlot,
    MarzhelpAdminSettings,
    User,
)
from app.dependencies import get_validated_user
from app.device_limit.constants import DeviceEventState, PenaltyStatus
from app.device_limit.engine import engine, mask_ip
from app.device_limit.slots import slot_subscription_url, sync_device_slots
from app.models.admin import Admin
from app.models.device_limit import (
    DeviceLimitIncidentList,
    DeviceLimitIncidentResponse,
    DeviceLimitPenaltyStageResponse,
    DeviceLimitPenaltyStagesUpdate,
    DeviceLimitSettingsResponse,
    DeviceLimitSettingsUpdate,
    DeviceLimitStateResponse,
    DeviceLimitUserSummary,
    DeviceClientObservationResponse,
    DeviceSlotModify,
    DeviceSlotResponse,
)
from app.models.user import UserStatus
from app.utils.audit import AuditLogService


router = APIRouter(tags=["Device Limit"], prefix="/api/device-limit")


def _settings(db: Session) -> DeviceLimitSettings:
    settings = db.get(DeviceLimitSettings, 1)
    if settings is None:
        settings = DeviceLimitSettings(id=1)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


def _can_view_full_ip(db: Session, admin: Admin) -> bool:
    if admin.is_sudo:
        return True
    dbadmin = crud.get_admin(db, admin.username)
    settings = db.get(MarzhelpAdminSettings, dbadmin.id) if dbadmin else None
    return bool(settings and settings.view_full_client_ip)


def _slot_response(username: str, slot: DeviceSlot, full_ip: bool) -> DeviceSlotResponse:
    observations = []
    for item in sorted(
        slot.client_observations,
        key=lambda observation: observation.last_seen_at,
        reverse=True,
    )[:10]:
        response = DeviceClientObservationResponse.model_validate(item)
        if not full_ip:
            response = response.model_copy(update={"raw_user_agent": None})
        observations.append(response)
    return DeviceSlotResponse(
        id=slot.id,
        slot_index=slot.slot_index,
        label=slot.label,
        enabled=slot.enabled,
        last_seen_at=slot.last_seen_at,
        last_ip=(slot.last_ip if full_ip or not slot.last_ip else mask_ip(slot.last_ip)),
        subscription_url=slot_subscription_url(username, slot),
        created_at=slot.created_at,
        client_observations=observations,
    )


@router.get("/settings", response_model=DeviceLimitSettingsResponse)
def get_settings(
    db: Session = Depends(get_db),
    _: Admin = Depends(Admin.check_sudo_admin),
):
    return _settings(db)


@router.put("/settings", response_model=DeviceLimitSettingsResponse)
def update_settings(
    values: DeviceLimitSettingsUpdate,
    request: Request,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.check_sudo_admin),
):
    settings = _settings(db)
    was_enabled = settings.enabled
    previous = DeviceLimitSettingsResponse.model_validate(settings).model_dump()
    update_values = values.model_dump(exclude_none=True)
    update_values["hit_threshold"] = values.min_successful_connections
    update_values["enforcement_mode"] = (
        "hybrid"
        if values.device_slots_enabled and values.ip_detection_enabled
        else "ip"
        if values.ip_detection_enabled
        else "slots"
    )
    slots_changed = settings.device_slots_enabled != values.device_slots_enabled
    for key, value in update_values.items():
        setattr(settings, key, value)
    if slots_changed:
        for chunk_start in range(0, db.query(User.id).count(), 500):
            users = (
                db.query(User)
                .filter(User.concurrent_user_limit.is_not(None))
                .order_by(User.id)
                .offset(chunk_start)
                .limit(500)
                .all()
            )
            for dbuser in users:
                sync_device_slots(db, dbuser)
    db.commit()
    db.refresh(settings)
    engine.configure(
        settings.enabled,
        settings.enforcement_mode,
        settings.ip_detection_enabled,
    )
    AuditLogService.log(
        db,
        admin,
        "device_limit.settings_update",
        "device_limit_settings",
        f"Admin {admin.username} updated native device-limit settings",
        target_id=1,
        previous_value=previous,
        new_value=DeviceLimitSettingsResponse.model_validate(settings).model_dump(),
        request=request,
    )
    if not settings.enabled:
        engine.release_all_temporary_penalties()
    elif not was_enabled:
        # Enabling requires Xray's info-level accepted logs. Apply the generated
        # configuration once to the main core and connected nodes.
        startup_config = xray.config.include_db_users()
        if xray.core.started:
            xray.core.restart(startup_config)
        for node_id, node in list(xray.nodes.items()):
            if node.connected:
                xray.operations.restart_node(node_id, startup_config)
    return settings


@router.get("/penalty-stages", response_model=list[DeviceLimitPenaltyStageResponse])
def get_penalty_stages(
    db: Session = Depends(get_db),
    _: Admin = Depends(Admin.check_sudo_admin),
):
    return db.query(DeviceLimitPenaltyStage).order_by(
        DeviceLimitPenaltyStage.violation_count.asc()
    ).all()


@router.put("/penalty-stages", response_model=list[DeviceLimitPenaltyStageResponse])
def update_penalty_stages(
    values: DeviceLimitPenaltyStagesUpdate,
    request: Request,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.check_sudo_admin),
):
    previous = [
        DeviceLimitPenaltyStageResponse.model_validate(stage).model_dump()
        for stage in db.query(DeviceLimitPenaltyStage).all()
    ]
    db.query(DeviceLimitPenaltyStage).delete(synchronize_session=False)
    db.add_all(
        DeviceLimitPenaltyStage(**stage.model_dump())
        for stage in sorted(values.stages, key=lambda item: item.violation_count)
    )
    db.commit()
    stages = db.query(DeviceLimitPenaltyStage).order_by(
        DeviceLimitPenaltyStage.violation_count.asc()
    ).all()
    AuditLogService.log(
        db,
        admin,
        "device_limit.penalties_update",
        "device_limit_penalty_stages",
        f"Admin {admin.username} updated device-limit penalty stages",
        previous_value=previous,
        new_value=[DeviceLimitPenaltyStageResponse.model_validate(stage).model_dump() for stage in stages],
        request=request,
    )
    return stages


@router.get("/incidents", response_model=DeviceLimitIncidentList)
def list_incidents(
    offset: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=100),
    username: str | None = None,
    unresolved_only: bool = False,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
):
    query = db.query(DeviceLimitIncident)
    if not admin.is_sudo:
        dbadmin = crud.get_admin(db, admin.username)
        if dbadmin is None:
            return DeviceLimitIncidentList(incidents=[], total=0, offset=offset, limit=limit)
        query = query.filter(DeviceLimitIncident.admin_id == dbadmin.id)
    if username:
        query = query.filter(DeviceLimitIncident.username.ilike(f"%{username.strip()}%"))
    if unresolved_only:
        query = query.filter(DeviceLimitIncident.resolved_at.is_(None))
    total = query.count()
    incidents = query.order_by(
        DeviceLimitIncident.created_at.desc(), DeviceLimitIncident.id.desc()
    ).offset(offset).limit(limit).all()
    full_ip = _can_view_full_ip(db, admin)
    incident_responses = []
    for incident in incidents:
        response = DeviceLimitIncidentResponse.model_validate(incident)
        if not full_ip and response.ip_addresses:
            response = response.model_copy(
                update={
                    "ip_addresses": [mask_ip(value) for value in response.ip_addresses]
                }
            )
        incident_responses.append(response)
    return DeviceLimitIncidentList(
        incidents=incident_responses,
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/users/{username}", response_model=DeviceLimitUserSummary)
def user_summary(
    dbuser=Depends(get_validated_user),
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
):
    settings = _settings(db)
    addresses, sources, _ = engine.live_snapshot(
        dbuser.id,
        settings.active_window_seconds,
        settings.min_successful_connections,
    )
    full_ip = _can_view_full_ip(db, admin)
    state = db.get(DeviceLimitUserState, dbuser.id)
    state_response = (
        DeviceLimitStateResponse.model_validate(state)
        if state
        else DeviceLimitStateResponse()
    )
    return DeviceLimitUserSummary(
        username=dbuser.username,
        configured_limit=dbuser.concurrent_user_limit,
        enabled=settings.enabled and dbuser.concurrent_user_limit is not None,
        live_active_ip_count=len(addresses),
        live_ip_addresses=sorted(addresses if full_ip else {mask_ip(value) for value in addresses}),
        live_source_nodes=sorted(sources),
        state=state_response,
        slots=[
            _slot_response(dbuser.username, slot, full_ip)
            for slot in sorted(dbuser.device_slots, key=lambda item: item.slot_index)
            if slot.enabled
        ],
        user_client_observations=[
            DeviceClientObservationResponse.model_validate(item).model_copy(
                update={} if full_ip else {"raw_user_agent": None}
            )
            for item in sorted(
                (
                    observation
                    for observation in dbuser.device_client_observations
                    if observation.slot_key == 0
                ),
                key=lambda observation: observation.last_seen_at,
                reverse=True,
            )[:10]
        ],
    )


@router.put("/users/{username}/slots/{slot_index}", response_model=DeviceSlotResponse)
def modify_slot(
    slot_index: int,
    values: DeviceSlotModify,
    request: Request,
    dbuser=Depends(get_validated_user),
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
):
    slot = (
        db.query(DeviceSlot)
        .filter(DeviceSlot.user_id == dbuser.id, DeviceSlot.slot_index == slot_index)
        .first()
    )
    if slot is None:
        raise HTTPException(status_code=404, detail="Device slot not found")
    previous_label = slot.label
    slot.label = values.label.strip() if values.label else None
    db.commit()
    db.refresh(slot)
    AuditLogService.log(
        db,
        admin,
        "device_limit.slot_update",
        "device_slot",
        f"Admin {admin.username} renamed device slot {slot_index} for {dbuser.username}",
        target_id=slot.id,
        target_name=dbuser.username,
        previous_value={"label": previous_label},
        new_value={"label": slot.label},
        request=request,
    )
    return _slot_response(dbuser.username, slot, _can_view_full_ip(db, admin))


@router.post("/users/{username}/reset-strikes", response_model=DeviceLimitStateResponse)
def reset_strikes(
    request: Request,
    dbuser=Depends(get_validated_user),
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
):
    state = db.get(DeviceLimitUserState, dbuser.id)
    if state is None:
        state = DeviceLimitUserState(user_id=dbuser.id)
        db.add(state)
    state.violation_count = 0
    state.current_stage = 0
    state.last_violation_at = None
    state.last_reason = None
    if state.penalty_status == PenaltyStatus.warning.value:
        state.penalty_status = PenaltyStatus.clear.value
    db.query(DeviceLimitIncident).filter(
        DeviceLimitIncident.user_id == dbuser.id,
        DeviceLimitIncident.resolved_at.is_(None),
    ).update(
        {
            DeviceLimitIncident.resolved_at: datetime.utcnow(),
            DeviceLimitIncident.event_state: DeviceEventState.resolved.value,
        },
        synchronize_session=False,
    )
    db.commit()
    db.refresh(state)
    engine.clear_user_activity(dbuser.id)
    AuditLogService.log(
        db,
        admin,
        "device_limit.strikes_reset",
        "user",
        f"Admin {admin.username} reset device-limit strikes for {dbuser.username}",
        target_id=dbuser.id,
        target_name=dbuser.username,
        request=request,
    )
    return state


@router.delete("/warnings/{incident_id}")
def delete_warning(
    incident_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
):
    incident = db.get(DeviceLimitIncident, incident_id)
    if incident is None or incident.event_state != DeviceEventState.warning.value:
        raise HTTPException(status_code=404, detail="Device warning not found")
    if not admin.is_sudo:
        dbadmin = crud.get_admin(db, admin.username)
        if dbadmin is None or incident.admin_id != dbadmin.id:
            raise HTTPException(status_code=403, detail="You're not allowed")
    user_id = incident.user_id
    username = incident.username
    db.delete(incident)
    if user_id is not None:
        remaining = (
            db.query(DeviceLimitIncident.id)
            .filter(
                DeviceLimitIncident.user_id == user_id,
                DeviceLimitIncident.id != incident_id,
                DeviceLimitIncident.event_state == DeviceEventState.warning.value,
                DeviceLimitIncident.resolved_at.is_(None),
            )
            .first()
        )
        state = db.get(DeviceLimitUserState, user_id)
        if remaining is None and state and state.penalty_status == PenaltyStatus.warning.value:
            state.penalty_status = PenaltyStatus.clear.value
            state.last_reason = None
    db.commit()
    AuditLogService.log(
        db,
        admin,
        "device_limit.warning_delete",
        "device_limit_incident",
        f"Admin {admin.username} deleted device warning for {username}",
        target_id=incident_id,
        target_name=username,
        request=request,
    )
    return {"detail": "Device warning deleted"}


@router.post("/users/{username}/unblock", response_model=DeviceLimitStateResponse)
def unblock_user(
    request: Request,
    dbuser=Depends(get_validated_user),
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
):
    state = db.get(DeviceLimitUserState, dbuser.id)
    if state is None:
        state = DeviceLimitUserState(user_id=dbuser.id)
        db.add(state)
    if dbuser.status == UserStatus.disabled and state.penalty_status in (
        PenaltyStatus.temporarily_disabled.value,
        PenaltyStatus.permanently_disabled.value,
    ):
        dbuser.status = UserStatus.active
        dbuser.last_status_change = datetime.utcnow()
        xray.operations.add_user(dbuser)
    state.penalty_status = PenaltyStatus.clear.value
    state.blocked_until = None
    db.query(DeviceLimitIncident).filter(
        DeviceLimitIncident.user_id == dbuser.id,
        DeviceLimitIncident.resolved_at.is_(None),
    ).update(
        {
            DeviceLimitIncident.resolved_at: datetime.utcnow(),
            DeviceLimitIncident.event_state: DeviceEventState.resolved.value,
        },
        synchronize_session=False,
    )
    db.commit()
    db.refresh(state)
    engine.clear_user_activity(dbuser.id)
    AuditLogService.log(
        db,
        admin,
        "device_limit.unblock",
        "user",
        f"Admin {admin.username} manually unblocked {dbuser.username}",
        target_id=dbuser.id,
        target_name=dbuser.username,
        request=request,
    )
    return state
