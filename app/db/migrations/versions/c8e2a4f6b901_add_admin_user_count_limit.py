"""add admin user count limit

Revision ID: c8e2a4f6b901
Revises: 9f4a1c2d7e31
"""

from alembic import op
import sqlalchemy as sa


revision = "c8e2a4f6b901"
down_revision = "9f4a1c2d7e31"
branch_labels = None
depends_on = None


def _columns(name: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(name)}


def _indexes(name: str) -> list[dict]:
    return sa.inspect(op.get_bind()).get_indexes(name)


def upgrade() -> None:
    if "max_users" not in _columns("marzhelp_admin_settings"):
        op.add_column(
            "marzhelp_admin_settings",
            sa.Column("max_users", sa.BigInteger(), nullable=True),
        )
    if not any(index.get("column_names") == ["admin_id"] for index in _indexes("users")):
        op.create_index("ix_users_admin_id", "users", ["admin_id"], unique=False)


def downgrade() -> None:
    if any(index.get("name") == "ix_users_admin_id" for index in _indexes("users")):
        op.drop_index("ix_users_admin_id", table_name="users")
    if "max_users" in _columns("marzhelp_admin_settings"):
        op.drop_column("marzhelp_admin_settings", "max_users")
