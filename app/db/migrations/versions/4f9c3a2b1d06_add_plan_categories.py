"""Add plan categories and administrator category access.

Revision ID: 4f9c3a2b1d06
Revises: e2a6c1f4b903
"""

from alembic import op
import sqlalchemy as sa


revision = "4f9c3a2b1d06"
down_revision = "e2a6c1f4b903"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "admin_plan_categories",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), autoincrement=True, nullable=False),
        sa.Column("owner_admin_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.String(length=512), nullable=True),
        sa.Column("archived_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["owner_admin_id"], ["admins.id"],
            name="fk_admin_plan_categories_owner", ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_admin_id", "name", name="uq_admin_plan_categories_owner_name"),
    )
    op.create_index(
        "ix_admin_plan_categories_owner_active",
        "admin_plan_categories",
        ["owner_admin_id", "archived_at", "id"],
        unique=False,
    )

    op.create_table(
        "admin_plan_category_access",
        sa.Column("category_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("admin_id", sa.Integer(), nullable=False),
        sa.Column("assigned_by_admin_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["category_id"], ["admin_plan_categories.id"],
            name="fk_admin_plan_category_access_category", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["admin_id"], ["admins.id"],
            name="fk_admin_plan_category_access_admin", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["assigned_by_admin_id"], ["admins.id"],
            name="fk_admin_plan_category_access_actor", ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("category_id", "admin_id"),
    )
    op.create_index(
        "ix_admin_plan_category_access_admin_category",
        "admin_plan_category_access",
        ["admin_id", "category_id"],
        unique=False,
    )

    with op.batch_alter_table("admin_user_plans") as batch_op:
        batch_op.add_column(
            sa.Column(
                "category_id",
                sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
                nullable=True,
            )
        )
        batch_op.create_foreign_key(
            "fk_admin_user_plans_category",
            "admin_plan_categories",
            ["category_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index(
            "ix_admin_user_plans_category_active",
            ["category_id", "archived_at", "id"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("admin_user_plans") as batch_op:
        batch_op.drop_index("ix_admin_user_plans_category_active")
        batch_op.drop_constraint("fk_admin_user_plans_category", type_="foreignkey")
        batch_op.drop_column("category_id")
    op.drop_index(
        "ix_admin_plan_category_access_admin_category",
        table_name="admin_plan_category_access",
    )
    op.drop_table("admin_plan_category_access")
    op.drop_index(
        "ix_admin_plan_categories_owner_active",
        table_name="admin_plan_categories",
    )
    op.drop_table("admin_plan_categories")
