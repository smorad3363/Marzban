"""Add Stage 10 User pagination indexes.

Revision ID: 1a9e7c3d5b20
Revises: 6d4f2a9c8e10
"""

from alembic import op
import sqlalchemy as sa


revision = "1a9e7c3d5b20"
down_revision = "6d4f2a9c8e10"
branch_labels = None
depends_on = None


def _indexes() -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if "users" not in inspector.get_table_names():
        return set()
    return {index["name"] for index in inspector.get_indexes("users")}


def upgrade() -> None:
    indexes = _indexes()
    if "ix_users_status_created_id" not in indexes:
        op.create_index(
            "ix_users_status_created_id", "users", ["status", "created_at", "id"]
        )
    if "ix_users_admin_created_id" not in indexes:
        op.create_index(
            "ix_users_admin_created_id", "users", ["admin_id", "created_at", "id"]
        )


def downgrade() -> None:
    indexes = _indexes()
    if "ix_users_admin_created_id" in indexes:
        op.drop_index("ix_users_admin_created_id", table_name="users")
    if "ix_users_status_created_id" in indexes:
        op.drop_index("ix_users_status_created_id", table_name="users")
