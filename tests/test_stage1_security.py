from inspect import signature
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.discord.handlers import report as discord_report
from app.routers import admin as admin_router
from app.telegram.handlers import report as telegram_report
from app.utils import report


SENTINEL_PASSWORD = "stage1-password-must-never-leave-auth"


def _request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/admin/token",
            "headers": [],
            "client": ("203.0.113.10", 443),
        }
    )


def test_failed_login_never_passes_password_to_reporter(monkeypatch):
    captured = {}
    monkeypatch.setattr(admin_router, "validate_admin", lambda *_args: None)
    monkeypatch.setattr(admin_router.AuditLogService, "log", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        admin_router.report,
        "login",
        lambda username, client_ip, success: captured.update(
            username=username,
            client_ip=client_ip,
            success=success,
        ),
    )

    with pytest.raises(HTTPException) as raised:
        admin_router.admin_token(
            request=_request(),
            form_data=SimpleNamespace(
                username="stage1-admin",
                password=SENTINEL_PASSWORD,
            ),
            db=object(),
        )

    assert raised.value.status_code == 401
    assert captured == {
        "username": "stage1-admin",
        "client_ip": "203.0.113.10",
        "success": False,
    }
    assert SENTINEL_PASSWORD not in repr(captured)


def test_login_report_payloads_have_no_password_field(monkeypatch):
    payloads = []
    monkeypatch.setattr(report, "NOTIFY_LOGIN", True)
    monkeypatch.setattr(
        report.telegram,
        "report_login",
        lambda **payload: payloads.append(payload),
    )
    monkeypatch.setattr(
        report.discord,
        "report_login",
        lambda **payload: payloads.append(payload),
    )

    report.login("stage1-admin", "203.0.113.10", False)

    assert len(payloads) == 2
    assert all("password" not in payload for payload in payloads)
    assert SENTINEL_PASSWORD not in repr(payloads)
    for callback in (report.login, telegram_report.report_login, discord_report.report_login):
        assert "password" not in signature(callback).parameters
