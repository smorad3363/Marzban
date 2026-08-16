from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import DeviceClientObservation, DeviceSlot, User


logger = logging.getLogger(__name__)
MAX_RAW_USER_AGENT = 512
TOKEN_RE = re.compile(r"(?P<name>[A-Za-z][A-Za-z0-9 ._+-]{0,63})/(?P<version>[0-9][A-Za-z0-9._+-]{0,63})")

CLIENT_ALIASES = (
    (re.compile(r"^v2rayNG\b", re.I), "v2rayNG", "Android"),
    (re.compile(r"^v2rayN\b", re.I), "v2rayN", "Windows"),
    (re.compile(r"^Hiddify(?:Next)?\b", re.I), "HiddifyNext", None),
    (re.compile(r"^Streisand\b", re.I), "Streisand", "Apple"),
    (re.compile(r"^Shadowrocket\b", re.I), "Shadowrocket", "Apple"),
    (re.compile(r"^(?:Clash[-. ]?Meta|Clash Verge|Mihomo|FlClash)\b", re.I), "Clash", None),
    (re.compile(r"^NekoBox\b", re.I), "NekoBox", None),
    (re.compile(r"^NekoRay\b", re.I), "NekoRay", None),
    (re.compile(r"^(?:SFA|SFI|SFM|SFT|sing-box)\b", re.I), "sing-box", None),
)


@dataclass(frozen=True)
class ParsedClient:
    client_name: str
    client_version: str | None
    platform: str | None
    os_token: str | None
    network_stack: str | None
    raw_user_agent: str
    normalized_identity: str


def _bounded(value: str | None, length: int) -> str | None:
    if value is None:
        return None
    value = " ".join(value.strip().split())
    return value[:length] or None


def parse_user_agent(raw_user_agent: str | None) -> ParsedClient:
    raw = _bounded(raw_user_agent or "", MAX_RAW_USER_AGENT) or "Unknown"
    first = TOKEN_RE.search(raw)
    client_name = _bounded(first.group("name"), 64) if first else "Unknown"
    client_version = _bounded(first.group("version"), 64) if first else None
    platform = None

    for pattern, canonical_name, default_platform in CLIENT_ALIASES:
        if pattern.search(raw):
            client_name = canonical_name
            platform = default_platform
            break

    os_match = re.search(
        r"\b(?:Darwin|Android|Windows(?: NT)?|iOS|macOS|Linux)/?[0-9A-Za-z._+-]*",
        raw,
        re.I,
    )
    stack_match = re.search(r"\b(?:CFNetwork|okhttp|Cronet)/[0-9A-Za-z._+-]+", raw, re.I)
    os_token = _bounded(os_match.group(0), 128) if os_match else None
    network_stack = _bounded(stack_match.group(0), 128) if stack_match else None

    if os_token:
        lowered = os_token.lower()
        if lowered.startswith("darwin") or lowered.startswith("ios") or lowered.startswith("macos"):
            platform = "Apple"
        elif lowered.startswith("android"):
            platform = "Android"
        elif lowered.startswith("windows"):
            platform = "Windows"
        elif lowered.startswith("linux") and platform is None:
            platform = "Linux"

    # Patch releases remain the same device identity. The latest exact version
    # is still retained in client_version for diagnostics.
    major_version = client_version.split(".", 1)[0] if client_version else ""
    os_family = re.split(r"[/0-9]", os_token or "", maxsplit=1)[0].lower()
    identity_source = "|".join(
        (
            (client_name or "Unknown").lower(),
            major_version.lower(),
            (platform or "").lower(),
            os_family,
        )
    )
    identity = hashlib.sha256(identity_source.encode("utf-8")).hexdigest()
    return ParsedClient(
        client_name=client_name or "Unknown",
        client_version=client_version,
        platform=platform,
        os_token=os_token,
        network_stack=network_stack,
        raw_user_agent=raw,
        normalized_identity=identity,
    )


def observe_subscription_client(
    db: Session,
    dbuser: User,
    raw_user_agent: str | None,
) -> DeviceClientObservation:
    parsed = parse_user_agent(raw_user_agent)
    slot_index = getattr(dbuser, "_device_slot_index", None)
    slot = None
    if slot_index is not None:
        slot = (
            db.query(DeviceSlot)
            .filter(DeviceSlot.user_id == dbuser.id, DeviceSlot.slot_index == int(slot_index))
            .first()
        )
    slot_key = int(slot.slot_index) if slot is not None else 0
    now = datetime.utcnow()
    observation = (
        db.query(DeviceClientObservation)
        .filter(
            DeviceClientObservation.user_id == dbuser.id,
            DeviceClientObservation.slot_key == slot_key,
            DeviceClientObservation.normalized_identity == parsed.normalized_identity,
        )
        .first()
    )
    if observation is None:
        observation = DeviceClientObservation(
            user_id=dbuser.id,
            slot_id=slot.id if slot is not None else None,
            slot_key=slot_key,
            first_seen_at=now,
            last_seen_at=now,
            seen_count=1,
            **parsed.__dict__,
        )
        try:
            with db.begin_nested():
                db.add(observation)
                db.flush()
        except IntegrityError:
            observation = (
                db.query(DeviceClientObservation)
                .filter(
                    DeviceClientObservation.user_id == dbuser.id,
                    DeviceClientObservation.slot_key == slot_key,
                    DeviceClientObservation.normalized_identity == parsed.normalized_identity,
                )
                .one()
            )
            observation.seen_count = int(observation.seen_count or 0) + 1
            observation.last_seen_at = now
    else:
        observation.client_name = parsed.client_name
        observation.client_version = parsed.client_version
        observation.platform = parsed.platform
        observation.os_token = parsed.os_token
        observation.network_stack = parsed.network_stack
        observation.raw_user_agent = parsed.raw_user_agent
        observation.last_seen_at = now
        observation.seen_count = int(observation.seen_count or 0) + 1

    logger.info(
        "device_client_observed user_id=%s slot=%s client=%s platform=%s",
        dbuser.id,
        slot_key or "user",
        parsed.client_name,
        parsed.platform or "unknown",
    )
    return observation
