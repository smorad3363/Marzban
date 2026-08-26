"""Add monetary wallets, reseller prices, and immutable money ledger.

Revision ID: c2f4a8d6e913
Revises: 8b7d3e5f1a24
"""

from alembic import op
import sqlalchemy as sa


revision = "c2f4a8d6e913"
down_revision = "8b7d3e5f1a24"
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
    if "marzhelp_admin_settings" in tables:
        columns = _columns("marzhelp_admin_settings")
        additions = (
            ("money_billing_enabled", sa.Boolean(), False, "0"),
            ("money_balance_toman", sa.BigInteger(), False, "0"),
            ("used_traffic_price_per_gib_toman", sa.BigInteger(), True, None),
            ("usage_billing_remainder", sa.BigInteger(), False, "0"),
        )
        for name, column_type, nullable, default in additions:
            if name not in columns:
                op.add_column(
                    "marzhelp_admin_settings",
                    sa.Column(name, column_type, nullable=nullable, server_default=default),
                )

    if "admin_user_plan_versions" in tables:
        columns = _columns("admin_user_plan_versions")
        if "price_toman" not in columns:
            op.add_column(
                "admin_user_plan_versions",
                sa.Column("price_toman", sa.BigInteger(), nullable=False, server_default="0"),
            )

    tables = _tables()
    if "admin_user_plan_prices" not in tables:
        op.create_table(
            "admin_user_plan_prices",
            sa.Column("admin_id", sa.Integer(), nullable=False),
            sa.Column("plan_id", sa.BigInteger(), nullable=False),
            sa.Column("price_toman", sa.BigInteger(), nullable=False),
            sa.Column("assigned_by_admin_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.CheckConstraint("price_toman >= 0", name="ck_admin_user_plan_price_nonnegative"),
            sa.ForeignKeyConstraint(["admin_id"], ["admins.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["plan_id"], ["admin_user_plans.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["assigned_by_admin_id"], ["admins.id"], ondelete="RESTRICT"),
            sa.PrimaryKeyConstraint("admin_id", "plan_id"),
        )
    if "ix_admin_user_plan_prices_plan_admin" not in _indexes("admin_user_plan_prices"):
        op.create_index(
            "ix_admin_user_plan_prices_plan_admin",
            "admin_user_plan_prices",
            ["plan_id", "admin_id"],
        )

    tables = _tables()
    if "admin_money_transactions" not in tables:
        op.create_table(
            "admin_money_transactions",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("operation_key", sa.String(160), nullable=False),
            sa.Column("operation_type", sa.String(32), nullable=False),
            sa.Column("admin_id", sa.Integer(), nullable=False),
            sa.Column("actor_admin_id", sa.Integer(), nullable=False),
            sa.Column("counterparty_admin_id", sa.Integer(), nullable=True),
            sa.Column("delta_toman", sa.BigInteger(), nullable=False),
            sa.Column("balance_before", sa.BigInteger(), nullable=False),
            sa.Column("balance_after", sa.BigInteger(), nullable=False),
            sa.Column("plan_id", sa.BigInteger(), nullable=True),
            sa.Column("version_id", sa.BigInteger(), nullable=True),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("details", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["admin_id"], ["admins.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["actor_admin_id"], ["admins.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["counterparty_admin_id"], ["admins.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["plan_id"], ["admin_user_plans.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["version_id"], ["admin_user_plan_versions.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("operation_key", "admin_id", name="uq_admin_money_operation_admin"),
        )
    indexes = _indexes("admin_money_transactions")
    if "ix_admin_money_admin_created" not in indexes:
        op.create_index("ix_admin_money_admin_created", "admin_money_transactions", ["admin_id", "created_at", "id"])
    if "ix_admin_money_user_created" not in indexes:
        op.create_index("ix_admin_money_user_created", "admin_money_transactions", ["user_id", "created_at", "id"])


def downgrade() -> None:
    tables = _tables()
    if "admin_money_transactions" in tables:
        # MySQL may select these composite indexes to support the table's
        # foreign keys. Dropping the table removes its indexes atomically;
        # dropping them first fails with error 1553 on MySQL 8.0.
        op.drop_table("admin_money_transactions")
    if "admin_user_plan_prices" in tables:
        op.drop_table("admin_user_plan_prices")
    if "admin_user_plan_versions" in tables and "price_toman" in _columns("admin_user_plan_versions"):
        op.drop_column("admin_user_plan_versions", "price_toman")
    if "marzhelp_admin_settings" in tables:
        columns = _columns("marzhelp_admin_settings")
        for name in (
            "usage_billing_remainder",
            "used_traffic_price_per_gib_toman",
            "money_balance_toman",
            "money_billing_enabled",
        ):
            if name in columns:
                op.drop_column("marzhelp_admin_settings", name)
                columns.remove(name)
