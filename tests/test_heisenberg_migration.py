import importlib.util
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

MIGRATION_PATH = (
    Path(__file__).parents[1]
    / "app"
    / "db"
    / "migrations"
    / "versions"
    / "d7f3a2c9e104_heisenberg_capabilities_and_quotas.py"
)
MIGRATION_SPEC = importlib.util.spec_from_file_location("heisenberg_migration", MIGRATION_PATH)
assert MIGRATION_SPEC and MIGRATION_SPEC.loader
migration = importlib.util.module_from_spec(MIGRATION_SPEC)
MIGRATION_SPEC.loader.exec_module(migration)


def _legacy_schema(connection: sa.Connection) -> None:
    statements = (
        "CREATE TABLE admins (id INTEGER PRIMARY KEY)",
        "CREATE TABLE users (id INTEGER PRIMARY KEY, admin_id INTEGER, data_limit BIGINT)",
        "CREATE TABLE device_slots (id INTEGER PRIMARY KEY)",
        "CREATE TABLE device_limit_settings ("
        "id INTEGER PRIMARY KEY, enabled BOOLEAN NOT NULL DEFAULT 1, "
        "enforcement_mode VARCHAR(16) NOT NULL, hit_threshold INTEGER NOT NULL)",
        "CREATE TABLE device_limit_user_states (user_id INTEGER PRIMARY KEY)",
        "CREATE TABLE device_limit_incidents ("
        "id INTEGER PRIMARY KEY, action VARCHAR(32) NOT NULL, resolved_at DATETIME)",
        "CREATE TABLE marzhelp_admin_settings (admin_id INTEGER PRIMARY KEY, max_users BIGINT)",
        "CREATE TABLE marzhelp_accounting_transactions (id INTEGER PRIMARY KEY)",
    )
    for statement in statements:
        connection.execute(sa.text(statement))


@pytest.mark.parametrize(
    ("legacy_mode", "ip_detection_enabled"),
    (("slots", False), ("ip", True), ("hybrid", True)),
)
def test_heisenberg_upgrade_maps_legacy_settings_and_backfills_quotas(
    monkeypatch: pytest.MonkeyPatch,
    legacy_mode: str,
    ip_detection_enabled: bool,
):
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        _legacy_schema(connection)
        connection.execute(sa.text("INSERT INTO admins (id) VALUES (1)"))
        connection.execute(
            sa.text(
                "INSERT INTO users (id, admin_id, data_limit) VALUES "
                "(1, 1, 100), (2, 1, NULL), (3, 999, 50)"
            )
        )
        connection.execute(
            sa.text(
                "INSERT INTO device_limit_settings "
                "(id, enforcement_mode, hit_threshold) VALUES (1, :mode, 7)"
            ),
            {"mode": legacy_mode},
        )
        connection.execute(
            sa.text(
                "INSERT INTO device_limit_incidents (id, action, resolved_at) "
                "VALUES (1, 'warn', NULL)"
            )
        )
        connection.execute(
            sa.text(
                "INSERT INTO marzhelp_admin_settings (admin_id, max_users) VALUES (1, 12)"
            )
        )

        operations = Operations(MigrationContext.configure(connection))
        monkeypatch.setattr(migration, "op", operations)
        migration.upgrade()

        settings = connection.execute(
            sa.text(
                "SELECT device_slots_enabled, ip_detection_enabled, "
                "client_fingerprint_enabled, min_successful_connections "
                "FROM device_limit_settings WHERE id = 1"
            )
        ).mappings().one()
        assert bool(settings["device_slots_enabled"]) is True
        assert bool(settings["ip_detection_enabled"]) is ip_detection_enabled
        assert bool(settings["client_fingerprint_enabled"]) is False
        assert settings["min_successful_connections"] == 7

        quota = connection.execute(
            sa.text(
                "SELECT max_users, device_capacity_limit, user_count_used, "
                "provisioning_volume_used FROM marzhelp_admin_settings WHERE admin_id = 1"
            )
        ).mappings().one()
        assert quota["max_users"] == 12
        assert quota["device_capacity_limit"] == 12
        assert quota["user_count_used"] == 2
        assert quota["provisioning_volume_used"] == 100

        assert connection.scalar(sa.text("SELECT admin_id FROM users WHERE id = 3")) is None
        assert connection.scalar(
            sa.text("SELECT event_state FROM device_limit_incidents WHERE id = 1")
        ) == "warning"

        inspector = sa.inspect(connection)
        assert "device_client_observations" in inspector.get_table_names()
        observation_indexes = {
            index["name"] for index in inspector.get_indexes("device_client_observations")
        }
        assert {
            "ix_device_client_observation_user_slot_seen",
            "ix_device_client_observation_user_seen",
            "ix_device_client_observation_slot",
        } <= observation_indexes
        assert "ix_device_limit_incidents_warning_expiry" in {
            index["name"] for index in inspector.get_indexes("device_limit_incidents")
        }
