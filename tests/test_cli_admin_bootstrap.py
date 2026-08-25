import typer

import cli.admin as admin_cli


class _DBContext:
    def __init__(self, db):
        self.db = db

    def __enter__(self):
        return self.db

    def __exit__(self, exc_type, exc, traceback):
        return False


def test_bootstrap_owner_creates_missing_admin_and_assigns_owner(monkeypatch):
    db = object()
    created = []
    assigned = []

    monkeypatch.setattr(admin_cli, "GetDB", lambda: _DBContext(db))
    monkeypatch.setattr(admin_cli.crud, "get_admin", lambda current_db, username: None)
    monkeypatch.setattr(
        admin_cli.crud,
        "create_admin",
        lambda current_db, values, commit: created.append((current_db, values, commit)),
    )
    monkeypatch.setattr(
        admin_cli.admin_hierarchy,
        "set_owner",
        lambda current_db, username: assigned.append((current_db, username))
        or {"owner": username},
    )

    try:
        admin_cli.bootstrap_owner(username="saji", password="secret-password")
    except typer.Exit as exc:
        assert exc.exit_code == 0

    assert len(created) == 1
    assert created[0][0] is db
    assert created[0][1].username == "saji"
    assert created[0][1].password == "secret-password"
    assert created[0][1].is_sudo is True
    assert created[0][2] is False
    assert assigned == [(db, "saji")]
