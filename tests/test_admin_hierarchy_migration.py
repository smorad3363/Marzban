import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


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
