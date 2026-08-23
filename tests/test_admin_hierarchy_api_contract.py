from app import app
from app.models.admin import Admin


def test_admin_hierarchy_openapi_contract_is_registered():
    paths = app.openapi()["paths"]
    required = {
        "/api/admin-management/tree",
        "/api/admin-management/{username}/children",
        "/api/admin-management/{username}/parent",
        "/api/admin-management/{username}/credit/grant",
        "/api/admin-management/{username}/credit/reclaim",
        "/api/admin-management/{username}/credit/ledger",
        "/api/admin-management/{username}/renewal-policy",
        "/api/admin-management/{username}/external-api",
        "/api/admin-management/{username}/api-tokens",
        "/api/admin-management/{username}/suspend",
        "/api/admin-management/{username}/resume",
        "/api/admin-management/{username}/freeze",
        "/api/admin-management/{username}/unfreeze",
        "/api/admin-management/{username}/referral",
        "/api/admin-management/{username}/users/disable",
        "/api/account/summary",
        "/api/account/activity",
        "/api/user-plans",
        "/api/user-plans/{plan_id}",
        "/api/plan-network-options",
        "/api/users/from-plan",
        "/api/users/{username}/renew-from-plan",
    }
    assert required <= set(paths)


def test_automation_token_scope_mapping_is_deny_by_default():
    assert Admin._required_api_scope("GET", "/api/account/summary") == "account:read"
    assert Admin._required_api_scope("GET", "/api/user-plans") == "plans:read"
    assert Admin._required_api_scope("GET", "/api/plan-network-options") == "plans:read"
    assert Admin._required_api_scope("POST", "/api/user-plans") == "plans:write"
    assert Admin._required_api_scope("GET", "/api/users") == "users:read"
    assert Admin._required_api_scope("POST", "/api/user") == "users:write"
    assert Admin._required_api_scope("POST", "/api/admin-management/child/suspend") is None
    assert Admin._required_api_scope("GET", "/api/core") is None
