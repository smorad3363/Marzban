"""Add persistent Stage 8 bulk job target snapshots and results.

Revision ID: 2e8c4a6f9b17
Revises: 7c9a2e4f1b65
"""

from alembic import op
import sqlalchemy as sa


revision = "2e8c4a6f9b17"
down_revision = "7c9a2e4f1b65"
branch_labels = None
depends_on = None


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _columns(table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    columns = _columns("admin_bulk_jobs")
    additions = (
        sa.Column("job_kind", sa.String(24), nullable=False, server_default="LEGACY_DISABLE"),
        sa.Column("target_scope", sa.String(40), nullable=True),
        sa.Column("selected_admin_ids", sa.JSON(), nullable=True),
        sa.Column("payload_fingerprint", sa.String(64), nullable=True),
        sa.Column("amount", sa.BigInteger(), nullable=True),
        sa.Column("days_amount", sa.Integer(), nullable=True),
        sa.Column("note", sa.String(512), nullable=True),
        sa.Column("success_count", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("failed_count", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("skipped_count", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )
    for column in additions:
        if column.name not in columns:
            op.add_column("admin_bulk_jobs", column)

    if "admin_bulk_job_targets" not in _tables():
        op.create_table(
            "admin_bulk_job_targets",
            sa.Column("job_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
            sa.Column("target_type", sa.String(16), nullable=False),
            sa.Column("target_id", sa.Integer(), nullable=False),
            sa.Column("sequence", sa.Integer(), nullable=False),
            sa.Column("target_username", sa.String(34), nullable=False),
            sa.Column("owner_admin_id", sa.Integer(), nullable=True),
            sa.Column("idempotency_key", sa.String(128), nullable=False),
            sa.Column("payload_fingerprint", sa.String(64), nullable=False),
            sa.Column("status", sa.String(16), nullable=False, server_default="PENDING"),
            sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("retryable", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("error_code", sa.String(64), nullable=True),
            sa.Column("error_message", sa.String(512), nullable=True),
            sa.Column("result_details", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["job_id"], ["admin_bulk_jobs.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("job_id", "target_type", "target_id"),
            sa.UniqueConstraint("idempotency_key", name="uq_admin_bulk_job_target_idempotency"),
        )
        op.create_index(
            "ix_admin_bulk_job_targets_pending",
            "admin_bulk_job_targets",
            ["job_id", "target_type", "status", "retryable", "sequence"],
        )
        op.create_index(
            "ix_admin_bulk_job_targets_report",
            "admin_bulk_job_targets",
            ["job_id", "sequence"],
        )
        op.create_index(
            "ix_admin_bulk_job_targets_target",
            "admin_bulk_job_targets",
            ["target_type", "target_id", "job_id"],
        )


def downgrade() -> None:
    if "admin_bulk_job_targets" in _tables():
        op.drop_table("admin_bulk_job_targets")
    columns = _columns("admin_bulk_jobs")
    for name in (
        "completed_at",
        "skipped_count",
        "failed_count",
        "success_count",
        "note",
        "days_amount",
        "amount",
        "payload_fingerprint",
        "selected_admin_ids",
        "target_scope",
        "job_kind",
    ):
        if name in columns:
            op.drop_column("admin_bulk_jobs", name)
