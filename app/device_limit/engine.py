from __future__ import annotations

import ipaddress
import json
import logging
import re
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Iterable

from sqlalchemy import update

from app import logger, xray
from app.db import GetDB
from app.db.models import (
    AdminAuditLog,
    DeviceLimitIncident,
    DeviceLimitPenaltyStage,
    DeviceLimitSettings,
    DeviceLimitUserState,
    DeviceSlot,
    User,
)
from app.device_limit.constants import PenaltyAction, PenaltyStatus
from app.models.user import UserStatus
from app.utils.audit import AuditLogService


SOURCE_RE = re.compile(
    r"(?:^|\s)(?:\[([0-9a-fA-F:]+)\]|(\d{1,3}(?:\.\d{1,3}){3})):\d+\s+accepted\b"
)
EMAIL_RE = re.compile(
    r"email:\s*(\d+)\.([A-Za-z0-9_@+%\-.]+?)(?:\.slot(\d+))?(?:\s|$)"
)
MAX_IPS_PER_SLOT = 64


def utc_now() -> datetime:
    return datetime.utcnow()


def mask_ip(value: str) -> str:
    try:
        parsed = ipaddress.ip_address(value)
    except ValueError:
        return "***"
    if parsed.version == 4:
        parts = value.split(".")
        return f"{parts[0]}.{parts[1]}.***.***"
    groups = parsed.exploded.split(":")
    return ":".join(groups[:3] + ["****"] * 5)


class DeviceLimitEngine:
    """Bounded, in-memory Xray activity tracker with durable incidents only."""

    def __init__(self):
        self._lock = threading.RLock()
        self._activity: dict[int, dict[int, dict[str, deque[float]]]] = defaultdict(
            lambda: defaultdict(dict)
        )
        self._sources: dict[int, set[str]] = defaultdict(set)
        self._stop = threading.Event()
        self._collector_threads: dict[str, threading.Thread] = {}
        self._manager_thread: threading.Thread | None = None
        self._last_evaluation = 0.0
        self._event_logger: logging.Logger | None = None
        self._runtime_enabled = False
        self._enforcement_mode = "hybrid"
        self._limited_user_ids: set[int] | None = None
        self._last_user_cache_refresh = 0.0

    def start(self) -> None:
        if self._manager_thread and self._manager_thread.is_alive():
            return
        self._stop.clear()
        self._configure_event_logger()
        try:
            with GetDB() as db:
                settings = db.get(DeviceLimitSettings, 1)
                if settings is not None:
                    self.configure(settings.enabled, settings.enforcement_mode)
                    if settings.enabled:
                        self._refresh_limited_users(db, force=True)
        except Exception as exc:
            logger.warning("Unable to load device-limit settings at startup: %s", exc)
        self._manager_thread = threading.Thread(
            target=self._manage_collectors,
            name="device-limit-log-manager",
            daemon=True,
        )
        self._manager_thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _configure_event_logger(self) -> None:
        event_logger = logging.getLogger("marzban.device_limit.events")
        if event_logger.handlers:
            self._event_logger = event_logger
            return
        try:
            from config import DEVICE_LIMIT_LOG_DIR

            path = Path(DEVICE_LIMIT_LOG_DIR)
            path.mkdir(parents=True, exist_ok=True)
            handler = RotatingFileHandler(
                path / "events.jsonl",
                maxBytes=25 * 1024 * 1024,
                backupCount=10,
                encoding="utf-8",
            )
            handler.setFormatter(logging.Formatter("%(message)s"))
            event_logger.addHandler(handler)
            event_logger.setLevel(logging.INFO)
            event_logger.propagate = False
            self._event_logger = event_logger
        except OSError as exc:
            logger.warning("Unable to initialize device-limit event file: %s", exc)

    def _manage_collectors(self) -> None:
        while not self._stop.wait(1):
            if getattr(xray.core, "started", False):
                self._ensure_collector("main", xray.core, "master")
            for node_id, node in list(xray.nodes.items()):
                try:
                    ready = node.connected and node.started
                except Exception:
                    ready = False
                if ready:
                    self._ensure_collector(f"node:{node_id}", node, f"node:{node_id}")

    def _ensure_collector(self, key: str, source, source_name: str) -> None:
        current = self._collector_threads.get(key)
        if current and current.is_alive():
            return
        thread = threading.Thread(
            target=self._collect,
            args=(source, source_name),
            name=f"device-limit-{key}",
            daemon=True,
        )
        self._collector_threads[key] = thread
        thread.start()

    def _collect(self, source, source_name: str) -> None:
        try:
            with source.get_logs() as logs:
                while not self._stop.wait(0.2):
                    try:
                        line = logs.popleft()
                    except IndexError:
                        continue
                    self.record_log(line, source_name)
        except Exception as exc:
            logger.debug("Device-limit collector %s stopped: %s", source_name, exc)

    def record_log(self, raw: str, source_name: str = "master") -> int:
        if not self._runtime_enabled or self._enforcement_mode == "slots":
            return 0
        recorded = 0
        now = time.time()
        for line in str(raw).splitlines():
            if "accepted" not in line or "BLOCK]" in line:
                continue
            source_match = SOURCE_RE.search(line)
            email_match = EMAIL_RE.search(line)
            if not source_match or not email_match:
                continue
            address = source_match.group(1) or source_match.group(2)
            try:
                parsed = ipaddress.ip_address(address)
            except ValueError:
                continue
            if parsed.is_private or parsed.is_loopback or parsed.is_unspecified:
                continue
            user_id = int(email_match.group(1))
            if (
                self._limited_user_ids is not None
                and user_id not in self._limited_user_ids
            ):
                continue
            slot_index = int(email_match.group(3) or 1)
            with self._lock:
                slot = self._activity[user_id][slot_index]
                if address not in slot and len(slot) >= MAX_IPS_PER_SLOT:
                    oldest = min(slot, key=lambda key: slot[key][-1])
                    del slot[oldest]
                hits = slot.setdefault(address, deque(maxlen=128))
                hits.append(now)
                self._sources[user_id].add(source_name)
            recorded += 1
        return recorded

    def _snapshot_user(
        self,
        user_id: int,
        window_seconds: int,
        hit_threshold: int,
    ) -> tuple[set[str], set[str], dict[int, set[str]]]:
        cutoff = time.time() - window_seconds
        per_slot: dict[int, set[str]] = {}
        with self._lock:
            slots = self._activity.get(user_id, {})
            for slot_index, addresses in list(slots.items()):
                qualified: set[str] = set()
                for address, hits in list(addresses.items()):
                    while hits and hits[0] < cutoff:
                        hits.popleft()
                    if not hits:
                        del addresses[address]
                    elif len(hits) >= hit_threshold:
                        qualified.add(address)
                if not addresses:
                    slots.pop(slot_index, None)
                if qualified:
                    per_slot[slot_index] = qualified
            if not slots:
                self._activity.pop(user_id, None)
                self._sources.pop(user_id, None)
            sources = set(self._sources.get(user_id, set()))
        all_addresses = set().union(*per_slot.values()) if per_slot else set()
        return all_addresses, sources, per_slot

    def live_snapshot(
        self,
        user_id: int,
        window_seconds: int,
        hit_threshold: int,
    ) -> tuple[set[str], set[str], dict[int, set[str]]]:
        return self._snapshot_user(user_id, window_seconds, hit_threshold)

    def evaluate(self) -> None:
        with GetDB() as db:
            settings = db.get(DeviceLimitSettings, 1)
            self.configure(
                bool(settings and settings.enabled),
                settings.enforcement_mode if settings else "hybrid",
            )
            if settings is None or not settings.enabled:
                return
            self._refresh_limited_users(db)
            if settings.enforcement_mode == "slots":
                self._release_due_penalties(db, settings, force=True)
                return
            now_monotonic = time.monotonic()
            if now_monotonic - self._last_evaluation < settings.check_interval_seconds:
                return
            self._last_evaluation = now_monotonic
            with self._lock:
                active_ids = list(self._activity)
            if not active_ids:
                self._release_due_penalties(db, settings)
                return

            stages = (
                db.query(DeviceLimitPenaltyStage)
                .filter(DeviceLimitPenaltyStage.enabled.is_(True))
                .order_by(DeviceLimitPenaltyStage.violation_count.asc())
                .all()
            )
            now = utc_now()
            for chunk_start in range(0, len(active_ids), 500):
                users = (
                    db.query(User)
                    .filter(
                        User.id.in_(active_ids[chunk_start:chunk_start + 500]),
                        User.concurrent_user_limit.is_not(None),
                        User.status.in_((UserStatus.active, UserStatus.on_hold)),
                    )
                    .all()
                )
                for user in users:
                    addresses, sources, per_slot = self._snapshot_user(
                        user.id,
                        settings.active_window_seconds,
                        settings.hit_threshold,
                    )
                    limit = int(user.concurrent_user_limit or 0)
                    if limit < 1 or len(addresses) <= limit:
                        continue
                    state = db.get(DeviceLimitUserState, user.id)
                    if state and state.last_violation_at:
                        cooldown = timedelta(seconds=settings.active_window_seconds)
                        if state.last_violation_at + cooldown > now:
                            continue
                        if state.last_violation_at + timedelta(
                            seconds=settings.strike_reset_seconds
                        ) <= now:
                            state.violation_count = 0
                    if state is None:
                        state = DeviceLimitUserState(user_id=user.id)
                        db.add(state)
                    state.violation_count = int(state.violation_count or 0) + 1
                    stage = self._stage_for(stages, state.violation_count)
                    self._apply_penalty(
                        db,
                        settings,
                        user,
                        state,
                        stage,
                        addresses,
                        sources,
                        per_slot,
                        now,
                    )
            db.commit()
            self._release_due_penalties(db, settings)

    def _refresh_limited_users(self, db, force: bool = False) -> None:
        now = time.monotonic()
        if not force and now - self._last_user_cache_refresh < 60:
            return
        limited_ids = {
            row[0]
            for row in db.query(User.id).filter(
                User.concurrent_user_limit.is_not(None),
                User.status.in_((UserStatus.active, UserStatus.on_hold)),
            )
        }
        with self._lock:
            self._limited_user_ids = limited_ids
            for user_id in set(self._activity) - limited_ids:
                self._activity.pop(user_id, None)
                self._sources.pop(user_id, None)
        self._last_user_cache_refresh = now

    @staticmethod
    def _stage_for(stages: Iterable[DeviceLimitPenaltyStage], count: int):
        selected = None
        for stage in stages:
            if stage.violation_count <= count:
                selected = stage
            else:
                break
        return selected

    def _apply_penalty(
        self,
        db,
        settings: DeviceLimitSettings,
        user: User,
        state: DeviceLimitUserState,
        stage: DeviceLimitPenaltyStage | None,
        addresses: set[str],
        sources: set[str],
        per_slot: dict[int, set[str]],
        now: datetime,
    ) -> None:
        action = PenaltyAction(stage.action) if stage else PenaltyAction.warn
        if action == PenaltyAction.delete and not settings.auto_delete_enabled:
            action = PenaltyAction.permanent_disable
        reason = (
            f"Observed {len(addresses)} active public IPs for configured device limit "
            f"{user.concurrent_user_limit}"
        )
        state.current_stage = stage.violation_count if stage else state.violation_count
        state.last_violation_at = now
        state.last_seen_at = now
        state.active_ip_count = len(addresses)
        state.last_reason = reason

        if action == PenaltyAction.warn:
            state.penalty_status = PenaltyStatus.warning.value
            state.blocked_until = None
        elif action == PenaltyAction.temporary_disable:
            if state.penalty_status != PenaltyStatus.temporarily_disabled.value:
                state.status_before_penalty = getattr(user.status, "value", user.status)
            state.penalty_status = PenaltyStatus.temporarily_disabled.value
            state.blocked_until = now + timedelta(seconds=int(stage.duration_seconds))
            user.status = UserStatus.disabled
            user.last_status_change = now
            xray.operations.remove_user(user)
        elif action == PenaltyAction.permanent_disable:
            if state.penalty_status != PenaltyStatus.permanently_disabled.value:
                state.status_before_penalty = getattr(user.status, "value", user.status)
            state.penalty_status = PenaltyStatus.permanently_disabled.value
            state.blocked_until = None
            user.status = UserStatus.disabled
            user.last_status_change = now
            xray.operations.remove_user(user)
        else:
            state.penalty_status = PenaltyStatus.deleted.value
            state.blocked_until = None
            xray.operations.remove_user(user)

        incident = DeviceLimitIncident(
            user_id=user.id,
            admin_id=user.admin_id,
            username=user.username,
            stage=state.current_stage,
            action=action.value,
            configured_limit=int(user.concurrent_user_limit),
            observed_count=len(addresses),
            ip_addresses=sorted(addresses),
            source_nodes=sorted(sources),
            reason=reason,
            created_at=now,
        )
        db.add(incident)
        for slot in user.device_slots:
            slot_addresses = per_slot.get(slot.slot_index)
            if slot_addresses:
                slot.last_seen_at = now
                slot.last_ip = sorted(slot_addresses)[-1]
        AuditLogService.log(
            db,
            "device-limit-engine",
            f"device_limit.{action.value}",
            "user",
            reason,
            target_id=user.id,
            target_name=user.username,
            details={
                "stage": state.current_stage,
                "configured_limit": user.concurrent_user_limit,
                "observed_count": len(addresses),
            },
            commit=False,
        )
        self._write_event(incident)
        if action == PenaltyAction.delete:
            incident.user_id = None
            db.delete(user)

    def _release_due_penalties(
        self,
        db,
        settings: DeviceLimitSettings,
        force: bool = False,
    ) -> None:
        now = utc_now()
        query = db.query(DeviceLimitUserState).filter(
            DeviceLimitUserState.penalty_status
            == PenaltyStatus.temporarily_disabled.value,
            DeviceLimitUserState.blocked_until.is_not(None),
        )
        if not force:
            query = query.filter(DeviceLimitUserState.blocked_until <= now)
        states = query.all()
        changed = False
        for state in states:
            user = state.user
            if user is None:
                continue
            manually_changed = (
                user.last_status_change
                and state.updated_at
                and user.last_status_change > state.updated_at + timedelta(seconds=1)
            )
            if not manually_changed and user.status == UserStatus.disabled:
                previous = state.status_before_penalty or UserStatus.active.value
                if previous not in (UserStatus.active.value, UserStatus.on_hold.value):
                    previous = UserStatus.active.value
                user.status = UserStatus(previous)
                user.last_status_change = now
                xray.operations.add_user(user)
            state.penalty_status = PenaltyStatus.clear.value
            state.blocked_until = None
            db.query(DeviceLimitIncident).filter(
                DeviceLimitIncident.user_id == user.id,
                DeviceLimitIncident.resolved_at.is_(None),
            ).update({DeviceLimitIncident.resolved_at: now}, synchronize_session=False)
            changed = True
        if changed:
            db.commit()

    def release_all_temporary_penalties(self) -> None:
        with GetDB() as db:
            settings = db.get(DeviceLimitSettings, 1)
            if settings is not None:
                self._release_due_penalties(db, settings, force=True)

    def retention_cleanup(self) -> None:
        with GetDB() as db:
            settings = db.get(DeviceLimitSettings, 1)
            if settings is None:
                return
            now = utc_now()
            db.execute(
                update(DeviceLimitIncident)
                .where(
                    DeviceLimitIncident.created_at
                    < now - timedelta(days=settings.full_ip_retention_days)
                )
                .values(ip_addresses=None)
            )
            db.query(DeviceLimitIncident).filter(
                DeviceLimitIncident.created_at
                < now - timedelta(days=settings.incident_retention_days)
            ).delete(synchronize_session=False)
            db.query(AdminAuditLog).filter(
                AdminAuditLog.created_at
                < now - timedelta(days=settings.audit_retention_days)
            ).delete(synchronize_session=False)
            db.commit()

    def clear_user_activity(self, user_id: int) -> None:
        with self._lock:
            self._activity.pop(user_id, None)
            self._sources.pop(user_id, None)

    def configure(self, enabled: bool, enforcement_mode: str = "hybrid") -> None:
        self._runtime_enabled = enabled
        self._enforcement_mode = enforcement_mode
        if not enabled or enforcement_mode == "slots":
            with self._lock:
                self._activity.clear()
                self._sources.clear()
        if not enabled:
            self._limited_user_ids = set()

    def _write_event(self, incident: DeviceLimitIncident) -> None:
        if self._event_logger is None:
            return
        self._event_logger.info(
            json.dumps(
                {
                    "created_at": incident.created_at.isoformat(),
                    "event": f"device_limit.{incident.action}",
                    "user_id": incident.user_id,
                    "admin_id": incident.admin_id,
                    "username": incident.username,
                    "stage": incident.stage,
                    "configured_limit": incident.configured_limit,
                    "observed_count": incident.observed_count,
                    # Durable full addresses live only in the retention-managed DB.
                    "ip_addresses": [mask_ip(value) for value in (incident.ip_addresses or [])],
                    "source_nodes": incident.source_nodes,
                    "reason": incident.reason,
                },
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )


engine = DeviceLimitEngine()
