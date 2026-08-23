import os
from datetime import datetime, timedelta
from time import perf_counter

import pytest
import sqlalchemy as sa
from OpenSSL import crypto
from alembic import command
from alembic.config import Config
from sqlalchemy.engine import make_url


MYSQL_URL = os.getenv("TEST_MYSQL_DATABASE_URL")


def _ensure_database():
    parsed = make_url(MYSQL_URL)
    database = parsed.database
    assert database and database.startswith("stage10_") and database.endswith("_test")
    engine = sa.create_engine(parsed.set(database="mysql"), pool_pre_ping=True)
    try:
        with engine.begin() as connection:
            quoted = database.replace("`", "``")
            connection.execute(sa.text(
                f"CREATE DATABASE IF NOT EXISTS `{quoted}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            ))
    finally:
        engine.dispose()


def _reset(engine):
    with engine.begin() as connection:
        connection.execute(sa.text("SET FOREIGN_KEY_CHECKS=0"))
        for table in sa.inspect(connection).get_table_names():
            connection.execute(sa.text(f"DROP TABLE `{table.replace('`', '``')}`"))
        connection.execute(sa.text("SET FOREIGN_KEY_CHECKS=1"))


def _migrate(revision, downgrade=False):
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", MYSQL_URL)
    (command.downgrade if downgrade else command.upgrade)(config, revision)


@pytest.mark.skipif(not MYSQL_URL, reason="TEST_MYSQL_DATABASE_URL is required")
def test_mysql_stage10_migration_indexes_explain_and_deep_offset_timing(monkeypatch):
    _ensure_database()
    engine = sa.create_engine(MYSQL_URL, pool_pre_ping=True)
    _reset(engine)
    original_not_after = crypto.X509.gmtime_adj_notAfter
    monkeypatch.setattr(
        crypto.X509, "gmtime_adj_notAfter",
        lambda certificate, seconds: original_not_after(certificate, min(seconds, 2_000_000_000)),
    )
    _migrate("6d4f2a9c8e10")
    _migrate("head")
    with engine.begin() as connection:
        assert connection.execute(sa.text("SELECT VERSION()" )).scalar().startswith("8.0.")
        assert connection.execute(sa.text("SHOW TABLE STATUS LIKE 'users'" )).mappings().one()["Engine"] == "InnoDB"
        indexes = {row["name"] for row in sa.inspect(connection).get_indexes("users")}
        assert {"ix_users_status_created_id", "ix_users_admin_created_id"} <= indexes

    _migrate("6d4f2a9c8e10", downgrade=True)
    indexes = {row["name"] for row in sa.inspect(engine).get_indexes("users")}
    assert "ix_users_status_created_id" not in indexes
    assert "ix_users_admin_created_id" not in indexes
    _migrate("head")

    with engine.begin() as connection:
        connection.execute(sa.text(
            "INSERT INTO admins (username, hashed_password, is_sudo, phone) VALUES ('stage10-owner', 'x', 1, '+1')"
        ))
        admin_id = connection.execute(sa.text(
            "SELECT id FROM admins WHERE username='stage10-owner'"
        )).scalar_one()
        started = datetime(2026, 1, 1)
        insert = sa.text(
            "INSERT INTO users (username,status,used_traffic,data_limit,created_at,admin_id,data_limit_reset_strategy) "
            "VALUES (:username,:status,0,1000,:created_at,:admin_id,'no_reset')"
        )
        for batch_start in range(0, 10_000, 1_000):
            connection.execute(insert, [
                {
                    "username": f"stage10-user-{index:05d}",
                    "status": "active" if index % 2 else "disabled",
                    "created_at": started + timedelta(seconds=index),
                    "admin_id": admin_id,
                }
                for index in range(batch_start, batch_start + 1_000)
            ])

    with engine.connect() as connection:
        status_plan = connection.execute(sa.text(
            "EXPLAIN SELECT id FROM users WHERE status='active' ORDER BY created_at DESC,id DESC LIMIT 50"
        )).mappings().one()
        admin_plan = connection.execute(sa.text(
            "EXPLAIN SELECT id FROM users WHERE admin_id=:admin_id ORDER BY created_at DESC,id DESC LIMIT 50"
        ), {"admin_id": admin_id}).mappings().one()
        assert status_plan["key"] == "ix_users_status_created_id"
        assert admin_plan["key"] == "ix_users_admin_created_id"
        analyze = connection.execute(sa.text(
            "EXPLAIN ANALYZE SELECT id FROM users ORDER BY created_at DESC,id DESC LIMIT 50 OFFSET 9500"
        )).scalar_one()
        assert "ix_users_created_at_id" in analyze
        start = perf_counter()
        rows = connection.execute(sa.text(
            "SELECT id FROM users ORDER BY created_at DESC,id DESC LIMIT 50 OFFSET 9500"
        )).all()
        elapsed = perf_counter() - start
        assert len(rows) == 50
        assert elapsed < 1.0
    engine.dispose()
