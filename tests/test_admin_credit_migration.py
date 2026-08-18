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
    / "a41c8e7d5b92_unify_admin_credit_and_allowance.py"
)
MIGRATION_SPEC = importlib.util.spec_from_file_location("admin_credit_migration", MIGRATION_PATH)
assert MIGRATION_SPEC and MIGRATION_SPEC.loader
migration = importlib.util.module_from_spec(MIGRATION_SPEC)
MIGRATION_SPEC.loader.exec_module(migration)


def test_upgrade_backfills_non_refundable_allocated_credit(monkeypatch):
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        for statement in (
            "CREATE TABLE marzhelp_admin_settings ("
            "admin_id INTEGER PRIMARY KEY, used_traffic BIGINT NOT NULL DEFAULT 0, "
            "calculate_volume VARCHAR(50) NOT NULL)",
            "CREATE TABLE users ("
            "id INTEGER PRIMARY KEY, admin_id INTEGER, data_limit BIGINT, used_traffic BIGINT)",
            "CREATE TABLE marzhelp_deleted_users ("
            "id INTEGER PRIMARY KEY, admin_id INTEGER, allocated_traffic BIGINT, "
            "used_traffic_total BIGINT NOT NULL DEFAULT 0)",
            "CREATE TABLE user_usage_logs ("
            "id INTEGER PRIMARY KEY, user_id INTEGER, used_traffic_at_reset BIGINT NOT NULL)",
        ):
            connection.execute(sa.text(statement))
        connection.execute(
            sa.text(
                "INSERT INTO marzhelp_admin_settings "
                "(admin_id, used_traffic, calculate_volume) VALUES "
                "(1, 10, 'created_traffic'), (2, 40, 'used_traffic')"
            )
        )
        connection.execute(
            sa.text(
                "INSERT INTO users (id, admin_id, data_limit, used_traffic) VALUES "
                "(1, 1, 100, 20), (2, 1, NULL, 30)"
            )
        )
        connection.execute(
            sa.text(
                "INSERT INTO marzhelp_deleted_users "
                "(id, admin_id, allocated_traffic, used_traffic_total) "
                "VALUES (1, 1, 50, 50)"
            )
        )

        operations = Operations(MigrationContext.configure(connection))
        monkeypatch.setattr(migration, "op", operations)
        migration.upgrade()

        rows = dict(
            connection.execute(
                sa.text("SELECT admin_id, used_traffic FROM marzhelp_admin_settings")
            ).all()
        )
        assert rows == {1: 180, 2: 40}
        thresholds = connection.execute(
            sa.text(
                "SELECT admin_traffic_warning_percent, sudo_traffic_warning_percent "
                "FROM marzhelp_admin_settings WHERE admin_id = 1"
            )
        ).one()
        assert thresholds == (80, 80)
        assert any(
            index.get("column_names") == ["user_id"]
            for index in sa.inspect(connection).get_indexes("user_usage_logs")
        )
