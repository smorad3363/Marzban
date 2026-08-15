from datetime import date, datetime

from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.requests import Request

from app.db.base import Base
from app.db.models import Admin as DBAdmin
from app.db.models import AdminAuditLog
from app.models.admin import Admin, pwd_context
from app.routers.admin import admin_token
from app.routers.audit import get_audit_logs
from app.utils.audit import (
    AuditLogService,
    REDACTED,
    sanitize_audit_value,
    summarize_targets,
)


def make_db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'audit.sqlite3'}")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)()


def test_audit_service_stores_safe_snapshot_and_client_ip(tmp_path):
    db = make_db(tmp_path)
    dbadmin = DBAdmin(
        username="matin",
        hashed_password="hash",
        is_sudo=True,
        users_usage=0,
    )
    db.add(dbadmin)
    db.commit()
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/user",
            "headers": [(b"x-forwarded-for", b"203.0.113.10, 10.0.0.2")],
            "client": ("127.0.0.1", 1234),
        }
    )

    entry = AuditLogService.log(
        db,
        Admin(username="matin", is_sudo=True),
        "user.create",
        "user",
        "Admin matin created user test123",
        target_id=44,
        target_name="test123",
        new_value={
            "username": "test123",
            "password": "must-not-leak",
            "nested": {"api_token": "must-not-leak"},
        },
        request=request,
    )

    assert entry.admin_id == dbadmin.id
    assert entry.admin_username == "matin"
    assert entry.ip_address == "203.0.113.10"
    assert entry.new_value["password"] == REDACTED
    assert entry.new_value["nested"]["api_token"] == REDACTED
    assert db.query(AdminAuditLog).count() == 1


def test_recursive_sanitizer_and_bulk_summary_are_bounded():
    sanitized = sanitize_audit_value(
        {
            "authorization": "Bearer credential",
            "safe": "visible",
            "items": [{"private_key": "secret"}],
        }
    )
    assert sanitized == {
        "authorization": REDACTED,
        "safe": "visible",
        "items": [{"private_key": REDACTED}],
    }

    summary = summarize_targets([f"user-{index}" for index in range(125)])
    assert summary["count"] == 125
    assert len(summary["usernames"]) == 100
    assert summary["omitted"] == 25


def test_audit_query_filters_combined_and_uses_server_pagination(tmp_path):
    db = make_db(tmp_path)
    db.add_all(
        [
            AdminAuditLog(
                admin_username="matin",
                action="user.traffic_add",
                target_type="user",
                target_id="1",
                target_name="test123",
                description="Admin matin added traffic to test123",
                status="success",
                created_at=datetime(2026, 8, 15, 12, 0, 0),
            ),
            AdminAuditLog(
                admin_username="other",
                action="user.delete",
                target_type="user",
                target_id="2",
                target_name="old-user",
                description="Admin other deleted old-user",
                status="success",
                created_at=datetime(2026, 8, 14, 12, 0, 0),
            ),
        ]
    )
    db.commit()

    result = get_audit_logs(
        offset=0,
        limit=1,
        admin_username="matin",
        action="user.traffic_add",
        target="test",
        search="traffic",
        date_from=date(2026, 8, 15),
        date_to=date(2026, 8, 15),
        sort="newest",
        db=db,
        _=Admin(username="sudo", is_sudo=True),
    )

    assert result.total == 1
    assert result.limit == 1
    assert [item.target_name for item in result.logs] == ["test123"]


def test_successful_admin_login_issues_token_and_writes_audit_log(
    tmp_path, monkeypatch
):
    db = make_db(tmp_path)
    dbadmin = DBAdmin(
        username="saji",
        hashed_password=pwd_context.hash("correct-password"),
        is_sudo=True,
        users_usage=0,
    )
    db.add(dbadmin)
    db.commit()
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/admin/token",
            "headers": [],
            "client": ("127.0.0.1", 1234),
        }
    )
    form = OAuth2PasswordRequestForm(
        grant_type="password",
        username="saji",
        password="correct-password",
        scope="",
        client_id=None,
        client_secret=None,
    )
    monkeypatch.setattr("app.routers.admin.report.login", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        "app.routers.admin.create_admin_token",
        lambda username, is_sudo: f"token-for-{username}-{is_sudo}",
    )

    token = admin_token(request=request, form_data=form, db=db)

    assert token.access_token
    entry = db.query(AdminAuditLog).filter_by(action="auth.login").one()
    assert entry.admin_id == dbadmin.id
    assert entry.target_id == str(dbadmin.id)
    assert entry.target_name == "saji"
