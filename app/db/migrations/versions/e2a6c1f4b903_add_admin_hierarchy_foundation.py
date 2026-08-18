"""add admin hierarchy foundation in compatibility mode

Revision ID: e2a6c1f4b903
Revises: a41c8e7d5b92
"""

from alembic import op
import sqlalchemy as sa


revision = "e2a6c1f4b903"
down_revision = "a41c8e7d5b92"
branch_labels = None
depends_on = None


ROLE_ROWS = (
    (1, "OWNER"),
    (2, "SUPER_ADMIN"),
    (3, "ADMIN"),
)

USER_CREATION_MODE_ROWS = ((1, "FREE_FORM"), (2, "PLAN_ONLY"))
ACCOUNT_STATUS_ROWS = ((1, "ACTIVE"), (2, "SUSPENDED"), (3, "DISABLED"))
SUSPENSION_REASON_ROWS = (
    (1, "MANUAL", "Suspended manually by an authorized administrator"),
    (2, "CREDIT_EXHAUSTED", "Available traffic credit was exhausted"),
    (3, "ACCOUNT_EXPIRED", "Administrative account expiry was reached"),
)


def _inspector() -> sa.Inspector:
    return sa.inspect(op.get_bind())


def _tables() -> set[str]:
    return set(_inspector().get_table_names())


def _columns(table: str) -> set[str]:
    return {column["name"] for column in _inspector().get_columns(table)}


def _indexes(table: str) -> list[dict]:
    return _inspector().get_indexes(table)


def _foreign_keys(table: str) -> list[dict]:
    return _inspector().get_foreign_keys(table)


def _has_index_columns(table: str, columns: list[str]) -> bool:
    return any(
        list(index.get("column_names") or []) == columns
        for index in _indexes(table)
    )


def _has_foreign_key_columns(table: str, columns: list[str]) -> bool:
    return any(
        list(foreign_key.get("constrained_columns") or []) == columns
        for foreign_key in _foreign_keys(table)
    )


def _ensure_index(table: str, name: str, columns: list[str]) -> None:
    if table in _tables() and not _has_index_columns(table, columns):
        op.create_index(name, table, columns, unique=False)


def _add_column(table: str, column: sa.Column) -> None:
    if column.name not in _columns(table):
        op.add_column(table, column)


def _seed_roles(bind: sa.Connection) -> None:
    existing = {
        row.id: row.code
        for row in bind.execute(sa.text("SELECT id, code FROM admin_roles"))
    }
    existing_codes = {code: role_id for role_id, code in existing.items()}
    for role_id, code in ROLE_ROWS:
        if role_id in existing and existing[role_id] != code:
            raise RuntimeError(
                f"admin_roles id {role_id} already belongs to {existing[role_id]!r}"
            )
        if code in existing_codes and existing_codes[code] != role_id:
            raise RuntimeError(
                f"admin_roles code {code!r} already belongs to id {existing_codes[code]}"
            )
        if role_id not in existing:
            bind.execute(
                sa.text("INSERT INTO admin_roles (id, code) VALUES (:id, :code)"),
                {"id": role_id, "code": code},
            )


def _seed_code_rows(
    bind: sa.Connection,
    table: str,
    rows: tuple[tuple[int, str], ...],
) -> None:
    existing = {
        row.id: row.code
        for row in bind.execute(sa.text(f"SELECT id, code FROM {table}"))
    }
    existing_codes = {code: row_id for row_id, code in existing.items()}
    for row_id, code in rows:
        if row_id in existing and existing[row_id] != code:
            raise RuntimeError(f"{table} id {row_id} already belongs to {existing[row_id]!r}")
        if code in existing_codes and existing_codes[code] != row_id:
            raise RuntimeError(f"{table} code {code!r} already belongs to id {existing_codes[code]}")
        if row_id not in existing:
            bind.execute(
                sa.text(f"INSERT INTO {table} (id, code) VALUES (:id, :code)"),
                {"id": row_id, "code": code},
            )


def _ensure_mysql_foreign_keys() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "mysql":
        return

    constraints = (
        (
            "fk_admins_role_id_admin_roles",
            "admins",
            "admin_roles",
            ["role_id"],
            ["id"],
            None,
        ),
        (
            "fk_admins_parent_admin_id_admins",
            "admins",
            "admins",
            ["parent_admin_id"],
            ["id"],
            "RESTRICT",
        ),
        (
            "fk_admins_external_api_updated_by_admins",
            "admins",
            "admins",
            ["external_api_updated_by"],
            ["id"],
            "SET NULL",
        ),
    )
    for name, source, target, local, remote, ondelete in constraints:
        if not _has_foreign_key_columns(source, local):
            op.create_foreign_key(
                name,
                source,
                target,
                local,
                remote,
                ondelete=ondelete,
            )


def _bigint_pk():
    return sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def _create_extended_schema(bind: sa.Connection) -> None:
    tables = _tables()
    for table, rows in (
        ("admin_user_creation_modes", USER_CREATION_MODE_ROWS),
        ("admin_account_statuses", ACCOUNT_STATUS_ROWS),
    ):
        if table not in tables:
            op.create_table(
                table,
                sa.Column("id", sa.SmallInteger(), autoincrement=False, nullable=False),
                sa.Column("code", sa.String(length=32), nullable=False),
                sa.PrimaryKeyConstraint("id"),
                sa.UniqueConstraint("code", name=f"uq_{table}_code"),
            )
        _seed_code_rows(bind, table, rows)
        tables.add(table)

    if "admin_suspension_reasons" not in tables:
        op.create_table(
            "admin_suspension_reasons",
            sa.Column("id", sa.SmallInteger(), autoincrement=False, nullable=False),
            sa.Column("code", sa.String(length=64), nullable=False),
            sa.Column("description", sa.String(length=255), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("code", name="uq_admin_suspension_reasons_code"),
        )
    existing_reasons = {
        row.id: row.code
        for row in bind.execute(sa.text("SELECT id, code FROM admin_suspension_reasons"))
    }
    for reason_id, code, description in SUSPENSION_REASON_ROWS:
        if reason_id not in existing_reasons:
            bind.execute(
                sa.text(
                    "INSERT INTO admin_suspension_reasons (id, code, description) "
                    "VALUES (:id, :code, :description)"
                ),
                {"id": reason_id, "code": code, "description": description},
            )

    tables = _tables()
    if "admin_credit_transfers" not in tables:
        op.create_table(
            "admin_credit_transfers",
            sa.Column("id", _bigint_pk(), autoincrement=True, nullable=False),
            sa.Column("from_admin_id", sa.Integer(), nullable=True),
            sa.Column("to_admin_id", sa.Integer(), nullable=True),
            sa.Column("actor_admin_id", sa.Integer(), nullable=False),
            sa.Column("amount", sa.BigInteger(), nullable=False),
            sa.Column("operation_type", sa.String(length=32), nullable=False),
            sa.Column("idempotency_key", sa.String(length=128), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("note", sa.String(length=512), nullable=True),
            sa.CheckConstraint("amount > 0", name="ck_admin_credit_transfer_amount_positive"),
            sa.ForeignKeyConstraint(["from_admin_id"], ["admins.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["to_admin_id"], ["admins.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["actor_admin_id"], ["admins.id"], ondelete="RESTRICT"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("idempotency_key", name="uq_admin_credit_idempotency_key"),
        )
        op.create_index("ix_admin_credit_from_created", "admin_credit_transfers", ["from_admin_id", "created_at", "id"])
        op.create_index("ix_admin_credit_to_created", "admin_credit_transfers", ["to_admin_id", "created_at", "id"])
        op.create_index("ix_admin_credit_actor_created", "admin_credit_transfers", ["actor_admin_id", "created_at", "id"])

    if "admin_api_tokens" not in tables:
        op.create_table(
            "admin_api_tokens",
            sa.Column("id", _bigint_pk(), autoincrement=True, nullable=False),
            sa.Column("admin_id", sa.Integer(), nullable=False),
            sa.Column("token_hash", sa.BINARY(length=32), nullable=False),
            sa.Column("name", sa.String(length=96), nullable=False),
            sa.Column("scopes", sa.JSON(), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("last_used_at", sa.DateTime(), nullable=True),
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
            sa.Column("created_by_admin_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["admin_id"], ["admins.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["created_by_admin_id"], ["admins.id"], ondelete="RESTRICT"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("token_hash", name="uq_admin_api_tokens_hash"),
        )
        op.create_index("ix_admin_api_tokens_active", "admin_api_tokens", ["admin_id", "revoked_at", "expires_at", "id"])

    if "admin_suspension_events" not in tables:
        op.create_table(
            "admin_suspension_events",
            sa.Column("id", _bigint_pk(), autoincrement=True, nullable=False),
            sa.Column("admin_id", sa.Integer(), nullable=False),
            sa.Column("actor_admin_id", sa.Integer(), nullable=False),
            sa.Column("reason_id", sa.SmallInteger(), nullable=False),
            sa.Column("limits_snapshot", sa.JSON(), nullable=True),
            sa.Column("status", sa.String(length=24), server_default="processing", nullable=False),
            sa.Column("started_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("resolved_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["admin_id"], ["admins.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["actor_admin_id"], ["admins.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["reason_id"], ["admin_suspension_reasons.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_admin_suspension_target_started", "admin_suspension_events", ["admin_id", "started_at", "id"])

    if "admin_suspension_users" not in tables:
        op.create_table(
            "admin_suspension_users",
            sa.Column("event_id", _bigint_pk(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("previous_status", sa.String(length=32), nullable=False),
            sa.Column("applied_status", sa.String(length=32), nullable=False),
            sa.Column("sync_status", sa.String(length=24), server_default="pending", nullable=False),
            sa.ForeignKeyConstraint(["event_id"], ["admin_suspension_events.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("event_id", "user_id"),
        )
        op.create_index("ix_admin_suspension_user_cursor", "admin_suspension_users", ["event_id", "sync_status", "user_id"])

    if "admin_bulk_jobs" not in tables:
        op.create_table(
            "admin_bulk_jobs",
            sa.Column("id", _bigint_pk(), autoincrement=True, nullable=False),
            sa.Column("actor_admin_id", sa.Integer(), nullable=False),
            sa.Column("target_admin_id", sa.Integer(), nullable=False),
            sa.Column("operation", sa.String(length=32), nullable=False),
            sa.Column("include_subtree", sa.Boolean(), server_default=sa.false(), nullable=False),
            sa.Column("status", sa.String(length=24), server_default="pending", nullable=False),
            sa.Column("total_count", sa.BigInteger(), server_default="0", nullable=False),
            sa.Column("processed_count", sa.BigInteger(), server_default="0", nullable=False),
            sa.Column("last_user_id", sa.Integer(), nullable=True),
            sa.Column("idempotency_key", sa.String(length=128), nullable=False),
            sa.Column("error", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["actor_admin_id"], ["admins.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["target_admin_id"], ["admins.id"], ondelete="RESTRICT"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("idempotency_key", name="uq_admin_bulk_jobs_idempotency_key"),
        )
        op.create_index("ix_admin_bulk_jobs_actor_created", "admin_bulk_jobs", ["actor_admin_id", "created_at", "id"])
        op.create_index("ix_admin_bulk_jobs_status_cursor", "admin_bulk_jobs", ["status", "last_user_id", "id"])

    if "admin_user_plans" not in tables:
        op.create_table(
            "admin_user_plans",
            sa.Column("id", _bigint_pk(), autoincrement=True, nullable=False),
            sa.Column("owner_admin_id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=128), nullable=False),
            sa.Column("description", sa.String(length=512), nullable=True),
            sa.Column("current_version_id", sa.BigInteger(), nullable=True),
            sa.Column("archived_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["owner_admin_id"], ["admins.id"], ondelete="RESTRICT"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("owner_admin_id", "name", name="uq_admin_user_plans_owner_name"),
        )
        op.create_index("ix_admin_user_plans_owner_active", "admin_user_plans", ["owner_admin_id", "archived_at", "id"])

    if "admin_user_plan_versions" not in tables:
        op.create_table(
            "admin_user_plan_versions",
            sa.Column("id", _bigint_pk(), autoincrement=True, nullable=False),
            sa.Column("plan_id", sa.BigInteger(), nullable=False),
            sa.Column("version_number", sa.Integer(), nullable=False),
            sa.Column("data_limit", sa.BigInteger(), nullable=False),
            sa.Column("duration_days", sa.Integer(), nullable=False),
            sa.Column("concurrent_user_limit", sa.Integer(), nullable=True),
            sa.Column("reset_strategy", sa.String(length=32), nullable=False),
            sa.Column("renewal_volume_strategy", sa.String(length=32), server_default="replace", nullable=False),
            sa.Column("renewal_time_strategy", sa.String(length=32), server_default="extend_max", nullable=False),
            sa.Column("created_by_admin_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.CheckConstraint("version_number > 0", name="ck_admin_plan_version_positive"),
            sa.ForeignKeyConstraint(["plan_id"], ["admin_user_plans.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["created_by_admin_id"], ["admins.id"], ondelete="RESTRICT"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("plan_id", "version_number", name="uq_admin_plan_version_number"),
        )

    if "admin_user_plan_inbounds" not in tables:
        op.create_table(
            "admin_user_plan_inbounds",
            sa.Column("version_id", sa.BigInteger(), nullable=False),
            sa.Column("inbound_tag", sa.String(length=256), nullable=False),
            sa.ForeignKeyConstraint(["version_id"], ["admin_user_plan_versions.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("version_id", "inbound_tag"),
        )

    if "admin_user_plan_access" not in tables:
        op.create_table(
            "admin_user_plan_access",
            sa.Column("admin_id", sa.Integer(), nullable=False),
            sa.Column("plan_id", sa.BigInteger(), nullable=False),
            sa.Column("include_subtree", sa.Boolean(), server_default=sa.false(), nullable=False),
            sa.ForeignKeyConstraint(["admin_id"], ["admins.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["plan_id"], ["admin_user_plans.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("admin_id", "plan_id"),
        )
        op.create_index("ix_admin_user_plan_access_plan_admin", "admin_user_plan_access", ["plan_id", "admin_id"])

    if "user_plan_assignments" not in tables:
        op.create_table(
            "user_plan_assignments",
            sa.Column("id", _bigint_pk(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("plan_id", sa.BigInteger(), nullable=False),
            sa.Column("version_id", sa.BigInteger(), nullable=False),
            sa.Column("actor_admin_id", sa.Integer(), nullable=False),
            sa.Column("operation_type", sa.String(length=24), nullable=False),
            sa.Column("idempotency_key", sa.String(length=128), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["plan_id"], ["admin_user_plans.id"]),
            sa.ForeignKeyConstraint(["version_id"], ["admin_user_plan_versions.id"]),
            sa.ForeignKeyConstraint(["actor_admin_id"], ["admins.id"], ondelete="RESTRICT"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("idempotency_key", name="uq_user_plan_assignment_idempotency_key"),
        )
        op.create_index("ix_user_plan_assignments_user_created", "user_plan_assignments", ["user_id", "created_at", "id"])

    # CREATE TABLE is atomic on MySQL 8.0, but a process can stop between the
    # table DDL and its following index DDL. Recreate every secondary index on
    # rerun without assuming which statement completed.
    for table, name, columns in (
        ("admin_credit_transfers", "ix_admin_credit_from_created", ["from_admin_id", "created_at", "id"]),
        ("admin_credit_transfers", "ix_admin_credit_to_created", ["to_admin_id", "created_at", "id"]),
        ("admin_credit_transfers", "ix_admin_credit_actor_created", ["actor_admin_id", "created_at", "id"]),
        ("admin_api_tokens", "ix_admin_api_tokens_active", ["admin_id", "revoked_at", "expires_at", "id"]),
        ("admin_suspension_events", "ix_admin_suspension_target_started", ["admin_id", "started_at", "id"]),
        ("admin_suspension_users", "ix_admin_suspension_user_cursor", ["event_id", "sync_status", "user_id"]),
        ("admin_bulk_jobs", "ix_admin_bulk_jobs_actor_created", ["actor_admin_id", "created_at", "id"]),
        ("admin_bulk_jobs", "ix_admin_bulk_jobs_status_cursor", ["status", "last_user_id", "id"]),
        ("admin_user_plans", "ix_admin_user_plans_owner_active", ["owner_admin_id", "archived_at", "id"]),
        ("admin_user_plan_access", "ix_admin_user_plan_access_plan_admin", ["plan_id", "admin_id"]),
        ("user_plan_assignments", "ix_user_plan_assignments_user_created", ["user_id", "created_at", "id"]),
    ):
        _ensure_index(table, name, columns)

    if "marzhelp_admin_settings" in _tables():
        settings_columns = (
            sa.Column("delegated_traffic", sa.BigInteger(), server_default="0", nullable=False),
            sa.Column("renewal_enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.Column("renewal_remaining", sa.BigInteger(), nullable=True),
            sa.Column("user_creation_mode_id", sa.SmallInteger(), server_default="1", nullable=False),
            sa.Column("can_manage_plans", sa.Boolean(), server_default=sa.false(), nullable=False),
            sa.Column("account_status_id", sa.SmallInteger(), server_default="1", nullable=False),
            sa.Column("suspended_reason_id", sa.SmallInteger(), nullable=True),
            sa.Column("suspended_at", sa.DateTime(), nullable=True),
            sa.Column("suspended_by_admin_id", sa.Integer(), nullable=True),
            sa.Column("suspension_event_id", sa.BigInteger(), nullable=True),
        )
        for column in settings_columns:
            _add_column("marzhelp_admin_settings", column)
        if {"renewal_limit", "renewals_used", "renewal_remaining"} <= _columns("marzhelp_admin_settings"):
            bind.execute(sa.text(
                "UPDATE marzhelp_admin_settings SET renewal_remaining = CASE "
                "WHEN renewal_limit IS NULL THEN NULL "
                "WHEN renewal_limit > renewals_used THEN renewal_limit - renewals_used ELSE 0 END "
                "WHERE renewal_remaining IS NULL"
            ))

    if bind.dialect.name == "mysql":
        mysql_constraints = (
            ("fk_admin_settings_creation_mode", "admin_user_creation_modes", ["user_creation_mode_id"], ["id"], None),
            ("fk_admin_settings_account_status", "admin_account_statuses", ["account_status_id"], ["id"], None),
            ("fk_admin_settings_suspension_reason", "admin_suspension_reasons", ["suspended_reason_id"], ["id"], None),
            ("fk_admin_settings_suspended_by", "admins", ["suspended_by_admin_id"], ["id"], "SET NULL"),
            ("fk_admin_settings_suspension_event", "admin_suspension_events", ["suspension_event_id"], ["id"], "SET NULL"),
        )
        if "marzhelp_admin_settings" in _tables():
            for name, target, local, remote, ondelete in mysql_constraints:
                if not _has_foreign_key_columns("marzhelp_admin_settings", local):
                    op.create_foreign_key(name, "marzhelp_admin_settings", target, local, remote, ondelete=ondelete)
        if not _has_foreign_key_columns("admin_user_plans", ["current_version_id"]):
            op.create_foreign_key(
                "fk_admin_user_plans_current_version",
                "admin_user_plans",
                "admin_user_plan_versions",
                ["current_version_id"],
                ["id"],
                ondelete="SET NULL",
            )


def upgrade() -> None:
    bind = op.get_bind()
    tables = _tables()

    if "admin_roles" not in tables:
        op.create_table(
            "admin_roles",
            sa.Column("id", sa.SmallInteger(), autoincrement=False, nullable=False),
            sa.Column("code", sa.String(length=32), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("code", name="uq_admin_roles_code"),
        )
    _seed_roles(bind)

    _add_column("admins", sa.Column("role_id", sa.SmallInteger(), nullable=True))
    _add_column("admins", sa.Column("parent_admin_id", sa.Integer(), nullable=True))
    _add_column(
        "admins",
        sa.Column(
            "external_api_enabled",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )
    _add_column(
        "admins",
        sa.Column("external_api_updated_by", sa.Integer(), nullable=True),
    )
    _add_column(
        "admins",
        sa.Column("external_api_updated_at", sa.DateTime(), nullable=True),
    )
    if not _has_index_columns("admins", ["parent_admin_id", "id"]):
        op.create_index(
            "ix_admins_parent_id",
            "admins",
            ["parent_admin_id", "id"],
            unique=False,
        )
    _ensure_mysql_foreign_keys()

    tables = _tables()
    if "admin_hierarchy_settings" not in tables:
        op.create_table(
            "admin_hierarchy_settings",
            sa.Column("id", sa.SmallInteger(), autoincrement=False, nullable=False),
            sa.Column(
                "enabled",
                sa.Boolean(),
                server_default=sa.false(),
                nullable=False,
            ),
            sa.Column(
                "max_depth",
                sa.Integer(),
                server_default="64",
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.CheckConstraint("id = 1", name="ck_admin_hierarchy_settings_singleton"),
            sa.CheckConstraint("max_depth > 0", name="ck_admin_hierarchy_settings_depth"),
        )
    if bind.scalar(
        sa.text("SELECT COUNT(*) FROM admin_hierarchy_settings WHERE id = 1")
    ) == 0:
        bind.execute(
            sa.text(
                "INSERT INTO admin_hierarchy_settings (id, enabled, max_depth) "
                "VALUES (1, false, 64)"
            )
        )

    tables = _tables()
    if "system_owner" not in tables:
        op.create_table(
            "system_owner",
            sa.Column("id", sa.SmallInteger(), autoincrement=False, nullable=False),
            sa.Column("admin_id", sa.Integer(), nullable=False),
            sa.Column(
                "assigned_at",
                sa.DateTime(),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.CheckConstraint("id = 1", name="ck_system_owner_singleton"),
            sa.ForeignKeyConstraint(
                ["admin_id"],
                ["admins.id"],
                name="fk_system_owner_admin_id_admins",
                ondelete="RESTRICT",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("admin_id", name="uq_system_owner_admin_id"),
        )

    tables = _tables()
    if "admin_hierarchy" not in tables:
        op.create_table(
            "admin_hierarchy",
            sa.Column("ancestor_id", sa.Integer(), nullable=False),
            sa.Column("descendant_id", sa.Integer(), nullable=False),
            sa.Column("depth", sa.Integer(), nullable=False),
            sa.CheckConstraint(
                "depth >= 0",
                name="ck_admin_hierarchy_depth_nonnegative",
            ),
            sa.ForeignKeyConstraint(
                ["ancestor_id"],
                ["admins.id"],
                name="fk_admin_hierarchy_ancestor_id_admins",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["descendant_id"],
                ["admins.id"],
                name="fk_admin_hierarchy_descendant_id_admins",
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("ancestor_id", "descendant_id"),
        )
    if not _has_index_columns(
        "admin_hierarchy",
        ["descendant_id", "ancestor_id", "depth"],
    ):
        op.create_index(
            "ix_admin_hierarchy_descendant_ancestor_depth",
            "admin_hierarchy",
            ["descendant_id", "ancestor_id", "depth"],
            unique=False,
        )

    _create_extended_schema(bind)

    # Self rows are factual and do not guess legacy parentage. The global flag
    # stays disabled until set-owner performs and verifies the real backfill.
    bind.execute(
        sa.text(
            "INSERT INTO admin_hierarchy (ancestor_id, descendant_id, depth) "
            "SELECT admins.id, admins.id, 0 FROM admins "
            "WHERE NOT EXISTS ("
            "SELECT 1 FROM admin_hierarchy "
            "WHERE admin_hierarchy.ancestor_id = admins.id "
            "AND admin_hierarchy.descendant_id = admins.id"
            ")"
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    tables = _tables()
    if bind.dialect.name == "mysql":
        if "admin_user_plans" in tables:
            plan_foreign_keys = {
                foreign_key.get("name") for foreign_key in _foreign_keys("admin_user_plans")
            }
            if "fk_admin_user_plans_current_version" in plan_foreign_keys:
                op.drop_constraint(
                    "fk_admin_user_plans_current_version",
                    "admin_user_plans",
                    type_="foreignkey",
                )
        if "marzhelp_admin_settings" in tables:
            settings_foreign_keys = {
                foreign_key.get("name") for foreign_key in _foreign_keys("marzhelp_admin_settings")
            }
            for name in (
                "fk_admin_settings_suspension_event",
                "fk_admin_settings_suspended_by",
                "fk_admin_settings_suspension_reason",
                "fk_admin_settings_account_status",
                "fk_admin_settings_creation_mode",
            ):
                if name in settings_foreign_keys:
                    op.drop_constraint(name, "marzhelp_admin_settings", type_="foreignkey")

    if "marzhelp_admin_settings" in tables:
        for column in (
            "suspension_event_id",
            "suspended_by_admin_id",
            "suspended_at",
            "suspended_reason_id",
            "account_status_id",
            "can_manage_plans",
            "user_creation_mode_id",
            "renewal_remaining",
            "renewal_enabled",
            "delegated_traffic",
        ):
            if column in _columns("marzhelp_admin_settings"):
                op.drop_column("marzhelp_admin_settings", column)

    for table in (
        "user_plan_assignments",
        "admin_user_plan_access",
        "admin_user_plan_inbounds",
        "admin_user_plan_versions",
        "admin_user_plans",
        "admin_bulk_jobs",
        "admin_suspension_users",
        "admin_suspension_events",
        "admin_api_tokens",
        "admin_credit_transfers",
        "admin_suspension_reasons",
        "admin_account_statuses",
        "admin_user_creation_modes",
    ):
        if table in _tables():
            op.drop_table(table)

    tables = _tables()
    for table in (
        "admin_hierarchy",
        "system_owner",
        "admin_hierarchy_settings",
    ):
        if table in tables:
            op.drop_table(table)

    if bind.dialect.name == "mysql":
        foreign_keys = {
            foreign_key.get("name")
            for foreign_key in _foreign_keys("admins")
        }
        for name in (
            "fk_admins_external_api_updated_by_admins",
            "fk_admins_parent_admin_id_admins",
            "fk_admins_role_id_admin_roles",
        ):
            if name in foreign_keys:
                op.drop_constraint(name, "admins", type_="foreignkey")

    if "ix_admins_parent_id" in {index.get("name") for index in _indexes("admins")}:
        op.drop_index("ix_admins_parent_id", table_name="admins")
    for column in (
        "external_api_updated_at",
        "external_api_updated_by",
        "external_api_enabled",
        "parent_admin_id",
        "role_id",
    ):
        if column in _columns("admins"):
            op.drop_column("admins", column)

    if "admin_roles" in _tables():
        op.drop_table("admin_roles")
