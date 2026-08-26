"""Idempotent sample data for the isolated local development database."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.engine import make_url

from app.db import GetDB, crud
from app.db.models import (
    Admin,
    AdminPlanCategory,
    AdminUserPlan,
    AdminUserPlanHost,
    AdminUserPlanInbound,
    AdminUserPlanVersion,
    MarzhelpAdminSettings,
    Proxy,
    ProxyHost,
    ProxyInbound,
    User,
)
from app.models.admin import AdminCreate
from app.models.proxy import ProxyTypes
from app.models.user import UserDataLimitResetStrategy, UserStatus
from app.utils import admin_hierarchy
from config import SQLALCHEMY_DATABASE_URL


GIB = 1024 ** 3
OWNER_USERNAME = "owner"
OWNER_PASSWORD = "DevOwner@1405"
ADMIN_PASSWORD = "DevAdmin@1405"


def require_isolated_database() -> None:
    url = make_url(SQLALCHEMY_DATABASE_URL)
    safe_hosts = {"127.0.0.1", "localhost", "host.docker.internal"}
    if (
        url.drivername != "mysql+pymysql"
        or url.host not in safe_hosts
        or url.port != 33079
        or url.database != "marzban_dev"
    ):
        raise RuntimeError(
            "Refusing to seed: expected isolated MySQL database "
            "marzban_dev on port 33079"
        )


def ensure_admin(db, username: str, password: str, phone: str) -> Admin:
    admin = crud.get_admin(db, username=username)
    values = AdminCreate(
        username=username,
        password=password,
        is_sudo=username == OWNER_USERNAME,
        phone=phone,
    )
    if admin is None:
        return crud.create_admin(db, values, commit=False)
    admin.hashed_password = values.hashed_password
    admin.phone = phone
    return admin


def configure_admins(db, owner: Admin, plan_admin: Admin, usage_admin: Admin, frozen_admin: Admin) -> None:
    owner_settings = db.get(MarzhelpAdminSettings, owner.id)
    owner_settings.billing_mode = "USED_TRAFFIC"
    owner_settings.money_billing_enabled = True
    owner_settings.money_balance_toman = 0
    owner_settings.used_traffic_price_per_gib_toman = None
    owner_settings.total_traffic = None
    owner_settings.max_users = None
    owner_settings.can_manage_plans = True
    owner_settings.can_create_admins = True
    owner_settings.can_delegate_admin_creation = True
    owner_settings.can_create_allocated_children = True
    owner_settings.admin_creation_limit = None
    owner_settings.user_creation_mode_id = admin_hierarchy.USER_CREATION_MODE_IDS[
        admin_hierarchy.FREE_FORM
    ]

    plan_settings = db.get(MarzhelpAdminSettings, plan_admin.id)
    plan_settings.billing_mode = "ALLOCATED_TRAFFIC"
    plan_settings.money_billing_enabled = True
    plan_settings.money_balance_toman = 1_000_000
    plan_settings.total_traffic = None
    plan_settings.max_users = 100
    plan_settings.calculate_volume = "created_traffic"
    plan_settings.can_manage_plans = False
    plan_settings.can_create_admins = True
    plan_settings.can_delegate_admin_creation = True
    plan_settings.can_create_allocated_children = True
    plan_settings.admin_creation_limit = 5
    plan_settings.user_creation_mode_id = admin_hierarchy.USER_CREATION_MODE_IDS[
        admin_hierarchy.PLAN_ONLY
    ]

    usage_settings = db.get(MarzhelpAdminSettings, usage_admin.id)
    usage_settings.billing_mode = "USED_TRAFFIC"
    usage_settings.money_billing_enabled = True
    usage_settings.money_balance_toman = 650_000
    usage_settings.used_traffic_price_per_gib_toman = 5_000
    usage_settings.total_traffic = None
    usage_settings.max_users = 100
    usage_settings.calculate_volume = "used_traffic"
    usage_settings.can_manage_plans = False
    usage_settings.can_create_admins = True
    usage_settings.can_delegate_admin_creation = False
    usage_settings.can_create_allocated_children = True
    usage_settings.admin_creation_limit = 2
    usage_settings.user_creation_mode_id = admin_hierarchy.USER_CREATION_MODE_IDS[
        admin_hierarchy.FREE_FORM
    ]

    frozen_settings = db.get(MarzhelpAdminSettings, frozen_admin.id)
    frozen_settings.billing_mode = "USED_TRAFFIC"
    frozen_settings.money_billing_enabled = True
    frozen_settings.money_balance_toman = 120_000
    frozen_settings.used_traffic_price_per_gib_toman = 7_000
    frozen_settings.max_users = 20
    frozen_settings.user_creation_mode_id = admin_hierarchy.USER_CREATION_MODE_IDS[
        admin_hierarchy.FREE_FORM
    ]
    frozen_settings.account_status_id = admin_hierarchy.ACCOUNT_STATUS_IDS["SUSPENDED"]
    frozen_settings.suspended_reason_id = 1
    frozen_settings.suspended_at = datetime.utcnow()
    frozen_settings.status = {"reason": "فریز آزمایشی برای بررسی حالت فقط خواندنی"}


def ensure_network(db) -> tuple[ProxyInbound, ProxyHost]:
    inbound = db.query(ProxyInbound).filter(ProxyInbound.tag == "Shadowsocks TCP").one_or_none()
    if inbound is None:
        inbound = ProxyInbound(tag="Shadowsocks TCP")
        db.add(inbound)
        db.flush()
    host = (
        db.query(ProxyHost)
        .filter(
            ProxyHost.inbound_tag == inbound.tag,
            ProxyHost.remark == "Dev {USERNAME}",
        )
        .one_or_none()
    )
    if host is None:
        host = ProxyHost(
            remark="Dev {USERNAME}",
            address="127.0.0.1",
            port=1080,
            inbound=inbound,
            is_disabled=False,
        )
        db.add(host)
        db.flush()
    return inbound, host


def ensure_plans(db, owner: Admin, inbound: ProxyInbound, host: ProxyHost) -> list[AdminUserPlan]:
    category = (
        db.query(AdminPlanCategory)
        .filter(
            AdminPlanCategory.owner_admin_id == owner.id,
            AdminPlanCategory.name == "پلن‌های آزمایشی Dev",
        )
        .one_or_none()
    )
    if category is None:
        category = AdminPlanCategory(
            owner_admin_id=owner.id,
            name="پلن‌های آزمایشی Dev",
            description="داده محلی؛ مناسب تست رابط",
        )
        db.add(category)
        db.flush()

    definitions = [
        ("اقتصادی ۲۰ گیگ", 20, 30, 1, 50_000),
        ("حرفه‌ای ۵۰ گیگ", 50, 30, 3, 100_000),
        ("سه‌ماهه ۱۲۰ گیگ", 120, 90, 5, 220_000),
    ]
    plans = []
    for name, size_gib, duration_days, device_limit, price_toman in definitions:
        plan = (
            db.query(AdminUserPlan)
            .filter(AdminUserPlan.owner_admin_id == owner.id, AdminUserPlan.name == name)
            .one_or_none()
        )
        if plan is None:
            plan = AdminUserPlan(
                owner_admin_id=owner.id,
                category_id=category.id,
                name=name,
                description="داده نمونه محیط توسعه",
                is_trial=False,
            )
            db.add(plan)
            db.flush()
            version = AdminUserPlanVersion(
                plan_id=plan.id,
                version_number=1,
                price_toman=price_toman,
                data_limit=size_gib * GIB,
                duration_days=duration_days,
                concurrent_user_limit=device_limit,
                reset_strategy="no_reset",
                renewal_volume_strategy="replace",
                renewal_time_strategy="extend_max",
                created_by_admin_id=owner.id,
            )
            db.add(version)
            db.flush()
            plan.current_version_id = version.id
            db.add(
                AdminUserPlanInbound(version_id=version.id, inbound_tag=inbound.tag)
            )
            db.add(
                AdminUserPlanHost(
                    version_id=version.id,
                    inbound_tag=inbound.tag,
                    host_id=host.id,
                )
            )
        plans.append(plan)
    return plans


def ensure_user(
    db,
    *,
    username: str,
    admin: Admin,
    status: UserStatus,
    used_gib: int,
    limit_gib: int,
    devices: int,
) -> None:
    user = db.query(User).filter(User.username == username).one_or_none()
    if user is None:
        user = User(username=username)
        db.add(user)
        db.flush()
    user.admin_id = admin.id
    user.status = status
    user.used_traffic = used_gib * GIB
    user.data_limit = limit_gib * GIB
    user.concurrent_user_limit = devices
    user.data_limit_reset_strategy = UserDataLimitResetStrategy.no_reset
    user.expire = int((datetime.utcnow() + timedelta(days=30)).timestamp())
    user.note = "داده نمونه محیط توسعه"
    user.online_at = datetime.utcnow() if status == UserStatus.active else None
    if not user.proxies:
        user.proxies.append(
            Proxy(
                type=ProxyTypes.Shadowsocks,
                settings={
                    "password": f"dev-{username}-password",
                    "method": "chacha20-ietf-poly1305",
                },
            )
        )
    else:
        for proxy in user.proxies:
            if (
                proxy.type == ProxyTypes.Shadowsocks
                and proxy.settings.get("method") == "chacha20-poly1305"
            ):
                proxy.settings = {
                    **proxy.settings,
                    "method": "chacha20-ietf-poly1305",
                }


def main() -> None:
    require_isolated_database()
    with GetDB() as db:
        owner = ensure_admin(db, OWNER_USERNAME, OWNER_PASSWORD, "09120000001")
        plan_admin = ensure_admin(db, "plan_admin", ADMIN_PASSWORD, "09120000002")
        usage_admin = ensure_admin(db, "usage_admin", ADMIN_PASSWORD, "09120000003")
        frozen_admin = ensure_admin(db, "frozen_admin", ADMIN_PASSWORD, "09120000004")
        db.commit()

        admin_hierarchy.set_owner(db, OWNER_USERNAME)
        owner = crud.get_admin(db, username=OWNER_USERNAME)
        plan_admin = crud.get_admin(db, username="plan_admin")
        usage_admin = crud.get_admin(db, username="usage_admin")
        frozen_admin = crud.get_admin(db, username="frozen_admin")
        configure_admins(db, owner, plan_admin, usage_admin, frozen_admin)
        inbound, host = ensure_network(db)
        ensure_plans(db, owner, inbound, host)

        samples = [
            ("dev_ali_mobile", plan_admin, UserStatus.active, 4, 20, 1),
            ("dev_sara_home", plan_admin, UserStatus.active, 11, 50, 3),
            ("dev_hossein_test", plan_admin, UserStatus.disabled, 2, 20, 1),
            ("dev_niloofar_usage", usage_admin, UserStatus.active, 17, 40, 2),
            ("dev_owner_sample", owner, UserStatus.active, 8, 30, 2),
            ("dev_frozen_one", frozen_admin, UserStatus.active, 3, 10, 1),
        ]
        for username, admin, status, used_gib, limit_gib, devices in samples:
            ensure_user(
                db,
                username=username,
                admin=admin,
                status=status,
                used_gib=used_gib,
                limit_gib=limit_gib,
                devices=devices,
            )
        db.commit()

    print("Development data ready")
    print(f"Owner: {OWNER_USERNAME} / {OWNER_PASSWORD}")
    print(f"Admins: plan_admin, usage_admin, frozen_admin / {ADMIN_PASSWORD}")


if __name__ == "__main__":
    main()
