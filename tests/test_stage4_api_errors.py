import json
from types import SimpleNamespace

from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError

from app import http_exception_handler, internal_exception_handler, validation_exception_handler
from app.utils.api_errors import (
    http_error_detail,
    internal_error_detail,
    validation_error_detail,
)


def test_http_error_preserves_stable_code_and_safe_context_but_hides_internal_text():
    detail = http_error_detail(
        409,
        {
            "code": "PLAN_PRICE_BELOW_PARENT",
            "message": "SELECT * FROM secret_wallets",
            "field": "price_toman",
            "allowed_actions": ["cancel"],
        },
        "req-123",
    )
    assert detail == {
        "error_code": "PLAN_PRICE_BELOW_PARENT",
        "message_fa": "این تغییر با وضعیت فعلی داده‌ها تداخل دارد.",
        "request_id": "req-123",
        "field": "price_toman",
        "allowed_actions": ["cancel"],
    }


def test_validation_error_is_field_specific_and_persian():
    detail = validation_error_detail(
        [
            {"loc": ("body", "username"), "type": "missing", "msg": "Field required"},
            {"loc": ("body", "price"), "type": "greater_than_equal", "msg": "bad"},
        ],
        "req-422",
    )
    assert detail["error_code"] == "VALIDATION_ERROR"
    assert detail["field"] == "username"
    assert detail["fields"] == {
        "username": "این فیلد الزامی است.",
        "price": "مقدار این فیلد از حداقل مجاز کمتر است.",
    }
    assert detail["request_id"] == "req-422"


def test_internal_error_contains_only_tracking_code():
    detail = internal_error_detail("req-500")
    assert detail == {
        "error_code": "INTERNAL_ERROR",
        "message_fa": "خطای داخلی رخ داد. کد پیگیری: req-500",
        "request_id": "req-500",
    }
    assert "traceback" not in detail
    assert "sql" not in detail


def test_application_handlers_return_persian_envelopes_without_internal_details():
    request = SimpleNamespace(state=SimpleNamespace(request_id="req-http"))
    denied = http_exception_handler(
        request,
        HTTPException(
            status_code=403,
            detail={"code": "PERMISSION_DENIED", "message": "internal permission detail"},
        ),
    )
    invalid = validation_exception_handler(
        request,
        RequestValidationError(
            [{"type": "missing", "loc": ("query", "required_number"), "msg": "Field required", "input": None}]
        ),
    )
    failed = internal_exception_handler(request, RuntimeError("SELECT password FROM admins"))
    denied_body = json.loads(denied.body)
    invalid_body = json.loads(invalid.body)
    failed_body = json.loads(failed.body)

    assert denied.status_code == 403
    assert denied_body["detail"] == {
        "error_code": "PERMISSION_DENIED",
        "message_fa": "اجازه انجام این عملیات را ندارید.",
        "request_id": "req-http",
    }
    assert invalid.status_code == 422
    assert invalid_body["detail"]["error_code"] == "VALIDATION_ERROR"
    assert invalid_body["detail"]["field"] == "required_number"
    assert failed.status_code == 500
    assert failed_body["detail"]["request_id"] == "req-http"
    assert "password" not in failed.body.decode()
    assert "SELECT" not in failed.body.decode()
