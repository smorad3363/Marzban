"""add Heisenberg capability, client observation and quota accounting fields

Revision ID: d7f3a2c9e104
Revises: b64e91d7c2a4
"""

from alembic import op
import sqlalchemy as sa


revision = "d7f3a2c9e104"
down_revision = "b64e91d7c2a4"
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}


def _indexes(table: str) -> set[str]:
    return {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table)}


def _has_index_columns(table: str, columns: list[str]) -> bool:
    return any(
        list(index.get("column_names") or []) == columns
        for index in sa.inspect(op.get_bind()).get_indexes(table)
    )


def _add(table: str, column: sa.Column) -> None:
    if column.name not in _columns(table):
        op.add_column(table, column)


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())

    _add("device_limit_settings", sa.Column("device_slots_enabled", sa.Boolean(), server_default=sa.true(), nullable=False))
    _add("device_limit_settings", sa.Column("ip_detection_enabled", sa.Boolean(), server_default=sa.true(), nullable=False))
    _add("device_limit_settings", sa.Column("client_fingerprint_enabled", sa.Boolean(), server_default=sa.false(), nullable=False))
    _add("device_limit_settings", sa.Column("min_successful_connections", sa.Integer(), server_default="3", nullable=False))
    _add("device_limit_settings", sa.Column("handoff_grace_seconds", sa.Integer(), server_default="90", nullable=False))
    _add("device_limit_settings", sa.Column("warning_auto_delete_seconds", sa.Integer(), server_default="86400", nullable=False))
    bind.execute(
        sa.text(
            "UPDATE device_limit_settings SET "
            "device_slots_enabled = true, "
            "ip_detection_enabled = CASE WHEN enforcement_mode = 'slots' THEN false ELSE true END, "
            "client_fingerprint_enabled = false, "
            "min_successful_connections = hit_threshold"
        )
    )
    _add("device_limit_user_states", sa.Column("pending_handoff_started_at", sa.DateTime(), nullable=True))
    _add("device_limit_user_states", sa.Column("pending_ip_addresses", sa.JSON(), nullable=True))
    _add("device_limit_user_states", sa.Column("pending_source_nodes", sa.JSON(), nullable=True))
    _add("device_limit_user_states", sa.Column("pending_risk_score", sa.Integer(), nullable=True))
    _add("device_limit_user_states", sa.Column("pending_last_fresh_at", sa.DateTime(), nullable=True))

    _add("device_limit_incidents", sa.Column("event_state", sa.String(length=32), server_default="confirmed_violation", nullable=False))
    _add("device_limit_incidents", sa.Column("risk_score", sa.Integer(), nullable=True))
    _add("device_limit_incidents", sa.Column("signal_summary", sa.JSON(), nullable=True))
    _add("device_limit_incidents", sa.Column("expires_at", sa.DateTime(), nullable=True))
    bind.execute(
        sa.text(
            "UPDATE device_limit_incidents SET event_state = CASE "
            "WHEN resolved_at IS NOT NULL THEN 'resolved' "
            "WHEN action = 'warn' THEN 'warning' "
            "WHEN action = 'temporary_disable' THEN 'temporarily_disabled' "
            "WHEN action IN ('permanent_disable', 'delete') THEN 'permanently_disabled' "
            "ELSE 'confirmed_violation' END"
        )
    )
    if "ix_device_limit_incidents_warning_expiry" not in _indexes("device_limit_incidents"):
        op.create_index(
            "ix_device_limit_incidents_warning_expiry",
            "device_limit_incidents",
            ["event_state", "resolved_at", "expires_at"],
            unique=False,
        )

    if "device_client_observations" not in tables:
        op.create_table(
            "device_client_observations",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("slot_id", sa.Integer(), nullable=True),
            sa.Column("slot_key", sa.Integer(), server_default="0", nullable=False),
            sa.Column("normalized_identity", sa.String(length=64), nullable=False),
            sa.Column("client_name", sa.String(length=64), server_default="Unknown", nullable=False),
            sa.Column("client_version", sa.String(length=64), nullable=True),
            sa.Column("platform", sa.String(length=64), nullable=True),
            sa.Column("os_token", sa.String(length=128), nullable=True),
            sa.Column("network_stack", sa.String(length=128), nullable=True),
            sa.Column("raw_user_agent", sa.String(length=512), nullable=False),
            sa.Column("first_seen_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("last_seen_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("seen_count", sa.BigInteger(), server_default="1", nullable=False),
            sa.ForeignKeyConstraint(["slot_id"], ["device_slots.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "user_id",
                "slot_key",
                "normalized_identity",
                name="uq_device_client_observation_identity",
            ),
        )
        op.create_index(
            "ix_device_client_observation_user_slot_seen",
            "device_client_observations",
            ["user_id", "slot_key", "last_seen_at"],
            unique=False,
        )
        op.create_index(
            "ix_device_client_observation_user_seen",
            "device_client_observations",
            ["user_id", "last_seen_at"],
            unique=False,
        )
    elif "ix_device_client_observation_user_slot_seen" not in _indexes("device_client_observations"):
        op.create_index(
            "ix_device_client_observation_user_slot_seen",
            "device_client_observations",
            ["user_id", "slot_key", "last_seen_at"],
            unique=False,
        )
    if "ix_device_client_observation_user_seen" not in _indexes("device_client_observations"):
        op.create_index(
            "ix_device_client_observation_user_seen",
            "device_client_observations",
            ["user_id", "last_seen_at"],
            unique=False,
        )
    # InnoDB usually creates a supporting slot_id index for the foreign key.
    # Create one only when the backend did not, avoiding a redundant index.
    if not _has_index_columns("device_client_observations", ["slot_id"]):
        op.create_index(
            "ix_device_client_observation_slot",
            "device_client_observations",
            ["slot_id"],
            unique=False,
        )

    _add("marzhelp_admin_settings", sa.Column("user_count_used", sa.BigInteger(), server_default="0", nullable=False))
    _add("marzhelp_admin_settings", sa.Column("device_capacity_limit", sa.BigInteger(), nullable=True))
    _add("marzhelp_admin_settings", sa.Column("provisioning_volume_limit", sa.BigInteger(), nullable=True))
    _add("marzhelp_admin_settings", sa.Column("provisioning_volume_used", sa.BigInteger(), server_default="0", nullable=False))
    _add("marzhelp_admin_settings", sa.Column("renewal_limit", sa.BigInteger(), nullable=True))
    _add("marzhelp_admin_settings", sa.Column("renewals_used", sa.BigInteger(), server_default="0", nullable=False))
    bind.execute(
        sa.text(
            "UPDATE marzhelp_admin_settings SET "
            "device_capacity_limit = max_users, "
            "user_count_used = (SELECT COUNT(*) FROM users WHERE users.admin_id = marzhelp_admin_settings.admin_id), "
            "provisioning_volume_used = COALESCE((SELECT SUM(COALESCE(users.data_limit, 0)) "
            "FROM users WHERE users.admin_id = marzhelp_admin_settings.admin_id), 0)"
        )
    )

    _add("marzhelp_accounting_transactions", sa.Column("volume_delta", sa.BigInteger(), server_default="0", nullable=False))
    _add("marzhelp_accounting_transactions", sa.Column("renewal_delta", sa.Integer(), server_default="0", nullable=False))
    _add("marzhelp_accounting_transactions", sa.Column("result", sa.String(length=16), server_default="consumed", nullable=False))

    # Recover legacy rows that reference an owner no longer present. NULL owner
    # is the existing sudo-manageable convention.
    bind.execute(
        sa.text(
            "UPDATE users SET admin_id = NULL WHERE admin_id IS NOT NULL "
            "AND NOT EXISTS (SELECT 1 FROM admins WHERE admins.id = users.admin_id)"
        )
    )


def downgrade() -> None:
    if "device_client_observations" in set(sa.inspect(op.get_bind()).get_table_names()):
        op.drop_table("device_client_observations")

    for column in (
        "result",
        "renewal_delta",
        "volume_delta",
    ):
        if column in _columns("marzhelp_accounting_transactions"):
            op.drop_column("marzhelp_accounting_transactions", column)

    for column in (
        "renewals_used",
        "renewal_limit",
        "provisioning_volume_used",
        "provisioning_volume_limit",
        "device_capacity_limit",
        "user_count_used",
    ):
        if column in _columns("marzhelp_admin_settings"):
            op.drop_column("marzhelp_admin_settings", column)

    if "ix_device_limit_incidents_warning_expiry" in _indexes("device_limit_incidents"):
        op.drop_index(
            "ix_device_limit_incidents_warning_expiry",
            table_name="device_limit_incidents",
        )

    for column in ("expires_at", "signal_summary", "risk_score", "event_state"):
        if column in _columns("device_limit_incidents"):
            op.drop_column("device_limit_incidents", column)

    for column in (
        "pending_last_fresh_at",
        "pending_risk_score",
        "pending_source_nodes",
        "pending_ip_addresses",
        "pending_handoff_started_at",
    ):
        if column in _columns("device_limit_user_states"):
            op.drop_column("device_limit_user_states", column)

    for column in (
        "warning_auto_delete_seconds",
        "handoff_grace_seconds",
        "min_successful_connections",
        "client_fingerprint_enabled",
        "ip_detection_enabled",
        "device_slots_enabled",
    ):
        if column in _columns("device_limit_settings"):
            op.drop_column("device_limit_settings", column)
