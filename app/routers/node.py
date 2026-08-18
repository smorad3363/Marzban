import asyncio
import time
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, WebSocket
from sqlalchemy.exc import IntegrityError
from starlette.websockets import WebSocketDisconnect

from app import logger, xray
from app.db import Session, crud, get_db
from app.dependencies import get_dbnode, validate_dates
from app.models.admin import Admin
from app.models.node import (
    NodeCreate,
    NodeModify,
    NodeResponse,
    NodeSettings,
    NodeStatus,
    NodesUsageResponse,
    NodeWatchdogSettingsResponse,
    NodeWatchdogSettingsUpdate,
)
from app.utils.node_watchdog import send_telegram_message
from app.models.proxy import ProxyHost
from app.utils import admin_hierarchy, responses
from app.utils.audit import AuditLogService, sanitize_audit_value

router = APIRouter(
    tags=["Node"], prefix="/api", responses={401: responses._401, 403: responses._403}
)


def add_host_if_needed(new_node: NodeCreate, db: Session):
    """Add a host if specified in the new node settings."""
    if new_node.add_as_new_host:
        host = ProxyHost(
            remark=f"{new_node.name} ({{USERNAME}}) [{{PROTOCOL}} - {{TRANSPORT}}]",
            address=new_node.address,
        )
        for inbound_tag in xray.config.inbounds_by_tag:
            crud.add_host(db, inbound_tag, host)
        xray.hosts.update()


@router.get("/node/settings", response_model=NodeSettings)
def get_node_settings(
    db: Session = Depends(get_db), admin: Admin = Depends(Admin.check_sudo_admin)
):
    """Retrieve the current node settings, including TLS certificate."""
    tls = crud.get_tls_certificate(db)
    return NodeSettings(certificate=tls.certificate)


def _watchdog_response(settings) -> NodeWatchdogSettingsResponse:
    return NodeWatchdogSettingsResponse(
        enabled=settings.enabled,
        telegram_bot_token_configured=bool(settings.telegram_bot_token),
        telegram_chat_id=settings.telegram_chat_id,
        check_interval=settings.check_interval,
        backoff_cap=settings.backoff_cap,
        remind_every=settings.remind_every,
    )


@router.get("/node/watchdog/settings", response_model=NodeWatchdogSettingsResponse)
def get_watchdog_settings(
    db: Session = Depends(get_db), _: Admin = Depends(Admin.check_sudo_admin)
):
    return _watchdog_response(crud.get_node_watchdog_settings(db))


@router.put("/node/watchdog/settings", response_model=NodeWatchdogSettingsResponse)
def set_watchdog_settings(
    request: Request,
    update: NodeWatchdogSettingsUpdate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.check_sudo_admin),
):
    current = crud.get_node_watchdog_settings(db)
    if update.enabled and not (update.telegram_bot_token or current.telegram_bot_token):
        raise HTTPException(status_code=422, detail={"telegram_bot_token": "Bot token is required"})
    if update.enabled and not update.telegram_chat_id:
        raise HTTPException(status_code=422, detail={"telegram_chat_id": "Chat ID is required"})
    previous_value = _watchdog_response(current)
    result = _watchdog_response(crud.update_node_watchdog_settings(db, update))
    AuditLogService.log(
        db,
        admin,
        "settings.watchdog_update",
        "node_watchdog",
        f"Admin {admin.username} updated node watchdog settings",
        previous_value=previous_value,
        new_value=result,
        request=request,
    )
    return result


@router.post("/node/watchdog/test")
def test_watchdog_notification(
    request: Request,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.check_sudo_admin),
):
    settings = crud.get_node_watchdog_settings(db)
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        raise HTTPException(status_code=422, detail="Configure the Telegram bot token and Chat ID first")
    try:
        send_telegram_message(
            settings.telegram_bot_token,
            settings.telegram_chat_id,
            "✅ <b>Marzban watchdog</b> is configured correctly.",
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    AuditLogService.log(
        db,
        admin,
        "settings.watchdog_test",
        "node_watchdog",
        f"Admin {admin.username} sent a watchdog test notification",
        request=request,
    )
    return {"detail": "Test notification sent"}


@router.post("/node", response_model=NodeResponse, responses={409: responses._409})
def add_node(
    request: Request,
    new_node: NodeCreate,
    bg: BackgroundTasks,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.check_sudo_admin),
):
    """Add a new node to the database and optionally add it as a host."""
    try:
        dbnode = crud.create_node(db, new_node)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409, detail=f'Node "{new_node.name}" already exists'
        )

    bg.add_task(xray.operations.connect_node, node_id=dbnode.id)
    bg.add_task(add_host_if_needed, new_node, db)

    logger.info(f'New node "{dbnode.name}" added')
    AuditLogService.log(
        db,
        admin,
        "node.create",
        "node",
        f"Admin {admin.username} created node {dbnode.name}",
        target_id=dbnode.id,
        target_name=dbnode.name,
        new_value=sanitize_audit_value(dbnode),
        request=request,
    )
    return dbnode


@router.get("/node/{node_id}", response_model=NodeResponse)
def get_node(
    dbnode: NodeResponse = Depends(get_dbnode),
    _: Admin = Depends(Admin.check_sudo_admin),
):
    """Retrieve details of a specific node by its ID."""
    return dbnode


@router.websocket("/node/{node_id}/logs")
async def node_logs(node_id: int, websocket: WebSocket, db: Session = Depends(get_db)):
    token = websocket.query_params.get("token") or websocket.headers.get(
        "Authorization", ""
    ).removeprefix("Bearer ")
    admin = Admin.get_admin(token, db)
    if not admin:
        return await websocket.close(reason="Unauthorized", code=4401)

    dbadmin = crud.get_admin(db, admin.username)
    if admin.auth_method != "session" or dbadmin is None or not admin_hierarchy.is_owner(db, dbadmin):
        return await websocket.close(reason="You're not allowed", code=4403)

    if not xray.nodes.get(node_id):
        return await websocket.close(reason="Node not found", code=4404)

    if not xray.nodes[node_id].connected:
        return await websocket.close(reason="Node is not connected", code=4400)

    interval = websocket.query_params.get("interval")
    if interval:
        try:
            interval = float(interval)
        except ValueError:
            return await websocket.close(reason="Invalid interval value", code=4400)
        if interval > 10:
            return await websocket.close(
                reason="Interval must be more than 0 and at most 10 seconds", code=4400
            )

    await websocket.accept()

    cache = ""
    last_sent_ts = 0
    node = xray.nodes[node_id]
    with node.get_logs() as logs:
        while True:
            if not node == xray.nodes[node_id]:
                break

            if interval and time.time() - last_sent_ts >= interval and cache:
                try:
                    await websocket.send_text(cache)
                except (WebSocketDisconnect, RuntimeError):
                    break
                cache = ""
                last_sent_ts = time.time()

            if not logs:
                try:
                    await asyncio.wait_for(websocket.receive(), timeout=0.2)
                    continue
                except asyncio.TimeoutError:
                    continue
                except (WebSocketDisconnect, RuntimeError):
                    break

            log = logs.popleft()

            if interval:
                cache += f"{log}\n"
                continue

            try:
                await websocket.send_text(log)
            except (WebSocketDisconnect, RuntimeError):
                break


@router.get("/nodes", response_model=List[NodeResponse])
def get_nodes(
    db: Session = Depends(get_db), _: Admin = Depends(Admin.check_sudo_admin)
):
    """Retrieve a list of all nodes. Accessible only to sudo admins."""
    return crud.get_nodes(db)


@router.put("/node/{node_id}", response_model=NodeResponse)
def modify_node(
    request: Request,
    modified_node: NodeModify,
    bg: BackgroundTasks,
    dbnode: NodeResponse = Depends(get_node),
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.check_sudo_admin),
):
    """Update a node's details. Only accessible to sudo admins."""
    previous_value = sanitize_audit_value(dbnode)
    updated_node = crud.update_node(db, dbnode, modified_node)
    xray.operations.remove_node(updated_node.id)
    if updated_node.status != NodeStatus.disabled:
        bg.add_task(xray.operations.connect_node, node_id=updated_node.id)

    logger.info(f'Node "{dbnode.name}" modified')
    AuditLogService.log(
        db,
        admin,
        "node.update",
        "node",
        f"Admin {admin.username} updated node {updated_node.name}",
        target_id=updated_node.id,
        target_name=updated_node.name,
        previous_value=previous_value,
        new_value=sanitize_audit_value(updated_node),
        request=request,
    )
    return dbnode


@router.post("/node/{node_id}/reconnect")
def reconnect_node(
    request: Request,
    bg: BackgroundTasks,
    dbnode: NodeResponse = Depends(get_node),
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.check_sudo_admin),
):
    """Trigger a reconnection for the specified node. Only accessible to sudo admins."""
    bg.add_task(xray.operations.connect_node, node_id=dbnode.id)
    AuditLogService.log(
        db,
        admin,
        "node.reconnect",
        "node",
        f"Admin {admin.username} scheduled reconnect for node {dbnode.name}",
        target_id=dbnode.id,
        target_name=dbnode.name,
        request=request,
    )
    return {"detail": "Reconnection task scheduled"}


@router.delete("/node/{node_id}")
def remove_node(
    request: Request,
    dbnode: NodeResponse = Depends(get_node),
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.check_sudo_admin),
):
    """Delete a node and remove it from xray in the background."""
    target_id = dbnode.id
    target_name = dbnode.name
    previous_value = sanitize_audit_value(dbnode)
    crud.remove_node(db, dbnode)
    xray.operations.remove_node(target_id)

    logger.info(f'Node "{dbnode.name}" deleted')
    AuditLogService.log(
        db,
        admin,
        "node.delete",
        "node",
        f"Admin {admin.username} deleted node {target_name}",
        target_id=target_id,
        target_name=target_name,
        previous_value=previous_value,
        request=request,
    )
    return {}


@router.get("/nodes/usage", response_model=NodesUsageResponse)
def get_usage(
    db: Session = Depends(get_db),
    start: str = "",
    end: str = "",
    _: Admin = Depends(Admin.check_sudo_admin),
):
    """Retrieve usage statistics for nodes within a specified date range."""
    start, end = validate_dates(start, end)

    usages = crud.get_nodes_usage(db, start, end)

    return {"usages": usages}
