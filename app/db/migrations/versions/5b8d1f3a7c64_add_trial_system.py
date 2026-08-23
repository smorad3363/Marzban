"""Add first-class Trial plans, quota, assignment snapshots and cleanup ledger.

Revision ID: 5b8d1f3a7c64
Revises: 3a7e5c1b8d42
"""

from alembic import op
import sqlalchemy as sa


revision = "5b8d1f3a7c64"
down_revision = "3a7e5c1b8d42"
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    if "is_trial" not in _columns("admin_user_plans"):
        op.add_column(
            "admin_user_plans",
            sa.Column("is_trial", sa.Boolean(), nullable=False, server_default=sa.false()),
        )
    if "is_trial" not in _columns("user_plan_assignments"):
        op.add_column(
            "user_plan_assignments",
            sa.Column("is_trial", sa.Boolean(), nullable=False, server_default=sa.false()),
        )
        op.create_index(
            "ix_user_plan_assignments_trial_operation_user",
            "user_plan_assignments",
            ["is_trial", "operation_type", "user_id"],
        )
    settings_columns = _columns("marzhelp_admin_settings")
    if "trial_quota" not in settings_columns:
        op.add_column(
            "marzhelp_admin_settings",
            sa.Column("trial_quota", sa.BigInteger(), nullable=False, server_default="0"),
        )
    if "trials_used" not in settings_columns:
        op.add_column(
            "marzhelp_admin_settings",
            sa.Column("trials_used", sa.BigInteger(), nullable=False, server_default="0"),
        )

    if "trial_cleanup_operations" not in _tables():
        op.create_table(
            "trial_cleanup_operations",
            sa.Column(
                "id",
                sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
                primary_key=True,
                autoincrement=True,
            ),
            sa.Column("actor_admin_id", sa.Integer(), nullable=False),
            sa.Column("expired_before", sa.DateTime(), nullable=False),
            sa.Column("payload_fingerprint", sa.String(length=64), nullable=False),
            sa.Column("idempotency_key", sa.String(length=128), nullable=False),
            sa.Column("deleted_count", sa.Integer(), nullable=False),
            sa.Column("deleted_usernames", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["actor_admin_id"], ["admins.id"], ondelete="RESTRICT"),
            sa.UniqueConstraint("idempotency_key", name="uq_trial_cleanup_idempotency"),
        )
        op.create_index(
            "ix_trial_cleanup_actor_created",
            "trial_cleanup_operations",
            ["actor_admin_id", "created_at", "id"],
        )


def downgrade() -> None:
    if "trial_cleanup_operations" in _tables():
        op.drop_index("ix_trial_cleanup_actor_created", table_name="trial_cleanup_operations")
        op.drop_table("trial_cleanup_operations")
    settings_columns = _columns("marzhelp_admin_settings")
    if "trials_used" in settings_columns:
        op.drop_column("marzhelp_admin_settings", "trials_used")
    if "trial_quota" in settings_columns:
        op.drop_column("marzhelp_admin_settings", "trial_quota")
    if "is_trial" in _columns("user_plan_assignments"):
        op.drop_index(
            "ix_user_plan_assignments_trial_operation_user",
            table_name="user_plan_assignments",
        )
        op.drop_column("user_plan_assignments", "is_trial")
    if "is_trial" in _columns("admin_user_plans"):
        op.drop_column("admin_user_plans", "is_trial")
