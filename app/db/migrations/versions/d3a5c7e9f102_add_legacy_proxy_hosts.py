"""Keep future-only historical proxy hosts routable.

Revision ID: d3a5c7e9f102
Revises: c2f4a8d6e913
"""

from alembic import op
import sqlalchemy as sa


revision = "d3a5c7e9f102"
down_revision = "c2f4a8d6e913"
branch_labels = None
depends_on = None


def _columns() -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns("hosts")}


def _indexes() -> set[str]:
    return {index["name"] for index in sa.inspect(op.get_bind()).get_indexes("hosts")}


def upgrade() -> None:
    if "is_legacy" not in _columns():
        op.add_column(
            "hosts",
            sa.Column("is_legacy", sa.Boolean(), nullable=False, server_default="0"),
        )
    if "ix_hosts_inbound_legacy_id" not in _indexes():
        op.create_index(
            "ix_hosts_inbound_legacy_id",
            "hosts",
            ["inbound_tag", "is_legacy", "id"],
        )


def downgrade() -> None:
    if "ix_hosts_inbound_legacy_id" in _indexes():
        # InnoDB may remove the original implicit FK index when the composite
        # index is added. Recreate it before dropping the composite index.
        if "hosts_ibfk_1" not in _indexes():
            op.create_index("hosts_ibfk_1", "hosts", ["inbound_tag"])
        op.drop_index("ix_hosts_inbound_legacy_id", table_name="hosts")
    if "is_legacy" in _columns():
        op.drop_column("hosts", "is_legacy")
