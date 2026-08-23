"""Add stable per-Admin customer username namespaces.

Revision ID: 3a7e5c1b8d42
Revises: 9f6a2c8d4e10
"""

from hashlib import sha256

from alembic import op
import sqlalchemy as sa


revision = "3a7e5c1b8d42"
down_revision = "9f6a2c8d4e10"
branch_labels = None
depends_on = None


COLUMN = "user_namespace_prefix"
INDEX = "uq_admins_user_namespace_prefix"


def _base36(value: int) -> str:
    alphabet = "0123456789abcdefghijklmnopqrstuvwxyz"
    encoded = ""
    while value:
        value, remainder = divmod(value, 36)
        encoded = alphabet[remainder] + encoded
    return encoded or "0"


def _legacy_prefix(admin_id: int, username: str) -> str:
    digest = sha256(f"{admin_id}:{username}".encode("utf-8")).hexdigest()[:4]
    return f"u{_base36(admin_id)}{digest}"


def _columns() -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns("admins")}


def _indexes() -> set[str]:
    inspector = sa.inspect(op.get_bind())
    names = {index["name"] for index in inspector.get_indexes("admins") if index.get("name")}
    names.update(
        constraint["name"]
        for constraint in inspector.get_unique_constraints("admins")
        if constraint.get("name")
    )
    return names


def upgrade() -> None:
    if COLUMN not in _columns():
        op.add_column("admins", sa.Column(COLUMN, sa.String(length=16), nullable=True))

    connection = op.get_bind()
    rows = connection.execute(
        sa.text(
            "SELECT id, username FROM admins "
            "WHERE user_namespace_prefix IS NULL ORDER BY id"
        )
    ).all()
    for admin_id, username in rows:
        connection.execute(
            sa.text(
                "UPDATE admins SET user_namespace_prefix = :prefix "
                "WHERE id = :admin_id AND user_namespace_prefix IS NULL"
            ),
            {
                "admin_id": admin_id,
                "prefix": _legacy_prefix(int(admin_id), str(username)),
            },
        )

    if INDEX not in _indexes():
        op.create_index(INDEX, "admins", [COLUMN], unique=True)


def downgrade() -> None:
    if INDEX in _indexes():
        op.drop_index(INDEX, table_name="admins")
    if COLUMN in _columns():
        op.drop_column("admins", COLUMN)
