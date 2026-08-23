"""Add immutable explicit Host scope to Plan versions.

Revision ID: 9f6a2c8d4e10
Revises: 8c4d7e9f2a31
"""

from alembic import op
import sqlalchemy as sa


revision = "9f6a2c8d4e10"
down_revision = "8c4d7e9f2a31"
branch_labels = None
depends_on = None


TABLE = "admin_user_plan_hosts"


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    if TABLE in _tables():
        return
    op.create_table(
        TABLE,
        sa.Column(
            "version_id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            nullable=False,
        ),
        sa.Column("inbound_tag", sa.String(length=256), nullable=False),
        sa.Column("host_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["version_id"],
            ["admin_user_plan_versions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("version_id", "inbound_tag", "host_id"),
    )


def downgrade() -> None:
    if TABLE in _tables():
        op.drop_table(TABLE)
