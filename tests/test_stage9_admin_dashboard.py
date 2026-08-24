from datetime import datetime, timezone
from pathlib import Path

import pytest
import sqlalchemy as sa
from pydantic import ValidationError
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models import Admin, MarzhelpAdminSettings, User
from app.models.admin import AdminModify, ManagedAdminCreate, MarzhelpAdminPolicy
from app.models.user import UserStatus
from app.utils import dashboard_metrics


@pytest.fixture()
def db(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'stage9.sqlite3'}")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def test_new_managed_admin_phone_is_optional_and_validated_when_present():
    values = dict(username="stage9", password="long-enough-password", policy=MarzhelpAdminPolicy())
    assert ManagedAdminCreate(**values).phone is None
    assert ManagedAdminCreate(**values, phone="   ").phone is None
    with pytest.raises(ValidationError):
        ManagedAdminCreate(**values, phone="+982100000000")
    assert ManagedAdminCreate(**values, phone="09395253363").phone == "09395253363"


def test_existing_admin_modify_remains_compatible_without_phone():
    change = AdminModify(telegram_id=42)
    assert "phone" not in change.model_fields_set


@pytest.mark.parametrize("mode", ["USED_TRAFFIC", "ALLOCATED_TRAFFIC", "USER_CREDIT"])
def test_admin_creation_contract_accepts_each_explicit_billing_mode(mode):
    policy = MarzhelpAdminPolicy(
        billing_mode=mode,
        max_users=10 if mode == "USER_CREDIT" else None,
        total_traffic=None if mode == "USER_CREDIT" else 1_000,
    )
    created = ManagedAdminCreate(
        username=f"admin-{mode.lower()}", password="long-enough-password", phone="09395253363", policy=policy
    )
    assert created.policy.billing_mode.value == mode


def test_dashboard_aggregate_week_boundary_modes_and_fixed_query_count(db):
    owner = Admin(username="owner", hashed_password="x", is_sudo=True, phone="1")
    seat = Admin(username="seat", hashed_password="x", phone="2")
    db.add_all([owner, seat])
    db.flush()
    db.add_all([
        MarzhelpAdminSettings(admin_id=owner.id, billing_mode="LEGACY_COMPAT"),
        MarzhelpAdminSettings(admin_id=seat.id, billing_mode="SEAT_CREDIT"),
    ])
    # Tehran Monday 00:00 is Sunday 20:30 UTC. These straddle that exact boundary.
    db.add_all([
        User(username="before", admin_id=owner.id, status=UserStatus.disabled, created_at=datetime(2026, 8, 16, 20, 29), used_traffic=3, data_limit=10),
        User(username="current", admin_id=seat.id, status=UserStatus.active, created_at=datetime(2026, 8, 16, 20, 30), online_at=datetime(2026, 8, 23, 10), used_traffic=7, data_limit=20),
    ])
    db.commit()
    count = 0
    def counted(*_args, **_kwargs):
        nonlocal count
        count += 1
    sa.event.listen(db.get_bind(), "before_cursor_execute", counted)
    result = dashboard_metrics.overview(
        db, owner, timezone_offset_minutes=210, now=datetime(2026, 8, 23, 12, tzinfo=timezone.utc)
    )
    sa.event.remove(db.get_bind(), "before_cursor_execute", counted)
    # Three aggregate statements plus bounded authorization/policy lookups; this
    # count is independent of the number of visible users and Admins.
    assert count <= 7
    assert result.total_users == 2
    assert result.active_users == 1
    assert result.disabled_users == 1
    assert result.online_users == 1
    assert result.current_used_traffic == 10
    assert result.allocated_quota == 30
    assert result.new_users.current == 1
    assert result.new_users.previous == 1
    assert result.new_users.change_percent == 0
    assert [metric.billing_mode for metric in result.billing_modes] == [
        "LEGACY_COMPAT", "SEAT_CREDIT", "USED_TRAFFIC", "ALLOCATED_TRAFFIC", "USER_CREDIT"
    ]
    assert next(metric for metric in result.billing_modes if metric.billing_mode == "SEAT_CREDIT").user_count == 1


def test_stage9_schema_and_ui_contracts():
    migration = Path("app/db/migrations/versions/6d4f2a9c8e10_add_stage9_admin_phone_dashboard_indexes.py").read_text(encoding="utf-8")
    admins = Path("app/dashboard/src/pages/Admins.tsx").read_text(encoding="utf-8")
    admin_form = Path("app/dashboard/src/components/AdminFormDrawer.tsx").read_text(encoding="utf-8")
    dashboard = Path("app/dashboard/src/components/DashboardOverview.tsx").read_text(encoding="utf-8")
    assert 'sa.String(32)' in migration
    assert 'ix_users_created_at_id' in migration
    assert 'ix_users_admin_status' in migration
    assert 'admins.discordWebhook' not in admins
    assert 'type="tel"' in admin_form
    assert 'billing_mode' in admin_form
    assert 'USER_CREDIT' in admin_form
    assert '/dashboard/overview?timezone_offset_minutes=' in dashboard
    assert 'aria-live="polite"' in dashboard
