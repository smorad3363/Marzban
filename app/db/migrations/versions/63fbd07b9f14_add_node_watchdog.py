"""add node watchdog

Revision ID: 63fbd07b9f14
Revises: 2b231de97dc3
"""
from alembic import op
import sqlalchemy as sa


revision = "63fbd07b9f14"
down_revision = "2b231de97dc3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "nodes",
        sa.Column("watchdog_enabled", sa.Boolean(), server_default="1", nullable=False),
    )
    op.create_table(
        "node_watchdog_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("telegram_bot_token", sa.String(length=256), nullable=True),
        sa.Column("telegram_chat_id", sa.String(length=64), nullable=True),
        sa.Column("check_interval", sa.Integer(), nullable=False),
        sa.Column("backoff_cap", sa.Integer(), nullable=False),
        sa.Column("remind_every", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    table = sa.table(
        "node_watchdog_settings",
        sa.column("id", sa.Integer()),
        sa.column("enabled", sa.Boolean()),
        sa.column("check_interval", sa.Integer()),
        sa.column("backoff_cap", sa.Integer()),
        sa.column("remind_every", sa.Integer()),
    )
    op.bulk_insert(table, [{
        "id": 1,
        "enabled": False,
        "check_interval": 15,
        "backoff_cap": 600,
        "remind_every": 1800,
    }])


def downgrade() -> None:
    op.drop_table("node_watchdog_settings")
    op.drop_column("nodes", "watchdog_enabled")
