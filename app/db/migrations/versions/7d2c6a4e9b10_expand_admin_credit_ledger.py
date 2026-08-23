"""Expand the admin credit ledger with auditable balance snapshots.

Revision ID: 7d2c6a4e9b10
Revises: 4f9c3a2b1d06
"""

from alembic import op
import sqlalchemy as sa


revision = "7d2c6a4e9b10"
down_revision = "4f9c3a2b1d06"
branch_labels = None
depends_on = None


TABLE = "admin_credit_transfers"
INDEX = "ix_admin_credit_adjusted_created"


def _columns() -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(TABLE)}


def _indexes() -> set[str]:
    return {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(TABLE)}


def upgrade() -> None:
    columns = _columns()
    additions = (
        sa.Column("adjusted_admin_id", sa.Integer(), nullable=True),
        sa.Column("resource", sa.String(length=32), nullable=True),
        sa.Column("delta", sa.BigInteger(), nullable=True),
        sa.Column("balance_before", sa.BigInteger(), nullable=True),
        sa.Column("balance_after", sa.BigInteger(), nullable=True),
        sa.Column("source_delegated_before", sa.BigInteger(), nullable=True),
        sa.Column("source_delegated_after", sa.BigInteger(), nullable=True),
    )
    for column in additions:
        if column.name not in columns:
            op.add_column(TABLE, column)

    foreign_keys = {
        key.get("name")
        for key in sa.inspect(op.get_bind()).get_foreign_keys(TABLE)
    }
    if "fk_admin_credit_adjusted_admin" not in foreign_keys:
        with op.batch_alter_table(TABLE) as batch_op:
            batch_op.create_foreign_key(
                "fk_admin_credit_adjusted_admin",
                "admins",
                ["adjusted_admin_id"],
                ["id"],
                ondelete="RESTRICT",
            )

    op.execute(
        sa.text(
            "UPDATE admin_credit_transfers SET "
            "resource = COALESCE(resource, 'traffic_credit'), "
            "delta = COALESCE(delta, CASE WHEN operation_type = 'reclaim' THEN -amount ELSE amount END), "
            "adjusted_admin_id = COALESCE(adjusted_admin_id, "
            "CASE WHEN operation_type = 'reclaim' THEN from_admin_id ELSE to_admin_id END)"
        )
    )
    if INDEX not in _indexes():
        op.create_index(
            INDEX,
            TABLE,
            ["adjusted_admin_id", "created_at", "id"],
            unique=False,
        )


def downgrade() -> None:
    if INDEX in _indexes():
        op.drop_index(INDEX, table_name=TABLE)
    columns = _columns()
    with op.batch_alter_table(TABLE) as batch_op:
        foreign_keys = {
            key.get("name")
            for key in sa.inspect(op.get_bind()).get_foreign_keys(TABLE)
        }
        if "fk_admin_credit_adjusted_admin" in foreign_keys:
            batch_op.drop_constraint("fk_admin_credit_adjusted_admin", type_="foreignkey")
        for name in (
            "source_delegated_after",
            "source_delegated_before",
            "balance_after",
            "balance_before",
            "delta",
            "resource",
            "adjusted_admin_id",
        ):
            if name in columns:
                batch_op.drop_column(name)
