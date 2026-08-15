"""add admin inbound and weighted user limits

Revision ID: f42c0e8a7d31
Revises: d71a9c4e2b60
"""

from alembic import op
import sqlalchemy as sa


revision = "f42c0e8a7d31"
down_revision = "d71a9c4e2b60"
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = inspector.get_table_names()

    if "concurrent_user_limit" not in _columns("users"):
        op.add_column("users", sa.Column("concurrent_user_limit", sa.Integer(), nullable=True))

    settings_columns = _columns("marzhelp_admin_settings")
    if "capacity_used" not in settings_columns:
        op.add_column(
            "marzhelp_admin_settings",
            sa.Column("capacity_used", sa.BigInteger(), server_default="0", nullable=False),
        )
    if "all_inbounds" not in settings_columns:
        op.add_column(
            "marzhelp_admin_settings",
            sa.Column("all_inbounds", sa.Boolean(), server_default=sa.true(), nullable=False),
        )
    if "all_user_limits" not in settings_columns:
        op.add_column(
            "marzhelp_admin_settings",
            sa.Column("all_user_limits", sa.Boolean(), server_default=sa.true(), nullable=False),
        )

    op.execute(
        sa.text(
            """
            UPDATE marzhelp_admin_settings
               SET capacity_used = (
                   SELECT COALESCE(SUM(
                       CASE
                           WHEN users.concurrent_user_limit IS NULL
                                OR users.concurrent_user_limit < 1 THEN 1
                           ELSE users.concurrent_user_limit
                       END
                   ), 0)
                     FROM users
                    WHERE users.admin_id = marzhelp_admin_settings.admin_id
               )
            """
        )
    )

    if "marzhelp_admin_allowed_inbounds" not in tables:
        op.create_table(
            "marzhelp_admin_allowed_inbounds",
            sa.Column("admin_id", sa.Integer(), nullable=False),
            sa.Column("inbound_tag", sa.String(length=256), nullable=False),
            sa.ForeignKeyConstraint(
                ["admin_id"],
                ["marzhelp_admin_settings.admin_id"],
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("admin_id", "inbound_tag"),
        )

    if "marzhelp_admin_allowed_user_limits" not in tables:
        op.create_table(
            "marzhelp_admin_allowed_user_limits",
            sa.Column("admin_id", sa.Integer(), nullable=False),
            sa.Column("concurrent_user_limit", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(
                ["admin_id"],
                ["marzhelp_admin_settings.admin_id"],
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("admin_id", "concurrent_user_limit"),
            sa.CheckConstraint("concurrent_user_limit >= 1", name="ck_admin_allowed_user_limit_positive"),
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = inspector.get_table_names()
    if "marzhelp_admin_allowed_user_limits" in tables:
        op.drop_table("marzhelp_admin_allowed_user_limits")
    if "marzhelp_admin_allowed_inbounds" in tables:
        op.drop_table("marzhelp_admin_allowed_inbounds")
    settings_columns = _columns("marzhelp_admin_settings")
    if "all_user_limits" in settings_columns:
        op.drop_column("marzhelp_admin_settings", "all_user_limits")
    if "all_inbounds" in settings_columns:
        op.drop_column("marzhelp_admin_settings", "all_inbounds")
    if "capacity_used" in settings_columns:
        op.drop_column("marzhelp_admin_settings", "capacity_used")
    if "concurrent_user_limit" in _columns("users"):
        op.drop_column("users", "concurrent_user_limit")
