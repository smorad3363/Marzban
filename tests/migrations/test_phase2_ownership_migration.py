import os
import sqlite3
from argparse import Namespace
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy import event
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError


ROOT = Path(__file__).resolve().parents[2]
PRE_PHASE2_HEAD = "63fbd07b9f14"
PHASE2_HEAD = "9c2f1a7b4d6e"
CREATOR_PROVENANCE = "inferred_from_legacy_owner"


def _alembic_config(url: str, x_args=None) -> Config:
    import config as application_config

    application_config.SQLALCHEMY_DATABASE_URL = url
    alembic_config = Config(str(ROOT / "alembic.ini"))
    alembic_config.cmd_opts = Namespace(x=x_args or [])
    return alembic_config


def _upgrade(url: str, revision: str, x_args=None) -> None:
    command.upgrade(_alembic_config(url, x_args), revision)


def _engine(url: str):
    engine = sa.create_engine(url)
    if engine.dialect.name == "sqlite":
        event.listen(
            engine,
            "connect",
            lambda connection, _: connection.execute("PRAGMA foreign_keys=ON"),
        )
    return engine


def _create_mysql_database(base_url: str):
    parsed = make_url(base_url)
    database_name = f"phase2_{uuid4().hex}"
    admin_url = parsed.set(database=None)
    admin_engine = sa.create_engine(admin_url)
    with admin_engine.begin() as connection:
        connection.execute(
            sa.text(
                f"CREATE DATABASE `{database_name}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        )
    admin_engine.dispose()
    return parsed.set(database=database_name).render_as_string(
        hide_password=False
    ), admin_url, database_name


@pytest.fixture(params=("sqlite", "mysql"))
def ownership_database(request, tmp_path):
    if request.param == "sqlite":
        yield f"sqlite:///{(tmp_path / 'ownership.sqlite3').as_posix()}"
        return

    base_url = os.getenv("PHASE2_MYSQL_URL")
    if not base_url:
        pytest.skip("PHASE2_MYSQL_URL is required for MySQL migration tests")

    url, admin_url, database_name = _create_mysql_database(base_url)
    try:
        yield url
    finally:
        admin_engine = sa.create_engine(admin_url)
        with admin_engine.begin() as connection:
            connection.execute(
                sa.text(f"DROP DATABASE IF EXISTS `{database_name}`")
            )
        admin_engine.dispose()


@pytest.fixture(scope="module", autouse=True)
def migration_application_environment(tmp_path_factory):
    executable_directory = tmp_path_factory.mktemp("migration-xray")
    if os.name == "nt":
        executable = executable_directory / "xray-test.cmd"
        executable.write_text(
            "@echo off\r\necho Xray 0.0.0\r\n", encoding="utf-8"
        )
    else:
        executable = executable_directory / "xray-test"
        executable.write_text(
            "#!/bin/sh\nprintf 'Xray 0.0.0\\n'\n", encoding="utf-8"
        )
        executable.chmod(0o700)

    os.environ.update(
        {
            "DEBUG": "false",
            "DOCS": "false",
            "XRAY_EXECUTABLE_PATH": str(executable),
            "XRAY_ASSETS_PATH": str(executable_directory),
        }
    )

    import app.utils.crypto

    original = app.utils.crypto.generate_certificate
    app.utils.crypto.generate_certificate = lambda: {
        "cert": "phase2-test-certificate",
        "key": "phase2-test-private-key",
    }
    try:
        yield
    finally:
        app.utils.crypto.generate_certificate = original


def _prepare_pre_phase2_schema(url: str) -> None:
    engine = _engine(url)
    metadata = sa.MetaData()
    admins = sa.Table(
        "admins",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("username", sa.String(34), nullable=True, unique=True),
    )
    sa.Table(
        "users",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("username", sa.String(34), nullable=True, unique=True),
        sa.Column(
            "admin_id",
            sa.Integer,
            sa.ForeignKey(admins.c.id, name="fk_users_admin_id_admins"),
            nullable=True,
        ),
    )
    sa.Table(
        "alembic_version",
        metadata,
        sa.Column("version_num", sa.String(32), nullable=False),
    )
    metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "INSERT INTO alembic_version (version_num) "
                "VALUES (:revision)"
            ),
            {"revision": PRE_PHASE2_HEAD},
        )
    engine.dispose()


def _insert_admin_and_user(
    url: str, admin_id, user_admin_id, username="legacy-user"
) -> None:
    engine = _engine(url)
    if engine.dialect.name == "sqlite" and user_admin_id not in (
        None,
        admin_id,
    ):
        engine.dispose()
        connection = sqlite3.connect(make_url(url).database)
        try:
            connection.execute("PRAGMA foreign_keys=OFF")
            connection.execute(
                "INSERT INTO admins (id, username) VALUES (?, ?)",
                (admin_id, "approved-owner"),
            )
            connection.execute(
                "INSERT INTO users (id, username, admin_id) VALUES (?, ?, ?)",
                (1, username, user_admin_id),
            )
            connection.commit()
        finally:
            connection.close()
        return

    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "INSERT INTO admins (id, username) "
                "VALUES (:id, :username)"
            ),
            {"id": admin_id, "username": "approved-owner"},
        )
        if engine.dialect.name == "mysql" and user_admin_id not in (
            None,
            admin_id,
        ):
            connection.execute(sa.text("SET FOREIGN_KEY_CHECKS=0"))
        connection.execute(
            sa.text(
                "INSERT INTO users (id, username, admin_id) "
                "VALUES (1, :username, :admin_id)"
            ),
            {"username": username, "admin_id": user_admin_id},
        )
        if engine.dialect.name == "mysql":
            connection.execute(sa.text("SET FOREIGN_KEY_CHECKS=1"))
    engine.dispose()


def _ownership_row(url: str):
    engine = _engine(url)
    with engine.connect() as connection:
        row = connection.execute(
            sa.text(
                "SELECT admin_id, owner_admin_id, created_by_admin_id "
                "FROM users WHERE id = 1"
            )
        ).one()
    engine.dispose()
    return tuple(row)


def test_empty_database_upgrade_has_phase2_schema(ownership_database):
    _upgrade(ownership_database, "head")

    engine = _engine(ownership_database)
    inspector = sa.inspect(engine)
    columns = {column["name"] for column in inspector.get_columns("users")}
    indexes = {
        index["name"]: tuple(index["column_names"])
        for index in inspector.get_indexes("users")
    }
    foreign_keys = {
        tuple(foreign_key["constrained_columns"]): foreign_key
        for foreign_key in inspector.get_foreign_keys("users")
    }
    with engine.connect() as connection:
        current = connection.scalar(
            sa.text("SELECT version_num FROM alembic_version")
        )

    assert current == PHASE2_HEAD
    assert {"admin_id", "created_by_admin_id", "owner_admin_id"} <= columns
    assert indexes["ix_users_created_by_admin_id"] == (
        "created_by_admin_id",
    )
    assert indexes["ix_users_owner_admin_id"] == ("owner_admin_id",)
    for column in (("created_by_admin_id",), ("owner_admin_id",)):
        assert foreign_keys[column]["referred_table"] == "admins"
        assert foreign_keys[column]["options"].get("ondelete") in (
            "RESTRICT",
            None,
        )
    engine.dispose()


def test_valid_legacy_owner_is_backfilled_and_retry_is_deterministic(
    ownership_database,
):
    _prepare_pre_phase2_schema(ownership_database)
    _insert_admin_and_user(ownership_database, admin_id=1, user_admin_id=1)

    _upgrade(ownership_database, "head")
    _upgrade(ownership_database, "head")

    assert _ownership_row(ownership_database) == (1, 1, 1)


def test_null_legacy_owner_requires_explicit_verified_destination(
    ownership_database,
):
    _prepare_pre_phase2_schema(ownership_database)
    _insert_admin_and_user(ownership_database, admin_id=7, user_admin_id=None)

    with pytest.raises(RuntimeError, match="explicit existing destination"):
        _upgrade(ownership_database, "head")

    _upgrade(
        ownership_database,
        "head",
        [
            "legacy_owner_username=approved-owner",
            "legacy_owner_verified=true",
        ],
    )
    assert _ownership_row(ownership_database) == (7, 7, 7)


def test_orphaned_legacy_owner_requires_explicit_verified_destination(
    ownership_database,
):
    _prepare_pre_phase2_schema(ownership_database)
    _insert_admin_and_user(ownership_database, admin_id=7, user_admin_id=999)

    with pytest.raises(RuntimeError, match="explicit existing destination"):
        _upgrade(ownership_database, "head")

    _upgrade(
        ownership_database,
        "head",
        [
            "legacy_owner_username=approved-owner",
            "legacy_owner_verified=true",
        ],
    )
    assert _ownership_row(ownership_database) == (7, 7, 7)


def test_admin_delete_is_restricted_and_downgrade_is_non_destructive(
    ownership_database,
):
    _prepare_pre_phase2_schema(ownership_database)
    _insert_admin_and_user(ownership_database, admin_id=1, user_admin_id=1)
    _upgrade(ownership_database, "head")

    engine = _engine(ownership_database)
    with pytest.raises(DBAPIError):
        with engine.begin() as connection:
            connection.execute(sa.text("DELETE FROM admins WHERE id = 1"))
    with engine.connect() as connection:
        assert connection.scalar(sa.text("SELECT COUNT(*) FROM users")) == 1

    with pytest.raises(RuntimeError, match="Destructive Phase 2 downgrade"):
        command.downgrade(_alembic_config(ownership_database), PRE_PHASE2_HEAD)

    assert {"created_by_admin_id", "owner_admin_id"} <= {
        column["name"] for column in sa.inspect(engine).get_columns("users")
    }
    engine.dispose()


def test_creator_inference_provenance_is_explicit():
    migration = (
        ROOT
        / "app"
        / "db"
        / "migrations"
        / "versions"
        / "9c2f1a7b4d6e_add_compatible_user_ownership_fields.py"
    ).read_text(encoding="utf-8")

    assert f'CREATOR_PROVENANCE = "{CREATOR_PROVENANCE}"' in migration
