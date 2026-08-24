import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


MIGRATION_PATH = Path(__file__).parents[1] / "app" / "db" / "migrations" / "versions" / "8b7d3e5f1a24_add_delegated_admin_creation_branding.py"


def _module():
    spec = importlib.util.spec_from_file_location("admin_creation_branding_migration", MIGRATION_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_contains_mysql_fk_index_downgrade_guard():
    source = MIGRATION_PATH.read_text(encoding="utf-8")
    assert 'op.get_bind().dialect.name == "mysql"' in source
    assert '"ix_marzhelp_admin_settings_account_status_id"' in source
    assert source.index('"ix_marzhelp_admin_settings_account_status_id"') < source.index(
        'for name in (\n            "ix_marzhelp_admin_settings_status_admin"'
    )


def test_admin_creation_branding_upgrade_is_additive_backfilled_and_rerunnable(monkeypatch):
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(sa.text("CREATE TABLE admin_roles (id INTEGER PRIMARY KEY, code VARCHAR(32) NOT NULL UNIQUE)"))
        connection.execute(sa.text("CREATE TABLE admins (id INTEGER PRIMARY KEY, username VARCHAR(34), role_id INTEGER)"))
        connection.execute(sa.text(
            "CREATE TABLE marzhelp_admin_settings ("
            "admin_id INTEGER PRIMARY KEY, billing_mode VARCHAR(32), account_status_id INTEGER NOT NULL DEFAULT 1, "
            "trial_quota BIGINT NOT NULL DEFAULT 0, trials_used BIGINT NOT NULL DEFAULT 0)"
        ))
        connection.execute(sa.text("INSERT INTO admin_roles (id, code) VALUES (1, 'OWNER'), (2, 'SUPER_ADMIN'), (3, 'ADMIN')"))
        connection.execute(sa.text("INSERT INTO admins (id, username, role_id) VALUES (1, 'owner', 1), (2, 'super', 2), (3, 'admin', 3)"))
        connection.execute(sa.text(
            "INSERT INTO marzhelp_admin_settings (admin_id, billing_mode, trial_quota, trials_used) VALUES "
            "(1, 'USED_TRAFFIC', 5, 2), (2, 'ALLOCATED_TRAFFIC', 0, 0), (3, 'USER_CREDIT', 1, 1)"
        ))
        migration = _module()
        monkeypatch.setattr(migration, "op", Operations(MigrationContext.configure(connection)))
        migration.upgrade()
        migration.upgrade()

        admin_columns = {column["name"] for column in sa.inspect(connection).get_columns("admins")}
        policy_columns = {column["name"] for column in sa.inspect(connection).get_columns("marzhelp_admin_settings")}
        indexes = {index["name"] for index in sa.inspect(connection).get_indexes("marzhelp_admin_settings")}
        assert {"dashboard_theme", "logo_filename"} <= admin_columns
        assert {
            "trial_quota_limit", "can_create_admins", "can_delegate_admin_creation",
            "can_create_allocated_children", "admin_creation_limit", "admin_creations_used",
            "delegated_admin_creation_limit",
        } <= policy_columns
        assert {
            "ix_marzhelp_admin_settings_billing_admin",
            "ix_marzhelp_admin_settings_status_admin",
        } <= indexes
        rows = connection.execute(sa.text(
            "SELECT admin_id, trial_quota_limit, can_create_admins, can_delegate_admin_creation "
            "FROM marzhelp_admin_settings ORDER BY admin_id"
        )).all()
        assert rows == [(1, 7, 1, 1), (2, 0, 1, 1), (3, 2, 0, 0)]
    engine.dispose()
