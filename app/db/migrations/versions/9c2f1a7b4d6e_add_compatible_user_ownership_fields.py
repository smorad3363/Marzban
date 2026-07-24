"""add compatible user ownership fields

Revision ID: 9c2f1a7b4d6e
Revises: 63fbd07b9f14
"""

import json
import logging

from alembic import context, op
import sqlalchemy as sa


revision = "9c2f1a7b4d6e"
down_revision = "63fbd07b9f14"
branch_labels = None
depends_on = None


CREATOR_PROVENANCE = "inferred_from_legacy_owner"
LEGACY_OWNER_USERNAME_ARG = "legacy_owner_username"
LEGACY_OWNER_VERIFIED_ARG = "legacy_owner_verified"
LOGGER = logging.getLogger("alembic.runtime.migration")


def _inspector():
    return sa.inspect(op.get_bind())


def _column_names():
    return {
        column["name"]
        for column in _inspector().get_columns("users")
    }


def _index_columns():
    return {
        tuple(index["column_names"])
        for index in _inspector().get_indexes("users")
    }


def _foreign_key_columns():
    return {
        tuple(foreign_key["constrained_columns"])
        for foreign_key in _inspector().get_foreign_keys("users")
        if foreign_key.get("referred_table") == "admins"
    }


def _scalar(statement, parameters=None):
    return op.get_bind().execute(
        sa.text(statement),
        parameters or {},
    ).scalar_one()


def _legacy_counts():
    return {
        "total_users": _scalar("SELECT COUNT(*) FROM users"),
        "null_admin_id": _scalar(
            "SELECT COUNT(*) FROM users WHERE admin_id IS NULL"
        ),
        "orphan_admin_id": _scalar(
            """
            SELECT COUNT(*)
            FROM users AS users
            LEFT JOIN admins AS admins ON admins.id = users.admin_id
            WHERE users.admin_id IS NOT NULL AND admins.id IS NULL
            """
        ),
    }


def _report(stage, counts, destination_username=None):
    payload = {
        "stage": stage,
        **counts,
        "creator_provenance": CREATOR_PROVENANCE,
        "legacy_owner_destination": destination_username,
    }
    LOGGER.info(
        "ownership_migration_validation=%s",
        json.dumps(payload, sort_keys=True),
    )


def _configured_legacy_owner(counts):
    if not (counts["null_admin_id"] or counts["orphan_admin_id"]):
        return None, None

    arguments = context.get_x_argument(as_dictionary=True)
    username = arguments.get(LEGACY_OWNER_USERNAME_ARG)
    verified = arguments.get(LEGACY_OWNER_VERIFIED_ARG, "").lower()

    if not username or verified not in {"1", "true", "yes"}:
        raise RuntimeError(
            "Legacy users with null or orphaned admin_id require an explicit "
            "existing destination: -x legacy_owner_username=<username> "
            "-x legacy_owner_verified=true"
        )

    rows = op.get_bind().execute(
        sa.text(
            "SELECT id FROM admins WHERE username = :username"
        ),
        {"username": username},
    ).all()
    if len(rows) != 1:
        raise RuntimeError(
            "The explicitly configured legacy owner must resolve to exactly "
            "one existing database-backed admin identity"
        )

    return rows[0][0], username


def _add_columns():
    existing = _column_names()
    columns = []
    if "created_by_admin_id" not in existing:
        columns.append(
            sa.Column("created_by_admin_id", sa.Integer(), nullable=True)
        )
    if "owner_admin_id" not in existing:
        columns.append(
            sa.Column("owner_admin_id", sa.Integer(), nullable=True)
        )

    if columns:
        with op.batch_alter_table("users") as batch_op:
            for column in columns:
                batch_op.add_column(column)


def _add_indexes():
    existing = _index_columns()
    if ("created_by_admin_id",) not in existing:
        op.create_index(
            "ix_users_created_by_admin_id",
            "users",
            ["created_by_admin_id"],
            unique=False,
        )
    if ("owner_admin_id",) not in existing:
        op.create_index(
            "ix_users_owner_admin_id",
            "users",
            ["owner_admin_id"],
            unique=False,
        )


def _repair_invalid_legacy_owners(destination_id):
    if destination_id is None:
        return

    op.get_bind().execute(
        sa.text(
            """
            UPDATE users
            SET admin_id = :destination_id
            WHERE admin_id IS NULL
               OR NOT EXISTS (
                    SELECT 1
                    FROM admins
                    WHERE admins.id = users.admin_id
               )
            """
        ),
        {"destination_id": destination_id},
    )


def _backfill():
    op.get_bind().execute(
        sa.text(
            """
            UPDATE users
            SET owner_admin_id = admin_id
            WHERE owner_admin_id IS NULL
            """
        )
    )
    op.get_bind().execute(
        sa.text(
            """
            UPDATE users
            SET created_by_admin_id = admin_id
            WHERE created_by_admin_id IS NULL
            """
        )
    )


def _validation_counts():
    return {
        "total_users": _scalar("SELECT COUNT(*) FROM users"),
        "null_admin_id": _scalar(
            "SELECT COUNT(*) FROM users WHERE admin_id IS NULL"
        ),
        "null_owner_admin_id": _scalar(
            "SELECT COUNT(*) FROM users WHERE owner_admin_id IS NULL"
        ),
        "null_created_by_admin_id": _scalar(
            "SELECT COUNT(*) FROM users WHERE created_by_admin_id IS NULL"
        ),
        "owner_mismatch": _scalar(
            """
            SELECT COUNT(*)
            FROM users
            WHERE admin_id <> owner_admin_id
               OR (admin_id IS NULL AND owner_admin_id IS NOT NULL)
               OR (admin_id IS NOT NULL AND owner_admin_id IS NULL)
            """
        ),
        "orphan_owner_admin_id": _scalar(
            """
            SELECT COUNT(*)
            FROM users AS users
            LEFT JOIN admins AS admins ON admins.id = users.owner_admin_id
            WHERE users.owner_admin_id IS NOT NULL AND admins.id IS NULL
            """
        ),
        "orphan_created_by_admin_id": _scalar(
            """
            SELECT COUNT(*)
            FROM users AS users
            LEFT JOIN admins AS admins ON admins.id = users.created_by_admin_id
            WHERE users.created_by_admin_id IS NOT NULL AND admins.id IS NULL
            """
        ),
    }


def _validate_backfill(counts):
    invalid_keys = (
        "null_admin_id",
        "null_owner_admin_id",
        "null_created_by_admin_id",
        "owner_mismatch",
        "orphan_owner_admin_id",
        "orphan_created_by_admin_id",
    )
    if any(counts[key] for key in invalid_keys):
        raise RuntimeError(
            "Ownership backfill validation failed: "
            + json.dumps(counts, sort_keys=True)
        )


def _add_foreign_keys():
    existing = _foreign_key_columns()
    missing = []
    if ("created_by_admin_id",) not in existing:
        missing.append(
            (
                "fk_users_created_by_admin_id_admins",
                "created_by_admin_id",
            )
        )
    if ("owner_admin_id",) not in existing:
        missing.append(
            (
                "fk_users_owner_admin_id_admins",
                "owner_admin_id",
            )
        )

    if missing:
        recreate = "always" if op.get_bind().dialect.name == "sqlite" else "auto"
        with op.batch_alter_table("users", recreate=recreate) as batch_op:
            for name, column in missing:
                batch_op.create_foreign_key(
                    name,
                    "admins",
                    [column],
                    ["id"],
                    ondelete="RESTRICT",
                )


def upgrade():
    _add_columns()
    _add_indexes()

    legacy_counts = _legacy_counts()
    destination_id, destination_username = _configured_legacy_owner(
        legacy_counts
    )
    _report("before_backfill", legacy_counts, destination_username)

    _repair_invalid_legacy_owners(destination_id)
    _backfill()

    validation_counts = _validation_counts()
    _validate_backfill(validation_counts)
    _add_foreign_keys()
    _report("after_backfill", validation_counts, destination_username)


def downgrade():
    raise RuntimeError(
        "Destructive Phase 2 downgrade is disabled. Roll back application "
        "dual-write behavior while retaining the additive ownership columns, "
        "then forward-fix the schema."
    )
