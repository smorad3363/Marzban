import os
import random
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def test_database_url(tmp_path_factory: pytest.TempPathFactory) -> str:
    database_path = tmp_path_factory.mktemp("database") / "marzban-test.sqlite3"
    return f"sqlite:///{database_path.as_posix()}"


@pytest.fixture(scope="session")
def fake_xray_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    executable_directory = tmp_path_factory.mktemp("xray")
    if os.name == "nt":
        executable = executable_directory / "xray-test.cmd"
        executable.write_text("@echo off\r\necho Xray 0.0.0\r\n", encoding="utf-8")
    else:
        executable = executable_directory / "xray-test"
        executable.write_text(
            "#!/bin/sh\nprintf 'Xray 0.0.0\\n'\n",
            encoding="utf-8",
        )
        executable.chmod(0o700)
    return executable


@pytest.fixture(scope="session")
def application(test_database_url: str, fake_xray_path: Path):
    random.seed(0)
    os.environ.update(
        {
            "SQLALCHEMY_DATABASE_URL": test_database_url,
            "DEBUG": "false",
            "DOCS": "true",
            "XRAY_EXECUTABLE_PATH": str(fake_xray_path),
            "XRAY_ASSETS_PATH": str(fake_xray_path.parent),
            "SUDO_USERNAME": "test-owner",
            "SUDO_PASSWORD": "synthetic-test-password",
            "TELEGRAM_API_TOKEN": "",
            "TELEGRAM_ADMIN_ID": "",
            "TELEGRAM_LOGGER_CHANNEL_ID": "0",
            "DISCORD_WEBHOOK_URL": "",
            "WEBHOOK_ADDRESS": "",
            "WEBHOOK_SECRET": "synthetic-test-webhook-secret",
            "NOTIFY_LOGIN": "false",
            "NOTIFY_STATUS_CHANGE": "false",
            "NOTIFY_USER_CREATED": "false",
            "NOTIFY_USER_UPDATED": "false",
            "NOTIFY_USER_DELETED": "false",
            "NOTIFY_USER_DATA_USED_RESET": "false",
            "NOTIFY_USER_SUB_REVOKED": "false",
            "NOTIFY_IF_DATA_USAGE_PERCENT_REACHED": "false",
            "NOTIFY_IF_DAYS_LEFT_REACHED": "false",
        }
    )

    from app import app
    from app.db import Base, engine

    Base.metadata.create_all(bind=engine)
    yield app
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def client(application):
    test_client = TestClient(application)
    yield test_client
    test_client.close()


@pytest.fixture
def db_session(application):
    from app.db.base import SessionLocal

    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
