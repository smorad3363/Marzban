import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy.dialects import mysql
from sqlalchemy.schema import CreateTable

from app.db.models import (
    AdminAccountStatus,
    AdminApiToken,
    AdminHierarchySettings,
    AdminRole,
    AdminSuspensionReason,
    AdminUserCreationMode,
    SystemOwner,
)


MIGRATION_PATH = (
    Path(__file__).parents[1]
    / "app"
    / "db"
    / "migrations"
    / "versions"
    / "e2a6c1f4b903_add_admin_hierarchy_foundation.py"
)
MIGRATION_SPEC = importlib.util.spec_from_file_location(
    "admin_hierarchy_migration",
    MIGRATION_PATH,
)
assert MIGRATION_SPEC and MIGRATION_SPEC.loader
migration = importlib.util.module_from_spec(MIGRATION_SPEC)
MIGRATION_SPEC.loader.exec_module(migration)

CATEGORY_MIGRATION_PATH = (
    Path(__file__).parents[1]
    / "app"
    / "db"
    / "migrations"
    / "versions"
    / "4f9c3a2b1d06_add_plan_categories.py"
)
CATEGORY_MIGRATION_SPEC = importlib.util.spec_from_file_location(
    "admin_plan_category_migration",
    CATEGORY_MIGRATION_PATH,
)
assert CATEGORY_MIGRATION_SPEC and CATEGORY_MIGRATION_SPEC.loader
category_migration = importlib.util.module_from_spec(CATEGORY_MIGRATION_SPEC)
CATEGORY_MIGRATION_SPEC.loader.exec_module(category_migration)

LEDGER_MIGRATION_PATH = (
    Path(__file__).parents[1]
    / "app"
    / "db"
    / "migrations"
    / "versions"
    / "7d2c6a4e9b10_expand_admin_credit_ledger.py"
)
LEDGER_MIGRATION_SPEC = importlib.util.spec_from_file_location(
    "admin_credit_ledger_migration",
    LEDGER_MIGRATION_PATH,
)
assert LEDGER_MIGRATION_SPEC and LEDGER_MIGRATION_SPEC.loader
ledger_migration = importlib.util.module_from_spec(LEDGER_MIGRATION_SPEC)
LEDGER_MIGRATION_SPEC.loader.exec_module(ledger_migration)

PLAN_HOST_MIGRATION_PATH = (
    Path(__file__).parents[1]
    / "app"
    / "db"
    / "migrations"
    / "versions"
    / "9f6a2c8d4e10_add_explicit_plan_host_scope.py"
)
PLAN_HOST_MIGRATION_SPEC = importlib.util.spec_from_file_location(
    "explicit_plan_host_scope_migration",
    PLAN_HOST_MIGRATION_PATH,
)
assert PLAN_HOST_MIGRATION_SPEC and PLAN_HOST_MIGRATION_SPEC.loader
plan_host_migration = importlib.util.module_from_spec(PLAN_HOST_MIGRATION_SPEC)
PLAN_HOST_MIGRATION_SPEC.loader.exec_module(plan_host_migration)

NAMESPACE_MIGRATION_PATH = (
    Path(__file__).parents[1]
    / "app"
    / "db"
    / "migrations"
    / "versions"
    / "3a7e5c1b8d42_add_admin_user_namespace.py"
)
NAMESPACE_MIGRATION_SPEC = importlib.util.spec_from_file_location(
    "admin_user_namespace_migration",
    NAMESPACE_MIGRATION_PATH,
)
assert NAMESPACE_MIGRATION_SPEC and NAMESPACE_MIGRATION_SPEC.loader
namespace_migration = importlib.util.module_from_spec(NAMESPACE_MIGRATION_SPEC)
NAMESPACE_MIGRATION_SPEC.loader.exec_module(namespace_migration)


def test_fixed_identifier_tables_do_not_compile_mysql_auto_increment():
    for model in (
        AdminRole,
        AdminHierarchySettings,
        SystemOwner,
        AdminUserCreationMode,
        AdminAccountStatus,
        AdminSuspensionReason,
    ):
        ddl = str(CreateTable(model.__table__).compile(dialect=mysql.dialect()))
        assert "AUTO_INCREMENT" not in ddl


def test_api_token_hash_compiles_as_indexable_mysql_binary():
    ddl = str(CreateTable(AdminApiToken.__table__).compile(dialect=mysql.dialect()))
    assert "token_hash BINARY(32)" in ddl
    assert "token_hash BLOB" not in ddl
    assert "UNIQUE (token_hash)" in ddl


def _legacy_schema(connection: sa.Connection) -> None:
    connection.execute(
        sa.text(
            "CREATE TABLE admins ("
            "id INTEGER PRIMARY KEY, username VARCHAR(34) NOT NULL, "
            "is_sudo BOOLEAN NOT NULL DEFAULT 0)"
        )
    )


def _upgrade(connection: sa.Connection, monkeypatch) -> None:
    operations = Operations(MigrationContext.configure(connection))
    monkeypatch.setattr(migration, "op", operations)
    migration.upgrade()


def _upgrade_categories(connection: sa.Connection, monkeypatch) -> None:
    operations = Operations(MigrationContext.configure(connection))
    monkeypatch.setattr(category_migration, "op", operations)
    category_migration.upgrade()


def _upgrade_ledger(connection: sa.Connection, monkeypatch) -> None:
    operations = Operations(MigrationContext.configure(connection))
    monkeypatch.setattr(ledger_migration, "op", operations)
    ledger_migration.upgrade()


def _upgrade_plan_hosts(connection: sa.Connection, monkeypatch) -> None:
    operations = Operations(MigrationContext.configure(connection))
    monkeypatch.setattr(plan_host_migration, "op", operations)
    plan_host_migration.upgrade()


def _upgrade_namespace(connection: sa.Connection, monkeypatch) -> None:
    operations = Operations(MigrationContext.configure(connection))
    monkeypatch.setattr(namespace_migration, "op", operations)
    namespace_migration.upgrade()


def test_namespace_upgrade_backfills_admins_without_renaming_users_and_reruns(monkeypatch):
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        _legacy_schema(connection)
        connection.execute(
            sa.text(
                "CREATE TABLE users (id INTEGER PRIMARY KEY, username VARCHAR(34) NOT NULL UNIQUE)"
            )
        )
        connection.execute(
            sa.text(
                "INSERT INTO admins (id, username, is_sudo) VALUES "
                "(10, 'owner-login', 1), (20, 'child-login', 0)"
            )
        )
        connection.execute(
            sa.text("INSERT INTO users (id, username) VALUES (1, 'legacy-customer')")
        )

        _upgrade_namespace(connection, monkeypatch)
        first = connection.execute(
            sa.text(
                "SELECT id, username, user_namespace_prefix FROM admins ORDER BY id"
            )
        ).all()
        _upgrade_namespace(connection, monkeypatch)

        assert first == connection.execute(
            sa.text(
                "SELECT id, username, user_namespace_prefix FROM admins ORDER BY id"
            )
        ).all()
        assert first[0][2] != first[1][2]
        assert connection.scalar(sa.text("SELECT username FROM users WHERE id = 1")) == "legacy-customer"
        indexes = sa.inspect(connection).get_indexes("admins")
        assert any(
            index.get("name") == "uq_admins_user_namespace_prefix"
            and index.get("unique")
            for index in indexes
        )


def test_explicit_plan_host_scope_upgrade_is_additive_and_rerunnable(monkeypatch):
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        _legacy_schema(connection)
        _upgrade(connection, monkeypatch)
        _upgrade_plan_hosts(connection, monkeypatch)
        _upgrade_plan_hosts(connection, monkeypatch)

        inspector = sa.inspect(connection)
        assert "admin_user_plan_hosts" in inspector.get_table_names()
        assert inspector.get_pk_constraint("admin_user_plan_hosts")["constrained_columns"] == [
            "version_id",
            "inbound_tag",
            "host_id",
        ]
        assert connection.scalar(
            sa.text("SELECT COUNT(*) FROM admin_user_plan_hosts")
        ) == 0


def test_credit_ledger_upgrade_backfills_legacy_rows_and_is_rerunnable(monkeypatch):
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        _legacy_schema(connection)
        connection.execute(
            sa.text(
                "INSERT INTO admins (id, username, is_sudo) VALUES "
                "(10, 'owner', 1), (20, 'child', 0)"
            )
        )
        _upgrade(connection, monkeypatch)
        connection.execute(
            sa.text(
                "INSERT INTO admin_credit_transfers "
                "(id, from_admin_id, to_admin_id, actor_admin_id, amount, operation_type, "
                "idempotency_key, created_at, note) VALUES "
                "(1, 10, 20, 10, 300, 'grant', 'legacy-grant', CURRENT_TIMESTAMP, 'legacy')"
            )
        )

        _upgrade_ledger(connection, monkeypatch)
        _upgrade_ledger(connection, monkeypatch)

        columns = {
            column["name"]
            for column in sa.inspect(connection).get_columns("admin_credit_transfers")
        }
        assert {
            "adjusted_admin_id",
            "resource",
            "delta",
            "balance_before",
            "balance_after",
            "source_delegated_before",
            "source_delegated_after",
        } <= columns
        assert connection.execute(
            sa.text(
                "SELECT adjusted_admin_id, resource, delta, balance_before, balance_after "
                "FROM admin_credit_transfers WHERE id = 1"
            )
        ).one() == (20, "traffic_credit", 300, None, None)
        assert sum(
            index.get("name") == "ix_admin_credit_adjusted_created"
            for index in sa.inspect(connection).get_indexes("admin_credit_transfers")
        ) == 1


def test_upgrade_adds_disabled_hierarchy_without_guessing_legacy_parents(monkeypatch):
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        _legacy_schema(connection)
        connection.execute(
            sa.text(
                "INSERT INTO admins (id, username, is_sudo) VALUES "
                "(10, 'legacy-sudo', 1), (20, 'legacy-admin', 0)"
            )
        )

        _upgrade(connection, monkeypatch)

        inspector = sa.inspect(connection)
        assert {
            "admin_roles",
            "admin_hierarchy_settings",
            "system_owner",
            "admin_hierarchy",
            "admin_credit_transfers",
            "admin_api_tokens",
            "admin_suspension_events",
            "admin_suspension_users",
            "admin_bulk_jobs",
            "admin_user_plans",
            "admin_user_plan_versions",
            "admin_user_plan_inbounds",
            "admin_user_plan_access",
            "user_plan_assignments",
        } <= set(inspector.get_table_names())
        assert {
            "role_id",
            "parent_admin_id",
            "external_api_enabled",
            "external_api_updated_by",
            "external_api_updated_at",
        } <= {column["name"] for column in inspector.get_columns("admins")}
        assert any(
            index.get("column_names") == ["parent_admin_id", "id"]
            for index in inspector.get_indexes("admins")
        )
        assert inspector.get_pk_constraint("admin_hierarchy")["constrained_columns"] == [
            "ancestor_id",
            "descendant_id",
        ]
        assert any(
            index.get("column_names")
            == ["descendant_id", "ancestor_id", "depth"]
            for index in inspector.get_indexes("admin_hierarchy")
        )

        assert connection.execute(
            sa.text("SELECT id, code FROM admin_roles ORDER BY id")
        ).all() == [(1, "OWNER"), (2, "SUPER_ADMIN"), (3, "ADMIN")]
        assert connection.execute(
            sa.text("SELECT id, code FROM admin_user_creation_modes ORDER BY id")
        ).all() == [(1, "FREE_FORM"), (2, "PLAN_ONLY")]
        assert connection.execute(
            sa.text("SELECT id, code FROM admin_account_statuses ORDER BY id")
        ).all() == [(1, "ACTIVE"), (2, "SUSPENDED"), (3, "DISABLED")]
        assert connection.execute(
            sa.text(
                "SELECT id, enabled, max_depth FROM admin_hierarchy_settings"
            )
        ).all() == [(1, False, 64)]
        assert connection.scalar(sa.text("SELECT COUNT(*) FROM system_owner")) == 0
        assert connection.execute(
            sa.text(
                "SELECT id, is_sudo, role_id, parent_admin_id, "
                "external_api_enabled FROM admins ORDER BY id"
            )
        ).all() == [(10, True, None, None, False), (20, False, None, None, False)]
        assert connection.execute(
            sa.text(
                "SELECT ancestor_id, descendant_id, depth "
                "FROM admin_hierarchy ORDER BY ancestor_id"
            )
        ).all() == [(10, 10, 0), (20, 20, 0)]


def test_plan_category_upgrade_preserves_existing_plans(monkeypatch):
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        _legacy_schema(connection)
        connection.execute(
            sa.text(
                "INSERT INTO admins (id, username, is_sudo) "
                "VALUES (10, 'legacy-sudo', 1)"
            )
        )
        _upgrade(connection, monkeypatch)
        connection.execute(
            sa.text(
                "INSERT INTO admin_user_plans "
                "(id, owner_admin_id, name, current_version_id, archived_at, created_at, updated_at) "
                "VALUES (100, 10, 'legacy-plan', NULL, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            )
        )

        _upgrade_categories(connection, monkeypatch)

        inspector = sa.inspect(connection)
        assert {"admin_plan_categories", "admin_plan_category_access"} <= set(
            inspector.get_table_names()
        )
        assert "category_id" in {
            column["name"] for column in inspector.get_columns("admin_user_plans")
        }
        assert any(
            index.get("column_names") == ["category_id", "archived_at", "id"]
            for index in inspector.get_indexes("admin_user_plans")
        )
        assert connection.execute(
            sa.text(
                "SELECT id, owner_admin_id, name, category_id "
                "FROM admin_user_plans WHERE id = 100"
            )
        ).one() == (100, 10, "legacy-plan", None)


def test_upgrade_is_safe_to_rerun_after_partial_admin_column_ddl(monkeypatch):
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        _legacy_schema(connection)
        connection.execute(sa.text("ALTER TABLE admins ADD COLUMN role_id SMALLINT"))
        connection.execute(
            sa.text(
                "INSERT INTO admins (id, username, is_sudo, role_id) "
                "VALUES (7, 'partial', 1, NULL)"
            )
        )

        _upgrade(connection, monkeypatch)
        _upgrade(connection, monkeypatch)

        assert connection.scalar(sa.text("SELECT COUNT(*) FROM admin_roles")) == 3
        assert connection.scalar(
            sa.text("SELECT COUNT(*) FROM admin_hierarchy_settings")
        ) == 1
        assert connection.scalar(sa.text("SELECT COUNT(*) FROM admin_hierarchy")) == 1
        assert connection.execute(
            sa.text(
                "SELECT is_sudo, role_id, parent_admin_id, external_api_enabled "
                "FROM admins WHERE id = 7"
            )
        ).one() == (True, None, None, False)


def test_upgrade_backfills_canonical_renewal_state_without_changing_legacy_values(monkeypatch):
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        _legacy_schema(connection)
        connection.execute(
            sa.text(
                "CREATE TABLE users (id INTEGER PRIMARY KEY, admin_id INTEGER, status VARCHAR(32))"
            )
        )
        connection.execute(
            sa.text(
                "CREATE TABLE marzhelp_admin_settings ("
                "admin_id INTEGER PRIMARY KEY, renewal_limit BIGINT, "
                "renewals_used BIGINT NOT NULL DEFAULT 0)"
            )
        )
        connection.execute(
            sa.text("INSERT INTO admins (id, username, is_sudo) VALUES (1, 'legacy', 1)")
        )
        connection.execute(
            sa.text(
                "INSERT INTO marzhelp_admin_settings (admin_id, renewal_limit, renewals_used) "
                "VALUES (1, 5, 2)"
            )
        )

        _upgrade(connection, monkeypatch)
        _upgrade(connection, monkeypatch)

        row = connection.execute(
            sa.text(
                "SELECT renewal_limit, renewals_used, renewal_enabled, renewal_remaining, "
                "delegated_traffic, user_creation_mode_id, account_status_id "
                "FROM marzhelp_admin_settings WHERE admin_id = 1"
            )
        ).one()
        assert row == (5, 2, True, 3, 0, 1, 1)
