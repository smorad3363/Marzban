"""unify admin traffic credit and operation allowance

Revision ID: a41c8e7d5b92
Revises: d7f3a2c9e104
"""

from alembic import op
import sqlalchemy as sa


revision = "a41c8e7d5b92"
down_revision = "d7f3a2c9e104"
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}


def _indexes(table: str) -> list[dict]:
    return sa.inspect(op.get_bind()).get_indexes(table)


def _has_index_columns(table: str, columns: list[str]) -> bool:
    return any(list(index.get("column_names") or []) == columns for index in _indexes(table))


def upgrade() -> None:
    bind = op.get_bind()
    if "admin_traffic_warning_percent" not in _columns("marzhelp_admin_settings"):
        op.add_column(
            "marzhelp_admin_settings",
            sa.Column(
                "admin_traffic_warning_percent",
                sa.Integer(),
                server_default="80",
                nullable=False,
            ),
        )
    if "sudo_traffic_warning_percent" not in _columns("marzhelp_admin_settings"):
        op.add_column(
            "marzhelp_admin_settings",
            sa.Column(
                "sudo_traffic_warning_percent",
                sa.Integer(),
                server_default="80",
                nullable=False,
            ),
        )

    # InnoDB may already provide this index for the foreign key. Avoid a duplicate.
    if not _has_index_columns("user_usage_logs", ["user_id"]):
        op.create_index(
            "ix_user_usage_logs_user_id",
            "user_usage_logs",
            ["user_id"],
            unique=False,
        )

    # Allocated-credit mode becomes non-refundable. Seed its persistent counter
    # from current and deleted allocations without ever lowering an existing value.
    baseline = (
        "COALESCE((SELECT SUM(COALESCE(users.data_limit, users.used_traffic, 0)) "
        "FROM users WHERE users.admin_id = marzhelp_admin_settings.admin_id), 0) + "
        "COALESCE((SELECT SUM(COALESCE(marzhelp_deleted_users.allocated_traffic, "
        "marzhelp_deleted_users.used_traffic_total, 0)) FROM marzhelp_deleted_users "
        "WHERE marzhelp_deleted_users.admin_id = marzhelp_admin_settings.admin_id), 0)"
    )
    bind.execute(
        sa.text(
            "UPDATE marzhelp_admin_settings SET used_traffic = CASE "
            f"WHEN COALESCE(used_traffic, 0) > ({baseline}) "
            "THEN COALESCE(used_traffic, 0) "
            f"ELSE ({baseline}) END "
            "WHERE calculate_volume = 'created_traffic'"
        )
    )


def downgrade() -> None:
    index_names = {index["name"] for index in _indexes("user_usage_logs")}
    if "ix_user_usage_logs_user_id" in index_names:
        op.drop_index("ix_user_usage_logs_user_id", table_name="user_usage_logs")

    for column in (
        "sudo_traffic_warning_percent",
        "admin_traffic_warning_percent",
    ):
        if column in _columns("marzhelp_admin_settings"):
            op.drop_column("marzhelp_admin_settings", column)
