import importlib.util
import os
from datetime import datetime
from pathlib import Path

import pytest
import sqlalchemy as sa
from OpenSSL import crypto
from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.db.models import Admin, MarzhelpAdminSettings, User
from app.models.user import UserStatus
from app.utils import dashboard_metrics


MYSQL_URL = os.getenv("TEST_MYSQL_DATABASE_URL")
MIGRATION_PATH = Path(__file__).parents[1] / "app/db/migrations/versions/6d4f2a9c8e10_add_stage9_admin_phone_dashboard_indexes.py"


def _module():
    spec = importlib.util.spec_from_file_location("stage9_mysql_migration", MIGRATION_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _reset(engine):
    database = make_url(MYSQL_URL).database
    assert database and database.startswith("stage9_") and database.endswith("_test")
    with engine.begin() as connection:
        connection.execute(sa.text("SET FOREIGN_KEY_CHECKS=0"))
        for table in sa.inspect(connection).get_table_names():
            connection.execute(sa.text(f"DROP TABLE `{table.replace('`', '``')}`"))
        connection.execute(sa.text("SET FOREIGN_KEY_CHECKS=1"))


def _upgrade(revision):
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", MYSQL_URL)
    command.upgrade(config, revision)


def _downgrade(revision):
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", MYSQL_URL)
    command.downgrade(config, revision)


@pytest.mark.skipif(not MYSQL_URL, reason="TEST_MYSQL_DATABASE_URL is required")
def test_mysql_stage9_migration_aggregate_and_query_plans(monkeypatch):
    engine = sa.create_engine(MYSQL_URL, pool_pre_ping=True)
    _reset(engine)
    original_not_after = crypto.X509.gmtime_adj_notAfter
    monkeypatch.setattr(
        crypto.X509, "gmtime_adj_notAfter",
        lambda certificate, seconds: original_not_after(certificate, min(seconds, 2_000_000_000)),
    )
    _upgrade("2e8c4a6f9b17")
    _upgrade("head")
    module = _module()
    with engine.begin() as connection:
        operations = Operations(MigrationContext.configure(connection))
        monkeypatch.setattr(module, "op", operations)
        module.downgrade()
        assert "phone" not in {item["name"] for item in sa.inspect(connection).get_columns("admins")}
        module.upgrade()
        inspector = sa.inspect(connection)
        assert connection.execute(sa.text("SELECT VERSION()" )).scalar().startswith("8.0.")
        assert connection.execute(sa.text("SHOW TABLE STATUS LIKE 'users'" )).mappings().one()["Engine"] == "InnoDB"
        assert "phone" in {item["name"] for item in inspector.get_columns("admins")}
        indexes = {item["name"] for item in inspector.get_indexes("users")}
        assert {"ix_users_created_at_id", "ix_users_admin_status"} <= indexes

    _downgrade("2e8c4a6f9b17")
    assert "phone" not in {item["name"] for item in sa.inspect(engine).get_columns("admins")}
    _upgrade("head")

    Session = sessionmaker(bind=engine, expire_on_commit=False)
    with Session() as db:
        owner = Admin(username="stage9-owner", hashed_password="x", is_sudo=True, phone="+1")
        db.add(owner)
        db.flush()
        db.add(MarzhelpAdminSettings(admin_id=owner.id, billing_mode="ALLOCATED_TRAFFIC"))
        db.flush()
        db.bulk_save_objects([
            User(
                username=f"stage9-user-{index}", admin_id=owner.id,
                status=UserStatus.active if index % 2 else UserStatus.disabled,
                used_traffic=index, data_limit=10_000, created_at=datetime.utcnow(),
            )
            for index in range(2_000)
        ])
        db.commit()
        result = dashboard_metrics.overview(db, owner, timezone_offset_minutes=210)
        assert result.total_users == 2_000
        assert result.active_users == 1_000

    with engine.connect() as connection:
        created_plan = connection.execute(sa.text(
            "EXPLAIN SELECT id FROM users WHERE created_at >= UTC_TIMESTAMP() - INTERVAL 7 DAY ORDER BY created_at, id LIMIT 100"
        )).mappings().one()
        scoped_plan = connection.execute(sa.text(
            "EXPLAIN SELECT id FROM users WHERE admin_id = 1 AND status = 'active' LIMIT 100"
        )).mappings().one()
        assert created_plan["key"] == "ix_users_created_at_id"
        assert scoped_plan["key"] == "ix_users_admin_status"
        assert int(created_plan["rows"]) < 2_000
        assert int(scoped_plan["rows"]) < 2_000
    engine.dispose()
