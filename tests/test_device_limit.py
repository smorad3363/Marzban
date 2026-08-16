from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models import (
    Admin,
    MarzhelpAdminSettings,
    MarzhelpAdminSubscriptionModePermission,
    Proxy,
    User,
    MarzhelpAdminUserLimitPermission,
)
from app.device_limit.constants import SubscriptionMode
from app.device_limit.engine import DeviceLimitEngine, mask_ip
from app.device_limit.slots import slot_email, sync_device_slots
from app.models.user import UserStatus
from app.utils import marzhelp_policy


@pytest.fixture()
def session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'device-limit.sqlite3'}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    db = Session()
    yield db
    db.close()
    engine.dispose()


def test_xray_access_parser_is_bounded_and_requires_hit_threshold():
    tracker = DeviceLimitEngine()
    tracker.configure(True, "hybrid")
    lines = "\n".join(
        (
            "2026/08/16 12:00:00 8.8.8.8:51000 accepted tcp:example.com:443 [vless >> direct] email: 42.demo.slot2",
            "2026/08/16 12:00:01 8.8.8.8:51001 accepted tcp:example.com:443 [vless >> direct] email: 42.demo.slot2",
            "2026/08/16 12:00:02 1.1.1.1:51002 accepted tcp:example.com:443 [vless >> direct] email: 42.demo.slot2",
            "2026/08/16 12:00:03 192.168.1.4:51003 accepted tcp:example.com:443 [vless >> direct] email: 42.demo.slot2",
        )
    )
    assert tracker.record_log(lines, "node:7") == 3
    addresses, sources, per_slot = tracker.live_snapshot(42, 300, 2)
    assert addresses == {"8.8.8.8"}
    assert sources == {"node:7"}
    assert per_slot == {2: {"8.8.8.8"}}
    assert mask_ip("8.8.8.8") == "8.8.***.***"


def test_finite_limit_creates_independent_standard_credentials(session):
    base_id = str(uuid4())
    user = User(
        username="slot-user",
        status=UserStatus.active,
        concurrent_user_limit=2,
        proxies=[Proxy(type="vless", settings={"id": base_id, "flow": ""})],
    )
    session.add(user)
    session.flush()

    slots = sync_device_slots(session, user)

    assert [slot.slot_index for slot in slots] == [1, 2]
    assert slots[0].credentials["vless"]["id"] == base_id
    assert slots[1].credentials["vless"]["id"] != base_id
    assert slot_email(user.id, user.username, 1) == f"{user.id}.slot-user"
    assert slot_email(user.id, user.username, 2) == f"{user.id}.slot-user.slot2"


def test_explicit_subscription_mode_permissions_are_enforced(session):
    admin = Admin(username="mode-admin", hashed_password="x", is_sudo=False)
    session.add(admin)
    session.flush()
    settings = MarzhelpAdminSettings(admin_id=admin.id)
    settings.subscription_mode_permissions = [
        MarzhelpAdminSubscriptionModePermission(
            admin_id=admin.id,
            mode=SubscriptionMode.unlimited_traffic_limited_devices.value,
        )
    ]
    session.add(settings)
    session.commit()

    allowed = type("Plan", (), {
        "data_limit": None,
        "concurrent_user_limit": 2,
        "expire": None,
        "on_hold_expire_duration": None,
        "next_plan": None,
        "inbounds": None,
    })()
    assert marzhelp_policy.validate_create(session, admin.id, allowed) is settings
    session.rollback()

    denied = type("Plan", (), {
        "data_limit": None,
        "concurrent_user_limit": None,
        "expire": None,
        "on_hold_expire_duration": None,
        "next_plan": None,
        "inbounds": None,
    })()
    with pytest.raises(marzhelp_policy.MarzhelpPolicyError) as exc:
        marzhelp_policy.validate_create(session, admin.id, denied)
    assert exc.value.code == "subscription_mode_forbidden"


def test_unlimited_devices_are_controlled_by_mode_not_finite_limit_allowlist(session):
    admin = Admin(username="unlimited-device-admin", hashed_password="x", is_sudo=False)
    session.add(admin)
    session.flush()
    settings = MarzhelpAdminSettings(admin_id=admin.id, all_user_limits=False)
    settings.user_limit_permissions = [
        MarzhelpAdminUserLimitPermission(admin_id=admin.id, concurrent_user_limit=2)
    ]
    settings.subscription_mode_permissions = [
        MarzhelpAdminSubscriptionModePermission(
            admin_id=admin.id,
            mode=SubscriptionMode.limited_traffic_unlimited_devices.value,
        )
    ]
    session.add(settings)
    session.commit()

    plan = type("Plan", (), {
        "data_limit": 10 * 1024**3,
        "concurrent_user_limit": None,
        "expire": None,
        "on_hold_expire_duration": None,
        "next_plan": None,
        "inbounds": None,
    })()
    assert marzhelp_policy.validate_create(session, admin.id, plan) is settings
