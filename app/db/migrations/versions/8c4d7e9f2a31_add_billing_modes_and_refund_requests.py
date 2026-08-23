"""Add explicit billing modes and allocated-traffic refund requests.

Revision ID: 8c4d7e9f2a31
Revises: 7d2c6a4e9b10
"""

from alembic import op
import sqlalchemy as sa


revision = "8c4d7e9f2a31"
down_revision = "7d2c6a4e9b10"
branch_labels = None
depends_on = None


SETTINGS = "marzhelp_admin_settings"
REQUESTS = "allocated_traffic_refund_requests"
EVENTS = "allocated_traffic_refund_events"


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _columns(table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    if "billing_mode" not in _columns(SETTINGS):
        op.add_column(
            SETTINGS,
            sa.Column(
                "billing_mode",
                sa.String(length=32),
                nullable=True,
                server_default="LEGACY_COMPAT",
            ),
        )
    op.execute(
        sa.text(
            "UPDATE marzhelp_admin_settings "
            "SET billing_mode = 'LEGACY_COMPAT' WHERE billing_mode IS NULL"
        )
    )

    tables = _tables()
    if REQUESTS not in tables:
        op.create_table(
            REQUESTS,
            sa.Column(
                "id",
                sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
                primary_key=True,
                autoincrement=True,
            ),
            sa.Column("requester_admin_id", sa.Integer(), nullable=False),
            sa.Column("account_admin_id", sa.Integer(), nullable=False),
            sa.Column("reviewer_admin_id", sa.Integer(), nullable=False),
            sa.Column("target_user_id", sa.Integer(), nullable=False),
            sa.Column("target_username", sa.String(length=34), nullable=False),
            sa.Column("snapshot_billing_mode", sa.String(length=32), nullable=False),
            sa.Column("snapshot_plan_id", sa.BigInteger(), nullable=True),
            sa.Column("snapshot_plan_version_id", sa.BigInteger(), nullable=True),
            sa.Column("snapshot_plan_name", sa.String(length=128), nullable=True),
            sa.Column("snapshot_allocated_quota", sa.BigInteger(), nullable=False),
            sa.Column("snapshot_current_quota", sa.BigInteger(), nullable=False),
            sa.Column("snapshot_used_traffic", sa.BigInteger(), nullable=False),
            sa.Column("snapshot_remaining_traffic", sa.BigInteger(), nullable=False),
            sa.Column("snapshot_user_created_at", sa.DateTime(), nullable=True),
            sa.Column("snapshot_user_expire_at", sa.DateTime(), nullable=True),
            sa.Column("snapshot_pre_delete_status", sa.String(length=32), nullable=False),
            sa.Column("requested_refund_amount", sa.BigInteger(), nullable=False),
            sa.Column("request_reason", sa.String(length=512), nullable=False),
            sa.Column("request_note", sa.String(length=1024), nullable=True),
            sa.Column("correlation_id", sa.String(length=128), nullable=False),
            sa.Column("idempotency_key", sa.String(length=128), nullable=False),
            sa.Column("status", sa.String(length=16), server_default="PENDING", nullable=False),
            sa.Column("requested_at", sa.DateTime(), nullable=False),
            sa.Column("decided_at", sa.DateTime(), nullable=True),
            sa.Column("decided_by_admin_id", sa.Integer(), nullable=True),
            sa.Column("decision_explanation", sa.String(length=1024), nullable=True),
            sa.Column("ledger_transfer_id", sa.BigInteger(), nullable=True),
            sa.CheckConstraint(
                "status IN ('PENDING','APPROVED','REJECTED','CANCELLED')",
                name="ck_alloc_refund_status",
            ),
            sa.CheckConstraint(
                "requested_refund_amount > 0",
                name="ck_alloc_refund_amount_positive",
            ),
            sa.ForeignKeyConstraint(
                ["requester_admin_id"], ["admins.id"], ondelete="RESTRICT"
            ),
            sa.ForeignKeyConstraint(
                ["account_admin_id"], ["admins.id"], ondelete="RESTRICT"
            ),
            sa.ForeignKeyConstraint(
                ["reviewer_admin_id"], ["admins.id"], ondelete="RESTRICT"
            ),
            sa.ForeignKeyConstraint(
                ["decided_by_admin_id"], ["admins.id"], ondelete="RESTRICT"
            ),
            sa.ForeignKeyConstraint(
                ["ledger_transfer_id"], ["admin_credit_transfers.id"], ondelete="RESTRICT"
            ),
            sa.UniqueConstraint("idempotency_key", name="uq_alloc_refund_idempotency"),
            sa.UniqueConstraint("ledger_transfer_id", name="uq_alloc_refund_ledger"),
        )
        op.create_index(
            "ix_alloc_refund_reviewer_status_requested",
            REQUESTS,
            ["reviewer_admin_id", "status", "requested_at", "id"],
        )
        op.create_index(
            "ix_alloc_refund_requester_requested",
            REQUESTS,
            ["requester_admin_id", "requested_at", "id"],
        )
        op.create_index(
            "ix_alloc_refund_correlation",
            REQUESTS,
            ["correlation_id"],
        )

    if EVENTS not in _tables():
        op.create_table(
            EVENTS,
            sa.Column(
                "id",
                sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
                primary_key=True,
                autoincrement=True,
            ),
            sa.Column(
                "request_id",
                sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
                nullable=False,
            ),
            sa.Column("actor_admin_id", sa.Integer(), nullable=False),
            sa.Column("from_status", sa.String(length=16), nullable=True),
            sa.Column("to_status", sa.String(length=16), nullable=False),
            sa.Column("explanation", sa.String(length=1024), nullable=True),
            sa.Column("operation_key", sa.String(length=128), nullable=False),
            sa.Column("correlation_id", sa.String(length=128), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.CheckConstraint(
                "to_status IN ('PENDING','APPROVED','REJECTED','CANCELLED')",
                name="ck_alloc_refund_event_status",
            ),
            sa.ForeignKeyConstraint(
                ["request_id"], [f"{REQUESTS}.id"], ondelete="RESTRICT"
            ),
            sa.ForeignKeyConstraint(
                ["actor_admin_id"], ["admins.id"], ondelete="RESTRICT"
            ),
            sa.UniqueConstraint("operation_key", name="uq_alloc_refund_event_operation"),
        )
        op.create_index(
            "ix_alloc_refund_event_request_created",
            EVENTS,
            ["request_id", "created_at", "id"],
        )


def downgrade() -> None:
    tables = _tables()
    if EVENTS in tables:
        op.drop_table(EVENTS)
    if REQUESTS in tables:
        op.drop_table(REQUESTS)
    if "billing_mode" in _columns(SETTINGS):
        op.drop_column(SETTINGS, "billing_mode")
