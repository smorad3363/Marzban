"""Add Stage 9 Admin phone and dashboard aggregate indexes.

Revision ID: 6d4f2a9c8e10
Revises: 2e8c4a6f9b17
"""

from alembic import op
import sqlalchemy as sa


revision = "6d4f2a9c8e10"
down_revision = "2e8c4a6f9b17"
branch_labels = None
depends_on = None


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _columns(table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}


def _indexes(table: str) -> set[str]:
    return {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table)}


def upgrade() -> None:
    tables = _tables()
    if "admins" in tables and "phone" not in _columns("admins"):
        op.add_column("admins", sa.Column("phone", sa.String(32), nullable=True))

    if "users" in tables:
        indexes = _indexes("users")
        if "ix_users_created_at_id" not in indexes:
            op.create_index("ix_users_created_at_id", "users", ["created_at", "id"])
        if "ix_users_admin_status" not in indexes:
            op.create_index("ix_users_admin_status", "users", ["admin_id", "status"])


def downgrade() -> None:
    tables = _tables()
    if "users" in tables:
        indexes = _indexes("users")
        if "ix_users_admin_status" in indexes:
            # MySQL may discard the implicit FK-supporting admin_id index after
            # the composite index is added. Recreate a supporting index before
            # removing the Stage 9 composite during rollback.
            if "ix_users_admin_id" not in indexes:
                op.create_index("ix_users_admin_id", "users", ["admin_id"])
            op.drop_index("ix_users_admin_status", table_name="users")
        if "ix_users_created_at_id" in indexes:
            op.drop_index("ix_users_created_at_id", table_name="users")
    if "admins" in tables and "phone" in _columns("admins"):
        op.drop_column("admins", "phone")
