import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

import app.utils.crypto
import config as app_config


REQUIRED_TABLES = {
    "admin_audit_logs",
    "marzhelp_metadata",
    "marzhelp_admin_settings",
    "marzhelp_user_states",
    "marzhelp_user_temporaries",
    "marzhelp_admin_usage",
    "marzhelp_limits",
    "marzhelp_runtime_settings",
    "marzhelp_deleted_users",
    "marzhelp_accounting_transactions",
    "marzhelp_admin_allowed_inbounds",
    "marzhelp_admin_allowed_user_limits",
}


def alembic_config(database: Path) -> Config:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database}")
    return config


def test_fresh_and_existing_migration_preserve_data(tmp_path, monkeypatch):
    monkeypatch.setattr(
        app.utils.crypto,
        "generate_certificate",
        lambda: {"key": "test-key", "cert": "test-cert"},
    )
    database = tmp_path / "migration.sqlite3"
    monkeypatch.setattr(app_config, "SQLALCHEMY_DATABASE_URL", f"sqlite:///{database}")
    config = alembic_config(database)
    command.upgrade(config, "63fbd07b9f14")
    connection = sqlite3.connect(database)
    connection.execute(
        "INSERT INTO admins (username, hashed_password, is_sudo, users_usage) VALUES (?, ?, ?, ?)",
        ("preserved-admin", "hash", 0, 0),
    )
    connection.commit()
    connection.close()

    command.upgrade(config, "head")
    connection = sqlite3.connect(database)
    assert connection.execute("SELECT username FROM admins").fetchone() == ("preserved-admin",)
    tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert REQUIRED_TABLES <= tables
    marker = dict(connection.execute("SELECT key, value FROM marzhelp_metadata"))
    assert marker["source_id"] == "smorad3363-marzban"
    assert marker["schema_version"] == "1"
    settings_columns = {
        row[1] for row in connection.execute("PRAGMA table_info(marzhelp_admin_settings)")
    }
    assert "max_users" in settings_columns
    assert "capacity_used" in settings_columns
    assert "all_inbounds" in settings_columns
    assert "all_user_limits" in settings_columns
    user_columns = {
        row[1] for row in connection.execute("PRAGMA table_info(users)")
    }
    assert "concurrent_user_limit" in user_columns
    user_indexes = {
        row[1] for row in connection.execute("PRAGMA index_list(users)")
    }
    assert "ix_users_admin_id" in user_indexes
    audit_indexes = {
        row[1] for row in connection.execute("PRAGMA index_list(admin_audit_logs)")
    }
    assert "ix_admin_audit_logs_created_at" in audit_indexes
    connection.close()


def test_sqlite_backup_contains_and_restores_marzhelp_data(tmp_path):
    source = tmp_path / "source.sqlite3"
    backup = tmp_path / "backup.sqlite3"
    restored = tmp_path / "restored.sqlite3"
    connection = sqlite3.connect(source)
    connection.execute("CREATE TABLE admins (id INTEGER PRIMARY KEY, username TEXT)")
    connection.execute(
        "CREATE TABLE marzhelp_admin_settings (admin_id INTEGER PRIMARY KEY, user_limit INTEGER)"
    )
    connection.execute("INSERT INTO admins VALUES (1, 'backup-admin')")
    connection.execute("INSERT INTO marzhelp_admin_settings VALUES (1, 17)")
    connection.commit()
    connection.backup(sqlite3.connect(backup))
    connection.close()

    source_backup = sqlite3.connect(backup)
    restored_connection = sqlite3.connect(restored)
    source_backup.backup(restored_connection)
    source_backup.close()
    assert restored_connection.execute(
        "SELECT admin_id, user_limit FROM marzhelp_admin_settings"
    ).fetchone() == (1, 17)
    restored_connection.close()

    backup_script = Path("scripts/marzban.sh").read_text(encoding="utf-8")
    assert 'cp "$sqlite_file" "$temp_dir/db_backup.sqlite"' in backup_script
    assert 'mysqldump -u root -p"$MYSQL_ROOT_PASSWORD" marzban' in backup_script


def test_installer_targets_master_and_latest_mysql_image():
    installer = Path("scripts/marzban.sh").read_text(encoding="utf-8")

    assert 'MARZBAN_GITHUB_REPO="${MARZBAN_GITHUB_REPO:-smorad3363/Marzban}"' in installer
    assert 'MARZBAN_GITHUB_BRANCH="${MARZBAN_GITHUB_BRANCH:-master}"' in installer
    assert 'MARZBAN_DOCKER_IMAGE="${MARZBAN_DOCKER_IMAGE:-ghcr.io/smorad3363/marzban}"' in installer
    assert 'database_type="mysql"' in installer
    assert "This Marzban build supports MySQL only" in installer
    assert 'marzban_version="latest"' in installer
    assert 'elif [ "$database_type" == "mysql" ]; then' in installer
    assert 'image: $(marzban_docker_image "${marzban_version}")' in installer
    assert 'requested_version="latest"' in installer
    assert 'previous_image=$(yq -r' in installer
    assert "for attempt in $(seq 1 150)" in installer
    assert "/code/scripts/healthcheck.py --mode internal --timeout 3" in installer
    assert 'docker logs --tail 200 "$container_id"' in installer
    assert "Update health check failed" in installer
    assert 'update_command --version "$1"' in installer
    assert 'rollback)' in installer
