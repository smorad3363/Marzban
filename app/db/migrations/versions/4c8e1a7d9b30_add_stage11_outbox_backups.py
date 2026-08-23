"""add Stage 11 Telegram outbox and backup artifacts

Revision ID: 4c8e1a7d9b30
Revises: 1a9e7c3d5b20
"""
from alembic import op
import sqlalchemy as sa

revision = "4c8e1a7d9b30"
down_revision = "1a9e7c3d5b20"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("telegram_outbox",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("idempotency_key", sa.String(191), nullable=False), sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False), sa.Column("status", sa.String(16), server_default="PENDING", nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False), sa.Column("next_attempt_at", sa.DateTime(), nullable=False),
        sa.Column("last_error_code", sa.String(64)), sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("completed_at", sa.DateTime()),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("idempotency_key", name="uq_telegram_outbox_idempotency"))
    op.create_index("ix_telegram_outbox_dispatch", "telegram_outbox", ["status", "next_attempt_at", "id"])
    op.create_index("ix_telegram_outbox_retention", "telegram_outbox", ["status", "completed_at", "id"])
    op.create_table("backup_artifacts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False), sa.Column("period_key", sa.String(32), nullable=False),
        sa.Column("database_name", sa.String(128), nullable=False), sa.Column("encrypted_path", sa.String(1024)),
        sa.Column("size_bytes", sa.BigInteger()), sa.Column("sha256", sa.String(64)), sa.Column("generation_status", sa.String(16), nullable=False),
        sa.Column("delivery_status", sa.String(16), nullable=False), sa.Column("error_code", sa.String(64)),
        sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("delivered_at", sa.DateTime()),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("period_key", name="uq_backup_artifacts_period"))
    op.create_index("ix_backup_artifacts_delivery", "backup_artifacts", ["delivery_status", "created_at", "id"])


def downgrade():
    op.drop_table("backup_artifacts")
    op.drop_table("telegram_outbox")
