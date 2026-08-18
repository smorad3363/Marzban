import importlib.util
import os
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy.engine import make_url


MYSQL_URL = os.getenv("TEST_MYSQL_DATABASE_URL")
MIGRATION_PATH = (
    Path(__file__).parents[1]
    / "app"
    / "db"
    / "migrations"
    / "versions"
    / "e2a6c1f4b903_add_admin_hierarchy_foundation.py"
)


def _migration_module():
    spec = importlib.util.spec_from_file_location("mysql_admin_hierarchy_migration", MIGRATION_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _reset_test_schema(engine: sa.Engine) -> None:
    database = make_url(MYSQL_URL).database
    assert database and database.endswith("marzban_test")
    with engine.begin() as connection:
        connection.execute(sa.text("SET FOREIGN_KEY_CHECKS=0"))
        for table in sa.inspect(connection).get_table_names():
            connection.execute(sa.text(f"DROP TABLE `{table.replace('`', '``')}`"))
        connection.execute(sa.text("SET FOREIGN_KEY_CHECKS=1"))


def _upgrade(url: str, revision: str) -> None:
    alembic = Config("alembic.ini")
    alembic.set_main_option("sqlalchemy.url", url)
    command.upgrade(alembic, revision)


def _assert_extended_schema(connection: sa.Connection) -> None:
    inspector = sa.inspect(connection)
    tables = set(inspector.get_table_names())
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
    } <= tables
    assert {
        "role_id",
        "parent_admin_id",
        "external_api_enabled",
        "external_api_updated_by",
        "external_api_updated_at",
    } <= {column["name"] for column in inspector.get_columns("admins")}
    assert any(
        index.get("column_names") == ["descendant_id", "ancestor_id", "depth"]
        for index in inspector.get_indexes("admin_hierarchy")
    )
    create_sql = connection.execute(sa.text("SHOW CREATE TABLE admin_credit_transfers")).one()[1]
    assert "ENGINE=InnoDB" in create_sql
    for table in (
        "admin_roles",
        "admin_hierarchy_settings",
        "system_owner",
        "admin_user_creation_modes",
        "admin_account_statuses",
        "admin_suspension_reasons",
    ):
        create_sql = connection.execute(sa.text(f"SHOW CREATE TABLE `{table}`")).one()[1]
        assert "AUTO_INCREMENT" not in create_sql


@pytest.mark.skipif(not MYSQL_URL, reason="TEST_MYSQL_DATABASE_URL is not configured")
def test_mysql_hierarchy_fresh_legacy_partial_and_rerun():
    assert make_url(MYSQL_URL).get_backend_name() == "mysql"
    engine = sa.create_engine(MYSQL_URL, pool_pre_ping=True)

    _reset_test_schema(engine)
    _upgrade(MYSQL_URL, "head")
    with engine.begin() as connection:
        _assert_extended_schema(connection)
        module = _migration_module()
        module.op = Operations(MigrationContext.configure(connection))
        module.upgrade()
        _assert_extended_schema(connection)

    _reset_test_schema(engine)
    _upgrade(MYSQL_URL, "a41c8e7d5b92")
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "INSERT INTO admins "
                "(id, username, hashed_password, is_sudo, users_usage) "
                "VALUES (101, 'legacy-owner', 'x', 1, 0), "
                "(202, 'legacy-admin', 'x', 0, 0)"
            )
        )
        connection.execute(
            sa.text(
                "INSERT INTO marzhelp_admin_settings "
                "(admin_id, renewal_limit, renewals_used) VALUES (202, 7, 2)"
            )
        )
        connection.execute(sa.text("ALTER TABLE admins ADD COLUMN role_id SMALLINT NULL"))

    _upgrade(MYSQL_URL, "head")
    with engine.begin() as connection:
        _assert_extended_schema(connection)
        assert connection.execute(
            sa.text("SELECT id, username, is_sudo, role_id, parent_admin_id FROM admins ORDER BY id")
        ).all() == [
            (101, "legacy-owner", True, None, None),
            (202, "legacy-admin", False, None, None),
        ]
        assert connection.execute(
            sa.text(
                "SELECT renewal_limit, renewals_used, renewal_remaining "
                "FROM marzhelp_admin_settings WHERE admin_id = 202"
            )
        ).one() == (7, 2, 5)
        module = _migration_module()
        module.op = Operations(MigrationContext.configure(connection))
        module.upgrade()
        assert connection.scalar(sa.text("SELECT COUNT(*) FROM admin_roles")) == 3
        assert connection.scalar(sa.text("SELECT COUNT(*) FROM admin_hierarchy_settings")) == 1

    engine.dispose()
