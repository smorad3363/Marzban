from alembic.config import Config
from alembic.script import ScriptDirectory


class _OperationRecorder:
    def __init__(self):
        self.added = []
        self.executed = []
        self.altered = []

    def add_column(self, table, column):
        self.added.append((table, column))

    def execute(self, statement):
        self.executed.append(str(statement))

    def alter_column(self, table, column, **kwargs):
        self.altered.append((table, column, kwargs))


def _upgrade_calls(monkeypatch, application):
    from app.db.migrations.versions import (
        b4c2d8e6f1a3_add_admin_identity_foundation as migration,
    )

    recorder = _OperationRecorder()
    monkeypatch.setattr(migration, "op", recorder)
    migration.upgrade()
    return recorder


def test_sudo_database_admin_migrates_to_owner(monkeypatch, application):
    recorder = _upgrade_calls(monkeypatch, application)
    sql = "\n".join(recorder.executed)
    assert "WHEN is_sudo = true THEN 'owner'" in sql


def test_non_sudo_database_admin_migrates_to_reseller(
    monkeypatch, application
):
    recorder = _upgrade_calls(monkeypatch, application)
    sql = "\n".join(recorder.executed)
    assert "ELSE 'reseller'" in sql


def test_existing_admins_migrate_to_active(monkeypatch, application):
    recorder = _upgrade_calls(monkeypatch, application)
    assert "UPDATE admins SET status = 'active'" in recorder.executed


def test_permissions_backfill_to_empty_object(monkeypatch, application):
    recorder = _upgrade_calls(monkeypatch, application)
    sql = "\n".join(recorder.executed)
    assert "permissions = JSON_OBJECT()" in sql
    assert {column for _, column, _ in recorder.altered} == {
        "role",
        "status",
        "permissions",
    }


def test_exactly_one_alembic_head(application):
    script = ScriptDirectory.from_config(Config("alembic.ini"))
    assert script.get_heads() == ["b4c2d8e6f1a3"]
