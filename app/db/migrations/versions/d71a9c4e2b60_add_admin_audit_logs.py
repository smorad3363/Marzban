"""add admin audit logs

Revision ID: d71a9c4e2b60
Revises: c8e2a4f6b901
"""

from alembic import op
import sqlalchemy as sa


revision = "d71a9c4e2b60"
down_revision = "c8e2a4f6b901"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "admin_audit_logs" in inspector.get_table_names():
        return

    op.create_table(
        "admin_audit_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("admin_id", sa.Integer(), nullable=True),
        sa.Column("admin_username", sa.String(length=34), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("target_type", sa.String(length=64), nullable=False),
        sa.Column("target_id", sa.String(length=128), nullable=True),
        sa.Column("target_name", sa.String(length=256), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("previous_value", sa.JSON(), nullable=True),
        sa.Column("new_value", sa.JSON(), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["admin_id"],
            ["admins.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_admin_audit_logs_admin_username",
        "admin_audit_logs",
        ["admin_username"],
        unique=False,
    )
    op.create_index(
        "ix_admin_audit_logs_created_at",
        "admin_audit_logs",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_admin_audit_logs_admin_created",
        "admin_audit_logs",
        ["admin_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_admin_audit_logs_action_created",
        "admin_audit_logs",
        ["action", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_admin_audit_logs_target",
        "admin_audit_logs",
        ["target_type", "target_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_audit_logs_target_name_created",
        "admin_audit_logs",
        ["target_name", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    if "admin_audit_logs" in sa.inspect(op.get_bind()).get_table_names():
        op.drop_table("admin_audit_logs")
