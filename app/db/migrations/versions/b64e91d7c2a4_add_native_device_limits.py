"""add native device-limit settings, permissions, state and incidents

Revision ID: b64e91d7c2a4
Revises: f42c0e8a7d31
"""

from copy import deepcopy
import json
import secrets
from uuid import uuid4

from alembic import op
import sqlalchemy as sa


revision = "b64e91d7c2a4"
down_revision = "f42c0e8a7d31"
branch_labels = None
depends_on = None


DEFAULT_SUBSCRIPTION_MODES = (
    "limited_traffic_unlimited_devices",
    "unlimited_traffic_limited_devices",
    "limited_traffic_limited_devices",
)


def _columns(table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "view_full_client_ip" not in _columns("marzhelp_admin_settings"):
        op.add_column(
            "marzhelp_admin_settings",
            sa.Column("view_full_client_ip", sa.Boolean(), server_default=sa.false(), nullable=False),
        )

    missing_admin_ids = [
        row[0]
        for row in bind.execute(
            sa.text(
                "SELECT admins.id FROM admins "
                "LEFT JOIN marzhelp_admin_settings "
                "ON marzhelp_admin_settings.admin_id = admins.id "
                "WHERE marzhelp_admin_settings.admin_id IS NULL"
            )
        )
    ]
    if missing_admin_ids:
        op.bulk_insert(
            sa.table("marzhelp_admin_settings", sa.column("admin_id", sa.Integer())),
            [{"admin_id": admin_id} for admin_id in missing_admin_ids],
        )

    if "marzhelp_admin_allowed_subscription_modes" not in tables:
        modes = op.create_table(
            "marzhelp_admin_allowed_subscription_modes",
            sa.Column("admin_id", sa.Integer(), nullable=False),
            sa.Column("mode", sa.String(length=48), nullable=False),
            sa.ForeignKeyConstraint(
                ["admin_id"],
                ["marzhelp_admin_settings.admin_id"],
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("admin_id", "mode"),
        )
        admin_ids = [row[0] for row in bind.execute(sa.text("SELECT admin_id FROM marzhelp_admin_settings"))]
        if admin_ids:
            op.bulk_insert(
                modes,
                [
                    {"admin_id": admin_id, "mode": mode}
                    for admin_id in admin_ids
                    for mode in DEFAULT_SUBSCRIPTION_MODES
                ],
            )

    if "device_limit_settings" not in tables:
        settings = op.create_table(
            "device_limit_settings",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("enabled", sa.Boolean(), server_default=sa.false(), nullable=False),
            sa.Column("enforcement_mode", sa.String(length=24), server_default="hybrid", nullable=False),
            sa.Column("check_interval_seconds", sa.Integer(), server_default="60", nullable=False),
            sa.Column("active_window_seconds", sa.Integer(), server_default="300", nullable=False),
            sa.Column("hit_threshold", sa.Integer(), server_default="3", nullable=False),
            sa.Column("strike_reset_seconds", sa.Integer(), server_default="2592000", nullable=False),
            sa.Column("full_ip_retention_days", sa.Integer(), server_default="7", nullable=False),
            sa.Column("incident_retention_days", sa.Integer(), server_default="90", nullable=False),
            sa.Column("audit_retention_days", sa.Integer(), server_default="180", nullable=False),
            sa.Column("auto_delete_enabled", sa.Boolean(), server_default=sa.false(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.CheckConstraint("id = 1", name="ck_device_limit_settings_singleton"),
        )
        op.bulk_insert(
            settings,
            [{
                "id": 1,
                "enabled": False,
                "enforcement_mode": "hybrid",
                "check_interval_seconds": 60,
                "active_window_seconds": 300,
                "hit_threshold": 3,
                "strike_reset_seconds": 2592000,
                "full_ip_retention_days": 7,
                "incident_retention_days": 90,
                "audit_retention_days": 180,
                "auto_delete_enabled": False,
            }],
        )

    if "device_limit_penalty_stages" not in tables:
        stages = op.create_table(
            "device_limit_penalty_stages",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("violation_count", sa.Integer(), nullable=False),
            sa.Column("action", sa.String(length=32), nullable=False),
            sa.Column("duration_seconds", sa.Integer(), nullable=True),
            sa.Column("enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("violation_count", name="uq_device_limit_stage_violation"),
        )
        op.bulk_insert(
            stages,
            [
                {"violation_count": 1, "action": "warn", "duration_seconds": None, "enabled": True},
                {"violation_count": 2, "action": "temporary_disable", "duration_seconds": 300, "enabled": True},
                {"violation_count": 3, "action": "temporary_disable", "duration_seconds": 900, "enabled": True},
                {"violation_count": 4, "action": "temporary_disable", "duration_seconds": 3600, "enabled": True},
                {"violation_count": 5, "action": "permanent_disable", "duration_seconds": None, "enabled": True},
            ],
        )

    created_device_slots = "device_slots" not in tables
    if created_device_slots:
        device_slots = op.create_table(
            "device_slots",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("slot_index", sa.Integer(), nullable=False),
            sa.Column("label", sa.String(length=64), nullable=True),
            sa.Column("credentials", sa.JSON(), nullable=False),
            sa.Column("token_version", sa.String(length=36), nullable=False),
            sa.Column("enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.Column("last_seen_at", sa.DateTime(), nullable=True),
            sa.Column("last_ip", sa.String(length=64), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "slot_index", name="uq_device_slots_user_index"),
            sa.CheckConstraint("slot_index >= 1", name="ck_device_slots_index_positive"),
        )
        op.create_index("ix_device_slots_user_enabled", "device_slots", ["user_id", "enabled"], unique=False)

        proxy_rows = bind.execute(
            sa.text(
                "SELECT users.id, users.username, users.concurrent_user_limit, "
                "proxies.type, proxies.settings FROM users "
                "JOIN proxies ON proxies.user_id = users.id "
                "WHERE users.concurrent_user_limit IS NOT NULL "
                "ORDER BY users.id"
            )
        ).mappings()
        users: dict[int, dict] = {}
        for row in proxy_rows:
            entry = users.setdefault(
                row["id"],
                {
                    "username": row["username"],
                    "limit": max(int(row["concurrent_user_limit"] or 0), 0),
                    "credentials": {},
                },
            )
            raw_settings = row["settings"]
            if isinstance(raw_settings, str):
                raw_settings = json.loads(raw_settings)
            entry["credentials"][str(row["type"]).lower()] = raw_settings

        batch = []
        for user_id, entry in users.items():
            for slot_index in range(1, entry["limit"] + 1):
                credentials = deepcopy(entry["credentials"])
                if slot_index > 1:
                    for proxy_settings in credentials.values():
                        if "id" in proxy_settings:
                            proxy_settings["id"] = str(uuid4())
                        elif "password" in proxy_settings:
                            proxy_settings["password"] = secrets.token_urlsafe(24)
                batch.append(
                    {
                        "user_id": user_id,
                        "slot_index": slot_index,
                        "label": f"Device {slot_index}",
                        "credentials": credentials,
                        "token_version": str(uuid4()),
                        "enabled": True,
                    }
                )
                if len(batch) >= 500:
                    op.bulk_insert(device_slots, batch)
                    batch.clear()
        if batch:
            op.bulk_insert(device_slots, batch)

    if "device_limit_user_states" not in tables:
        op.create_table(
            "device_limit_user_states",
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("violation_count", sa.Integer(), server_default="0", nullable=False),
            sa.Column("current_stage", sa.Integer(), server_default="0", nullable=False),
            sa.Column("penalty_status", sa.String(length=32), server_default="clear", nullable=False),
            sa.Column("blocked_until", sa.DateTime(), nullable=True),
            sa.Column("status_before_penalty", sa.String(length=24), nullable=True),
            sa.Column("last_violation_at", sa.DateTime(), nullable=True),
            sa.Column("last_seen_at", sa.DateTime(), nullable=True),
            sa.Column("active_ip_count", sa.Integer(), server_default="0", nullable=False),
            sa.Column("last_reason", sa.Text(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("user_id"),
        )
        op.create_index(
            "ix_device_limit_state_penalty_until",
            "device_limit_user_states",
            ["penalty_status", "blocked_until"],
            unique=False,
        )

    if "device_limit_incidents" not in tables:
        op.create_table(
            "device_limit_incidents",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("admin_id", sa.Integer(), nullable=True),
            sa.Column("username", sa.String(length=34), nullable=False),
            sa.Column("stage", sa.Integer(), nullable=False),
            sa.Column("action", sa.String(length=32), nullable=False),
            sa.Column("configured_limit", sa.Integer(), nullable=False),
            sa.Column("observed_count", sa.Integer(), nullable=False),
            sa.Column("ip_addresses", sa.JSON(), nullable=True),
            sa.Column("source_nodes", sa.JSON(), nullable=True),
            sa.Column("reason", sa.Text(), nullable=False),
            sa.Column("resolved_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_device_limit_incidents_user_created",
            "device_limit_incidents",
            ["user_id", "created_at"],
            unique=False,
        )
        op.create_index(
            "ix_device_limit_incidents_admin_created",
            "device_limit_incidents",
            ["admin_id", "created_at"],
            unique=False,
        )
        op.create_index(
            "ix_device_limit_incidents_created",
            "device_limit_incidents",
            ["created_at"],
            unique=False,
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    for table in (
        "device_limit_incidents",
        "device_limit_user_states",
        "device_slots",
        "device_limit_penalty_stages",
        "device_limit_settings",
        "marzhelp_admin_allowed_subscription_modes",
    ):
        if table in tables:
            op.drop_table(table)
    if "view_full_client_ip" in _columns("marzhelp_admin_settings"):
        op.drop_column("marzhelp_admin_settings", "view_full_client_ip")
