from pathlib import Path

from sqlalchemy import text


def test_isolated_sqlite_database_is_available(db_session, test_database_url):
    assert test_database_url.startswith("sqlite:///")
    assert Path(test_database_url.removeprefix("sqlite:///")).name == (
        "marzban-test.sqlite3"
    )
    assert db_session.execute(text("SELECT 1")).scalar_one() == 1
