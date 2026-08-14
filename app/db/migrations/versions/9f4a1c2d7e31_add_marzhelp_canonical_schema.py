"""add Marzhelp canonical schema

Revision ID: 9f4a1c2d7e31
Revises: 63fbd07b9f14
"""

from alembic import op
import sqlalchemy as sa


revision = "9f4a1c2d7e31"
down_revision = "63fbd07b9f14"
branch_labels = None
depends_on = None


def _table_exists(name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(name)


def _columns(name: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(name)}


def _index_exists(table: str, name: str) -> bool:
    return any(index["name"] == name for index in sa.inspect(op.get_bind()).get_indexes(table))


def _seed_metadata() -> None:
    table = sa.table(
        "marzhelp_metadata",
        sa.column("key", sa.String(64)),
        sa.column("value", sa.String(255)),
        sa.column("updated_at", sa.DateTime()),
    )
    bind = op.get_bind()
    values = {
        "source_id": "smorad3363-marzban",
        "schema_version": "1",
        "minimum_marzhelp_version": "2",
        "legacy_enforcement_status": "obsolete",
    }
    for key, value in values.items():
        existing = bind.execute(sa.select(table.c.key).where(table.c.key == key)).first()
        if existing:
            bind.execute(table.update().where(table.c.key == key).values(value=value, updated_at=sa.func.now()))
        else:
            bind.execute(table.insert().values(key=key, value=value, updated_at=sa.func.now()))


def upgrade() -> None:
    if not _table_exists("marzhelp_metadata"):
        op.create_table(
            "marzhelp_metadata",
            sa.Column("key", sa.String(length=64), nullable=False),
            sa.Column("value", sa.String(length=255), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("key"),
        )

    if not _table_exists("marzhelp_admin_settings"):
        op.create_table(
            "marzhelp_admin_settings",
            sa.Column("admin_id", sa.Integer(), nullable=False),
            sa.Column("total_traffic", sa.BigInteger(), nullable=True),
            sa.Column("used_traffic", sa.BigInteger(), server_default="0", nullable=False),
            sa.Column("expiry_date", sa.Date(), nullable=True),
            sa.Column("status", sa.JSON(), nullable=True),
            sa.Column("user_limit", sa.BigInteger(), nullable=True),
            sa.Column("max_user_duration_days", sa.Integer(), nullable=True),
            sa.Column("hashed_password_before", sa.String(length=255), nullable=True),
            sa.Column("last_expiry_notification", sa.DateTime(), nullable=True),
            sa.Column("last_traffic_notification", sa.Integer(), nullable=True),
            sa.Column("last_traffic_notify", sa.Integer(), nullable=True),
            sa.Column("calculate_volume", sa.String(length=50), server_default="used_traffic", nullable=False),
            sa.Column("prevent_user_creation", sa.Boolean(), server_default=sa.false(), nullable=False),
            sa.Column("prevent_user_deletion", sa.Boolean(), server_default=sa.false(), nullable=False),
            sa.Column("prevent_user_reset", sa.Boolean(), server_default=sa.false(), nullable=False),
            sa.Column("prevent_revoke_subscription", sa.Boolean(), server_default=sa.false(), nullable=False),
            sa.Column("prevent_unlimited_traffic", sa.Boolean(), server_default=sa.false(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["admin_id"], ["admins.id"]),
            sa.PrimaryKeyConstraint("admin_id"),
        )

    if not _table_exists("marzhelp_user_states"):
        op.create_table(
            "marzhelp_user_states",
            sa.Column("user_id", sa.BigInteger(), nullable=False),
            sa.Column("username", sa.String(length=50), nullable=True),
            sa.Column("lang", sa.String(length=10), nullable=True),
            sa.Column("state", sa.String(length=50), nullable=True),
            sa.Column("admin_id", sa.Integer(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("data", sa.Text(), nullable=True),
            sa.Column("message_id", sa.Integer(), nullable=True),
            sa.Column("template_index", sa.Integer(), server_default="0", nullable=False),
            sa.PrimaryKeyConstraint("user_id"),
        )

    if not _table_exists("marzhelp_user_temporaries"):
        op.create_table(
            "marzhelp_user_temporaries",
            sa.Column("user_id", sa.BigInteger(), nullable=False),
            sa.Column("user_key", sa.String(length=50), nullable=False),
            sa.Column("value", sa.Text(), nullable=True),
            sa.PrimaryKeyConstraint("user_id", "user_key"),
        )

    if not _table_exists("marzhelp_admin_usage"):
        op.create_table(
            "marzhelp_admin_usage",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("admin_id", sa.Integer(), nullable=False),
            sa.Column("used_traffic_gb", sa.Numeric(precision=18, scale=2), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["admin_id"], ["admins.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_marzhelp_admin_usage_admin_created", "marzhelp_admin_usage", ["admin_id", "created_at"])

    if not _table_exists("marzhelp_limits"):
        op.create_table(
            "marzhelp_limits",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("type", sa.String(length=16), nullable=False),
            sa.Column("admin_id", sa.Integer(), nullable=False),
            sa.Column("inbound_tag", sa.String(length=255), nullable=False),
            sa.ForeignKeyConstraint(["admin_id"], ["admins.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("type", "admin_id", "inbound_tag", name="uq_marzhelp_limit"),
        )
        op.create_index("ix_marzhelp_limits_admin_id", "marzhelp_limits", ["admin_id"])

    if not _table_exists("marzhelp_runtime_settings"):
        op.create_table(
            "marzhelp_runtime_settings",
            sa.Column("setting_name", sa.String(length=64), nullable=False),
            sa.Column("setting_value", sa.String(length=255), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("setting_name"),
        )

    if not _table_exists("marzhelp_deleted_users"):
        op.create_table(
            "marzhelp_deleted_users",
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("admin_id", sa.Integer(), nullable=False),
            sa.Column("username", sa.String(length=34), nullable=True),
            sa.Column("used_traffic_total", sa.BigInteger(), server_default="0", nullable=False),
            sa.Column("allocated_traffic", sa.BigInteger(), nullable=True),
            sa.Column("refunded_traffic", sa.BigInteger(), server_default="0", nullable=False),
            sa.Column("deleted_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("user_id"),
        )
    else:
        existing = _columns("marzhelp_deleted_users")
        if "username" not in existing:
            op.add_column("marzhelp_deleted_users", sa.Column("username", sa.String(length=34), nullable=True))
        if "refunded_traffic" not in existing:
            op.add_column(
                "marzhelp_deleted_users",
                sa.Column("refunded_traffic", sa.BigInteger(), server_default="0", nullable=False),
            )
    if not _index_exists("marzhelp_deleted_users", "ix_marzhelp_deleted_users_admin_deleted"):
        op.create_index(
            "ix_marzhelp_deleted_users_admin_deleted",
            "marzhelp_deleted_users",
            ["admin_id", "deleted_at"],
        )

    if not _table_exists("marzhelp_accounting_transactions"):
        op.create_table(
            "marzhelp_accounting_transactions",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("operation_key", sa.String(length=128), nullable=False),
            sa.Column("operation_type", sa.String(length=32), nullable=False),
            sa.Column("admin_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("username", sa.String(length=34), nullable=True),
            sa.Column("traffic_delta", sa.BigInteger(), server_default="0", nullable=False),
            sa.Column("allowance_delta", sa.Integer(), server_default="0", nullable=False),
            sa.Column("details", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("operation_key", name="uq_marzhelp_accounting_operation_key"),
        )
        op.create_index(
            "ix_marzhelp_accounting_admin_created",
            "marzhelp_accounting_transactions",
            ["admin_id", "created_at"],
        )

    bind = op.get_bind()
    if bind.dialect.name in {"mysql", "mariadb"}:
        # Older MarzHelp releases installed database triggers/events directly.
        # They bypass the transactional Python policy and must be retired by
        # this Marzban-owned migration before the compatibility marker is set.
        legacy_triggers = (
            "set_default_status",
            "marzhelp_capture_user_delete",
            "marzhelp_enforce_user_insert",
            "marzhelp_enforce_user_update",
            "marzhelp_enforce_user_delete",
            "prevent_user_creation",
            "admin_delete",
            "prevent_User_Reset_Usage",
            "prevent_revoke_subscription",
            "prevent_unlimited_traffic",
            "user_creation_traffic",
            "user_update_traffic",
            "prevent_insert_traffic",
            "prevent_update_traffic",
            "cron_prevent_user_creation",
            "save_user_traffic_used",
            "save_user_traffic_reseted",
        )
        for trigger in legacy_triggers:
            op.execute(sa.text(f"DROP TRIGGER IF EXISTS `{trigger}`"))
        op.execute(sa.text("DROP EVENT IF EXISTS `manage_inbound_limits`"))
        op.execute(sa.text("DROP EVENT IF EXISTS `marzhelp_manage_inbound_limits`"))

        if _table_exists("marzhelp_admin_enforcement"):
            op.execute(
                sa.text(
                    """
                    INSERT INTO marzhelp_admin_settings
                        (admin_id, total_traffic, user_limit, calculate_volume,
                         prevent_user_creation, prevent_user_deletion,
                         prevent_user_reset, prevent_revoke_subscription,
                         prevent_unlimited_traffic)
                    SELECT e.admin_id, e.traffic_limit, e.user_limit, e.traffic_mode,
                           e.prevent_user_creation, e.prevent_user_deletion,
                           e.prevent_user_reset, e.prevent_revoke_subscription,
                           e.prevent_unlimited_traffic
                      FROM marzhelp_admin_enforcement e
                      INNER JOIN admins a ON a.id = e.admin_id
                    ON DUPLICATE KEY UPDATE admin_id = VALUES(admin_id)
                    """
                )
            )

        if _table_exists("user_deletions"):
            op.execute(
                sa.text(
                    """
                    INSERT INTO marzhelp_deleted_users
                        (user_id, admin_id, used_traffic_total, allocated_traffic,
                         refunded_traffic, deleted_at)
                    SELECT user_id, admin_id,
                           SUM(COALESCE(used_traffic, 0) + COALESCE(reseted_usage, 0)),
                           NULL, 0, MAX(COALESCE(deleted_at, CURRENT_TIMESTAMP))
                      FROM user_deletions
                     WHERE user_id IS NOT NULL AND admin_id IS NOT NULL
                     GROUP BY user_id, admin_id
                    ON DUPLICATE KEY UPDATE
                        used_traffic_total = GREATEST(
                            marzhelp_deleted_users.used_traffic_total,
                            VALUES(used_traffic_total)
                        ),
                        deleted_at = GREATEST(
                            marzhelp_deleted_users.deleted_at,
                            VALUES(deleted_at)
                        )
                    """
                )
            )

    runtime = sa.table(
        "marzhelp_runtime_settings",
        sa.column("setting_name", sa.String(64)),
        sa.column("setting_value", sa.String(255)),
        sa.column("updated_at", sa.DateTime()),
    )
    if not bind.execute(
        sa.select(runtime.c.setting_name).where(runtime.c.setting_name == "inbound_sync_interval")
    ).first():
        bind.execute(
            runtime.insert().values(
                setting_name="inbound_sync_interval",
                setting_value="10",
                updated_at=sa.func.now(),
            )
        )

    _seed_metadata()


def downgrade() -> None:
    # Existing Marzhelp deployments may contain production data in these tables.
    # Downgrade intentionally removes only the new accounting/schema metadata.
    if _table_exists("marzhelp_accounting_transactions"):
        if _index_exists("marzhelp_accounting_transactions", "ix_marzhelp_accounting_admin_created"):
            op.drop_index(
                "ix_marzhelp_accounting_admin_created",
                table_name="marzhelp_accounting_transactions",
            )
        op.drop_table("marzhelp_accounting_transactions")
    for table_name in (
        "marzhelp_admin_usage",
        "marzhelp_user_temporaries",
        "marzhelp_user_states",
        "marzhelp_admin_settings",
        "marzhelp_metadata",
    ):
        if _table_exists(table_name):
            op.drop_table(table_name)
