import os

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url


MYSQL_URL = os.getenv("TEST_MYSQL_DATABASE_URL")


@pytest.mark.skipif(not MYSQL_URL, reason="TEST_MYSQL_DATABASE_URL is not configured")
def test_device_limit_migration_recovers_from_mysql_partial_ddl():
    assert make_url(MYSQL_URL).get_backend_name() == "mysql"
    alembic = Config("alembic.ini")
    alembic.set_main_option("sqlalchemy.url", MYSQL_URL)

    command.upgrade(alembic, "f42c0e8a7d31")

    engine = create_engine(MYSQL_URL, pool_pre_ping=True)
    with engine.begin() as connection:
        columns = {
            column["name"]
            for column in inspect(connection).get_columns("marzhelp_admin_settings")
        }
        if "view_full_client_ip" not in columns:
            connection.execute(
                text(
                    "ALTER TABLE marzhelp_admin_settings "
                    "ADD COLUMN view_full_client_ip BOOL NOT NULL DEFAULT false"
                )
            )
        connection.execute(
            text(
                "CREATE TABLE IF NOT EXISTS marzhelp_admin_allowed_subscription_modes ("
                "admin_id INTEGER NOT NULL, "
                "mode VARCHAR(48) NOT NULL, "
                "PRIMARY KEY (admin_id, mode), "
                "FOREIGN KEY (admin_id) REFERENCES marzhelp_admin_settings (admin_id) "
                "ON DELETE CASCADE"
                ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
            )
        )

    command.upgrade(alembic, "head")

    with engine.connect() as connection:
        tables = set(inspect(connection).get_table_names())
        assert {
            "device_limit_settings",
            "device_limit_penalty_stages",
            "device_slots",
            "device_limit_user_states",
            "device_limit_incidents",
        } <= tables
        settings = connection.execute(
            text("SELECT enabled, enforcement_mode FROM device_limit_settings WHERE id = 1")
        ).one()
        assert settings == (False, "hybrid")
        create_sql = connection.execute(
            text("SHOW CREATE TABLE device_limit_settings")
        ).one()[1].upper()
        assert "AUTO_INCREMENT" not in create_sql
        assert "CK_DEVICE_LIMIT_SETTINGS_SINGLETON" not in create_sql

    engine.dispose()
