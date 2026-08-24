"""Add delegated Admin creation quotas, Trial reset baseline, and branding.

Revision ID: 8b7d3e5f1a24
Revises: 4c8e1a7d9b30
"""

from alembic import op
import sqlalchemy as sa


revision = "8b7d3e5f1a24"
down_revision = "4c8e1a7d9b30"
branch_labels = None
depends_on = None


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _columns(table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}


def _indexes(table: str) -> set[str]:
    return {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table)}


def upgrade() -> None:
    tables = _tables()
    if "admins" in tables:
        columns = _columns("admins")
        if "dashboard_theme" not in columns:
            op.add_column(
                "admins",
                sa.Column(
                    "dashboard_theme",
                    sa.String(32),
                    nullable=False,
                    server_default="heisenberg",
                ),
            )
        if "logo_filename" not in columns:
            op.add_column("admins", sa.Column("logo_filename", sa.String(255), nullable=True))

    if "marzhelp_admin_settings" not in tables:
        return
    columns = _columns("marzhelp_admin_settings")
    additions = (
        ("trial_quota_limit", sa.BigInteger(), "0"),
        ("can_create_admins", sa.Boolean(), "0"),
        ("can_delegate_admin_creation", sa.Boolean(), "0"),
        ("can_create_allocated_children", sa.Boolean(), "1"),
        ("admin_creation_limit", sa.BigInteger(), None),
        ("admin_creations_used", sa.BigInteger(), "0"),
        ("delegated_admin_creation_limit", sa.BigInteger(), "0"),
    )
    for name, column_type, default in additions:
        if name in columns:
            continue
        op.add_column(
            "marzhelp_admin_settings",
            sa.Column(
                name,
                column_type,
                nullable=default is None,
                server_default=default,
            ),
        )

    columns = _columns("marzhelp_admin_settings")
    if {"trial_quota_limit", "trial_quota", "trials_used"} <= columns:
        op.execute(
            sa.text(
                "UPDATE marzhelp_admin_settings "
                "SET trial_quota_limit = COALESCE(trial_quota, 0) + COALESCE(trials_used, 0)"
            )
        )
    if (
        {"admins", "admin_roles", "marzhelp_admin_settings"} <= tables
        and {"can_create_admins", "can_delegate_admin_creation"} <= columns
    ):
        op.execute(
            sa.text(
                "UPDATE marzhelp_admin_settings SET "
                "can_create_admins = 1, can_delegate_admin_creation = 1 "
                "WHERE admin_id IN ("
                "SELECT admins.id FROM admins "
                "JOIN admin_roles ON admin_roles.id = admins.role_id "
                "WHERE admin_roles.code IN ('OWNER', 'SUPER_ADMIN')"
                ")"
            )
        )
    indexes = _indexes("marzhelp_admin_settings")
    if "ix_marzhelp_admin_settings_billing_admin" not in indexes:
        op.create_index(
            "ix_marzhelp_admin_settings_billing_admin",
            "marzhelp_admin_settings",
            ["billing_mode", "admin_id"],
        )
    if "ix_marzhelp_admin_settings_status_admin" not in indexes:
        op.create_index(
            "ix_marzhelp_admin_settings_status_admin",
            "marzhelp_admin_settings",
            ["account_status_id", "admin_id"],
        )


def downgrade() -> None:
    tables = _tables()
    if "marzhelp_admin_settings" in tables:
        indexes = _indexes("marzhelp_admin_settings")
        for name in (
            "ix_marzhelp_admin_settings_status_admin",
            "ix_marzhelp_admin_settings_billing_admin",
        ):
            if name in indexes:
                op.drop_index(name, table_name="marzhelp_admin_settings")
                indexes.remove(name)
        columns = _columns("marzhelp_admin_settings")
        for name in (
            "delegated_admin_creation_limit",
            "admin_creations_used",
            "admin_creation_limit",
            "can_create_allocated_children",
            "can_delegate_admin_creation",
            "can_create_admins",
            "trial_quota_limit",
        ):
            if name in columns:
                op.drop_column("marzhelp_admin_settings", name)
                columns.remove(name)
    if "admins" in tables:
        columns = _columns("admins")
        for name in ("logo_filename", "dashboard_theme"):
            if name in columns:
                op.drop_column("admins", name)
                columns.remove(name)
