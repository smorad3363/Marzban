"""add admin identity foundation

Revision ID: b4c2d8e6f1a3
Revises: 9c2f1a7b4d6e
"""

from alembic import op
import sqlalchemy as sa


revision = "b4c2d8e6f1a3"
down_revision = "9c2f1a7b4d6e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "admins",
        sa.Column("role", sa.String(length=16), nullable=True),
    )
    op.add_column(
        "admins",
        sa.Column("status", sa.String(length=16), nullable=True),
    )
    op.add_column(
        "admins",
        sa.Column("permissions", sa.JSON(), nullable=True),
    )

    op.execute(
        sa.text(
            "UPDATE admins SET role = CASE "
            "WHEN is_sudo = true THEN 'owner' ELSE 'reseller' END"
        )
    )
    op.execute(sa.text("UPDATE admins SET status = 'active'"))
    op.execute(
        sa.text(
            "UPDATE admins SET permissions = JSON_OBJECT() "
            "WHERE permissions IS NULL"
        )
    )

    op.alter_column(
        "admins",
        "role",
        existing_type=sa.String(length=16),
        nullable=False,
    )
    op.alter_column(
        "admins",
        "status",
        existing_type=sa.String(length=16),
        nullable=False,
    )
    op.alter_column(
        "admins",
        "permissions",
        existing_type=sa.JSON(),
        nullable=False,
    )


def downgrade() -> None:
    op.drop_column("admins", "permissions")
    op.drop_column("admins", "status")
    op.drop_column("admins", "role")
