from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from app.db.models import DeviceLimitSettings, DeviceSlot
from app.models.proxy import ProxySettings, ProxyTypes
from app.utils.jwt import create_device_slot_token
from config import XRAY_SUBSCRIPTION_PATH, XRAY_SUBSCRIPTION_URL_PREFIX

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.db.models import User


def slot_email(user_id: int, username: str, slot_index: int) -> str:
    if slot_index == 1:
        return f"{user_id}.{username}"
    return f"{user_id}.{username}.slot{slot_index}"


def _base_credentials(dbuser: "User") -> dict[str, dict]:
    return {
        ProxyTypes(proxy.type).value: dict(proxy.settings)
        for proxy in dbuser.proxies
    }


def _credentials_for_slot(
    dbuser: "User",
    slot_index: int,
    previous: dict[str, dict] | None = None,
) -> dict[str, dict]:
    base = _base_credentials(dbuser)
    if slot_index == 1:
        return base

    result: dict[str, dict] = {}
    previous = previous or {}
    for protocol, raw_settings in base.items():
        proxy_type = ProxyTypes(protocol)
        settings = ProxySettings.from_dict(proxy_type, raw_settings)
        old = previous.get(protocol, {})
        if "id" in old and hasattr(settings, "id"):
            settings.id = UUID(str(old["id"]))
        elif "password" in old and hasattr(settings, "password"):
            settings.password = old["password"]
        else:
            settings.revoke()
        result[protocol] = settings.dict(no_obj=True)
    return result


def sync_device_slots(db: "Session", dbuser: "User") -> list[DeviceSlot]:
    """Synchronize persistent slots with the user's finite device limit.

    Excess slots are disabled instead of deleted. Dynamic Xray updates can then
    remove stale credential emails without requiring a core restart.
    """

    settings = db.get(DeviceLimitSettings, 1)
    slots_enabled = settings is None or bool(settings.device_slots_enabled)
    desired = int(dbuser.concurrent_user_limit or 0) if slots_enabled else 0
    existing = {slot.slot_index: slot for slot in dbuser.device_slots}
    highest = max([desired, *existing.keys()], default=desired)

    for slot_index in range(1, highest + 1):
        slot = existing.get(slot_index)
        if slot_index <= desired:
            credentials = _credentials_for_slot(
                dbuser,
                slot_index,
                previous=slot.credentials if slot is not None else None,
            )
            if slot is None:
                slot = DeviceSlot(
                    user_id=dbuser.id,
                    slot_index=slot_index,
                    label=f"Device {slot_index}",
                    credentials=credentials,
                    token_version=str(uuid4()),
                    enabled=True,
                )
                dbuser.device_slots.append(slot)
            else:
                slot.credentials = credentials
                slot.enabled = True
        elif slot is not None:
            slot.enabled = False

    db.flush()
    return sorted(dbuser.device_slots, key=lambda item: item.slot_index)


def enabled_device_slots(dbuser: "User") -> list[DeviceSlot]:
    if dbuser.concurrent_user_limit is None:
        return []
    return sorted(
        (slot for slot in dbuser.device_slots if slot.enabled),
        key=lambda item: item.slot_index,
    )


def slot_subscription_url(username: str, slot: DeviceSlot) -> str:
    token = create_device_slot_token(username, slot.slot_index, slot.token_version)
    prefix = XRAY_SUBSCRIPTION_URL_PREFIX.rstrip("/")
    path = f"/{XRAY_SUBSCRIPTION_PATH}/{token}"
    return f"{prefix}{path}" if prefix else path
