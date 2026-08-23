"""Add Stage 7 referral attribution and provenance-safe Owner Freeze.

Revision ID: 7c9a2e4f1b65
Revises: 5b8d1f3a7c64
"""

from alembic import op
import sqlalchemy as sa


revision = "7c9a2e4f1b65"
down_revision = "5b8d1f3a7c64"
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    event_columns = _columns("admin_suspension_events")
    additions = (
        sa.Column("operation_type", sa.String(32), nullable=False, server_default="suspension"),
        sa.Column("idempotency_key", sa.String(128), nullable=True),
        sa.Column("payload_fingerprint", sa.String(64), nullable=True),
        sa.Column("resolved_by_admin_id", sa.Integer(), nullable=True),
        sa.Column("resolved_idempotency_key", sa.String(128), nullable=True),
    )
    for column in additions:
        if column.name not in event_columns:
            op.add_column("admin_suspension_events", column)
    indexes = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes("admin_suspension_events")}
    if "uq_admin_suspension_event_idempotency" not in indexes:
        op.create_index(
            "uq_admin_suspension_event_idempotency",
            "admin_suspension_events",
            ["idempotency_key"],
            unique=True,
        )
    if "uq_admin_suspension_event_resolved_idempotency" not in indexes:
        op.create_index(
            "uq_admin_suspension_event_resolved_idempotency",
            "admin_suspension_events",
            ["resolved_idempotency_key"],
            unique=True,
        )
    foreign_keys = {fk.get("name") for fk in sa.inspect(op.get_bind()).get_foreign_keys("admin_suspension_events")}
    if "fk_admin_suspension_event_resolver" not in foreign_keys:
        op.create_foreign_key(
            "fk_admin_suspension_event_resolver",
            "admin_suspension_events",
            "admins",
            ["resolved_by_admin_id"],
            ["id"],
            ondelete="RESTRICT",
        )

    if "admin_suspension_admins" not in _tables():
        op.create_table(
            "admin_suspension_admins",
            sa.Column("event_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
            sa.Column("admin_id", sa.Integer(), nullable=False),
            sa.Column("previous_account_status_id", sa.SmallInteger(), nullable=False),
            sa.Column("previous_suspended_reason_id", sa.SmallInteger(), nullable=True),
            sa.Column("previous_suspended_at", sa.DateTime(), nullable=True),
            sa.Column("previous_suspended_by_admin_id", sa.Integer(), nullable=True),
            sa.Column("previous_suspension_event_id", sa.BigInteger(), nullable=True),
            sa.Column("applied_account_status_id", sa.SmallInteger(), nullable=False),
            sa.Column("restore_status", sa.String(24), nullable=False, server_default="applied"),
            sa.ForeignKeyConstraint(["event_id"], ["admin_suspension_events.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["admin_id"], ["admins.id"], ondelete="RESTRICT"),
            sa.PrimaryKeyConstraint("event_id", "admin_id"),
        )
        op.create_index(
            "ix_admin_suspension_admin_cursor",
            "admin_suspension_admins",
            ["event_id", "restore_status", "admin_id"],
        )

    if "admin_referral_attributions" not in _tables():
        op.create_table(
            "admin_referral_attributions",
            sa.Column("referred_admin_id", sa.Integer(), nullable=False),
            sa.Column("referrer_admin_id", sa.Integer(), nullable=False),
            sa.Column("rate_bps", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_by_admin_id", sa.Integer(), nullable=False),
            sa.Column("updated_by_admin_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.CheckConstraint("referrer_admin_id <> referred_admin_id", name="ck_admin_referral_no_self"),
            sa.CheckConstraint("rate_bps >= 0 AND rate_bps <= 10000", name="ck_admin_referral_rate"),
            sa.ForeignKeyConstraint(["referred_admin_id"], ["admins.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["referrer_admin_id"], ["admins.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["created_by_admin_id"], ["admins.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["updated_by_admin_id"], ["admins.id"], ondelete="RESTRICT"),
            sa.PrimaryKeyConstraint("referred_admin_id"),
        )
        op.create_index(
            "ix_admin_referral_referrer_referred",
            "admin_referral_attributions",
            ["referrer_admin_id", "referred_admin_id"],
        )

    if "admin_referral_events" not in _tables():
        op.create_table(
            "admin_referral_events",
            sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True),
            sa.Column("actor_admin_id", sa.Integer(), nullable=False),
            sa.Column("referred_admin_id", sa.Integer(), nullable=False),
            sa.Column("previous_referrer_admin_id", sa.Integer(), nullable=True),
            sa.Column("new_referrer_admin_id", sa.Integer(), nullable=True),
            sa.Column("previous_rate_bps", sa.Integer(), nullable=True),
            sa.Column("new_rate_bps", sa.Integer(), nullable=True),
            sa.Column("operation_type", sa.String(16), nullable=False),
            sa.Column("idempotency_key", sa.String(128), nullable=False),
            sa.Column("payload_fingerprint", sa.String(64), nullable=False),
            sa.Column("note", sa.String(512), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["actor_admin_id"], ["admins.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["referred_admin_id"], ["admins.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["previous_referrer_admin_id"], ["admins.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["new_referrer_admin_id"], ["admins.id"], ondelete="RESTRICT"),
            sa.UniqueConstraint("idempotency_key", name="uq_admin_referral_event_idempotency"),
        )
        op.create_index("ix_admin_referral_event_referred_created", "admin_referral_events", ["referred_admin_id", "created_at", "id"])
        op.create_index("ix_admin_referral_event_referrer_created", "admin_referral_events", ["new_referrer_admin_id", "created_at", "id"])


def downgrade() -> None:
    tables = _tables()
    if "admin_referral_events" in tables:
        op.drop_table("admin_referral_events")
    if "admin_referral_attributions" in tables:
        op.drop_table("admin_referral_attributions")
    if "admin_suspension_admins" in tables:
        op.drop_table("admin_suspension_admins")
    inspector = sa.inspect(op.get_bind())
    foreign_keys = {fk.get("name") for fk in inspector.get_foreign_keys("admin_suspension_events")}
    if "fk_admin_suspension_event_resolver" in foreign_keys:
        op.drop_constraint(
            "fk_admin_suspension_event_resolver",
            "admin_suspension_events",
            type_="foreignkey",
        )
    indexes = {index["name"] for index in inspector.get_indexes("admin_suspension_events")}
    for index_name in (
        "uq_admin_suspension_event_resolved_idempotency",
        "uq_admin_suspension_event_idempotency",
    ):
        if index_name in indexes:
            op.drop_index(index_name, table_name="admin_suspension_events")
    event_columns = _columns("admin_suspension_events")
    for name in (
        "resolved_idempotency_key",
        "resolved_by_admin_id",
        "payload_fingerprint",
        "idempotency_key",
        "operation_type",
    ):
        if name in event_columns:
            op.drop_column("admin_suspension_events", name)
