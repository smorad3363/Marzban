import pytest


TEST_PASSWORD = "synthetic-mutation-password"


@pytest.fixture(autouse=True)
def jwt_secret(db_session):
    from app.db.models import JWT
    from app.utils.jwt import get_secret_key

    if db_session.query(JWT).first() is None:
        db_session.add(JWT(secret_key="1" * 64))
        db_session.commit()
    get_secret_key.cache_clear()
    yield
    get_secret_key.cache_clear()


@pytest.fixture
def admin_factory(db_session):
    from app.db.models import Admin
    from app.models.admin import pwd_context

    usernames = []

    def create(username, *, role="reseller", permissions=None):
        admin = Admin(
            username=username,
            hashed_password=pwd_context.hash(TEST_PASSWORD),
            is_sudo=role == "owner",
            role=role,
            status="active",
            permissions=permissions or {},
        )
        db_session.add(admin)
        db_session.commit()
        db_session.refresh(admin)
        usernames.append(username)
        return admin

    yield create

    for username in usernames:
        admin = db_session.query(Admin).filter(Admin.username == username).first()
        if admin:
            db_session.delete(admin)
    db_session.commit()


def _auth(client, username):
    response = client.post(
        "/api/admin/token",
        data={"username": username, "password": TEST_PASSWORD},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _user_payload(username, **overrides):
    payload = {
        "username": username,
        "proxies": {"vless": {}},
        "inbounds": {},
        "data_limit": 1024,
    }
    payload.update(overrides)
    return payload


def _owned_user(db_session, admin, username):
    from app.db import crud
    from app.models.user import UserCreate

    return crud.create_user(
        db_session,
        UserCreate.model_validate(_user_payload(username)),
        admin=admin,
    )


@pytest.mark.parametrize(
    ("method", "suffix", "permission"),
    [
        ("put", "", "user.edit"),
        ("delete", "", "user.delete"),
        ("post", "/reset", "user.reset"),
        ("post", "/revoke_sub", "user.revoke"),
    ],
)
def test_reseller_mutation_requires_explicit_permission(
    client,
    db_session,
    admin_factory,
    method,
    suffix,
    permission,
):
    admin = admin_factory(f"denied-{permission.replace('.', '-')}")
    username = f"owned-{permission.replace('.', '-')}"
    user = _owned_user(db_session, admin, username)
    user.used_traffic = 1024
    db_session.commit()
    headers = _auth(client, admin.username)

    request = getattr(client, method)
    response = (
        request(
            f"/api/user/{username}{suffix}",
            headers=headers,
            json={"proxies": {}, "inbounds": {}, "note": "blocked"},
        )
        if method == "put"
        else request(f"/api/user/{username}{suffix}", headers=headers)
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "You're not allowed"}
    db_session.refresh(user)
    assert user.note is None
    assert user.used_traffic == 1024
    assert user.sub_revoked_at is None


def test_reseller_create_requires_explicit_permission(client, admin_factory):
    admin = admin_factory("denied-create")

    response = client.post(
        "/api/user",
        headers=_auth(client, admin.username),
        json=_user_payload("denied-create-user"),
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "You're not allowed"}


def test_unlimited_creation_requires_extra_permission(client, admin_factory):
    admin = admin_factory(
        "limited-create-only",
        permissions={"user.create": True},
    )

    response = client.post(
        "/api/user",
        headers=_auth(client, admin.username),
        json=_user_payload("denied-unlimited-user", data_limit=0),
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "You're not allowed"}


def test_omitted_data_limit_is_also_unlimited(client, admin_factory):
    admin = admin_factory(
        "omitted-limit-create",
        permissions={"user.create": True},
    )
    payload = _user_payload("denied-omitted-limit-user")
    del payload["data_limit"]

    response = client.post(
        "/api/user",
        headers=_auth(client, admin.username),
        json=payload,
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "You're not allowed"}


def test_on_hold_creation_requires_extra_permission(client, admin_factory):
    admin = admin_factory(
        "active-create-only",
        permissions={"user.create": True},
    )

    response = client.post(
        "/api/user",
        headers=_auth(client, admin.username),
        json=_user_payload(
            "denied-on-hold-user",
            status="on_hold",
            on_hold_expire_duration=3600,
        ),
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "You're not allowed"}


def test_granted_create_permissions_allow_on_hold_unlimited_user(
    client,
    db_session,
    admin_factory,
    monkeypatch,
):
    from app import xray
    from app.db import crud
    from app.routers import user as user_router

    admin = admin_factory(
        "granted-create",
        permissions={
            "user.create": True,
            "user.create_unlimited": True,
            "user.create_on_hold": True,
        },
    )
    protocol = next(iter(xray.config.inbounds_by_protocol))
    monkeypatch.setattr(xray.operations, "add_user", lambda **kwargs: None)
    monkeypatch.setattr(user_router.report, "user_created", lambda **kwargs: None)

    response = client.post(
        "/api/user",
        headers=_auth(client, admin.username),
        json={
            "username": "granted-create-user",
            "proxies": {protocol: {}},
            "inbounds": {},
            "data_limit": 0,
            "status": "on_hold",
            "on_hold_expire_duration": 3600,
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "on_hold"
    assert response.json()["data_limit"] is None
    crud.remove_user(db_session, crud.get_user(db_session, "granted-create-user"))


def test_granted_reseller_permissions_allow_individual_mutations(
    client,
    db_session,
    admin_factory,
    monkeypatch,
):
    from app import xray
    from app.db import crud
    from app.routers import user as user_router

    permissions = {
        "user.edit": True,
        "user.delete": True,
        "user.reset": True,
        "user.revoke": True,
    }
    admin = admin_factory("granted-mutations", permissions=permissions)
    username = "granted-mutations-user"
    user = _owned_user(db_session, admin, username)
    user.used_traffic = 1024
    db_session.commit()
    headers = _auth(client, admin.username)

    for operation in ("add_user", "update_user", "remove_user"):
        monkeypatch.setattr(xray.operations, operation, lambda **kwargs: None)
    for notification in (
        "user_updated",
        "user_deleted",
        "user_data_usage_reset",
        "user_subscription_revoked",
    ):
        monkeypatch.setattr(user_router.report, notification, lambda **kwargs: None)

    modified = client.put(
        f"/api/user/{username}",
        headers=headers,
        json={"proxies": {}, "inbounds": {}, "note": "allowed"},
    )
    reset = client.post(f"/api/user/{username}/reset", headers=headers)
    revoked = client.post(f"/api/user/{username}/revoke_sub", headers=headers)
    revoked_at = crud.get_user(db_session, username).sub_revoked_at
    deleted = client.delete(f"/api/user/{username}", headers=headers)

    assert modified.status_code == 200
    assert modified.json()["note"] == "allowed"
    assert reset.status_code == 200
    assert reset.json()["used_traffic"] == 0
    assert revoked.status_code == 200
    assert revoked_at is not None
    assert deleted.status_code == 200
    assert crud.get_user(db_session, username) is None


@pytest.mark.parametrize(
    "permission",
    [
        "user.create",
        "user.edit",
        "user.delete",
        "user.reset",
        "user.revoke",
        "user.create_unlimited",
        "user.create_on_hold",
    ],
)
def test_owner_keeps_each_mutation_permission(permission):
    from app.dependencies import require_admin_permission
    from app.models.admin import Admin

    owner = Admin(username="owner", is_sudo=True, role="owner", status="active")

    assert require_admin_permission(owner, permission) is None
