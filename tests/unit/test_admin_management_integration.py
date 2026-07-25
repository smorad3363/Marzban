import pytest


TEST_PASSWORD = "synthetic-admin-password"


@pytest.fixture(autouse=True)
def jwt_secret(db_session):
    from app.db.models import JWT
    from app.utils.jwt import get_secret_key

    if db_session.query(JWT).first() is None:
        db_session.add(JWT(secret_key="0" * 64))
        db_session.commit()
    get_secret_key.cache_clear()
    yield
    get_secret_key.cache_clear()


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _login(client, username, password=TEST_PASSWORD):
    return client.post(
        "/api/admin/token",
        data={"username": username, "password": password},
    )


@pytest.fixture
def admin_factory(db_session):
    from app.db.models import Admin
    from app.models.admin import pwd_context

    usernames = []

    def create(
        username,
        *,
        role="reseller",
        status="active",
        is_sudo=None,
    ):
        admin = Admin(
            username=username,
            hashed_password=pwd_context.hash(TEST_PASSWORD),
            is_sudo=role == "owner" if is_sudo is None else is_sudo,
            role=role,
            status=status,
            permissions={},
        )
        db_session.add(admin)
        db_session.commit()
        db_session.refresh(admin)
        usernames.append(username)
        return admin

    yield create

    db_session.rollback()
    db_session.query(Admin).filter(Admin.username.in_(usernames)).delete(
        synchronize_session=False
    )
    db_session.commit()


def test_active_database_owner_can_obtain_and_use_token(client, admin_factory):
    admin_factory("management-active-owner", role="owner")

    response = _login(client, "management-active-owner")

    assert response.status_code == 200
    current = client.get("/api/admin", headers=_auth(response.json()["access_token"]))
    assert current.status_code == 200
    assert current.json()["role"] == "owner"
    assert current.json()["status"] == "active"


@pytest.mark.parametrize("role", ["owner", "reseller"])
def test_suspended_admin_cannot_obtain_token(client, admin_factory, role):
    username = f"management-suspended-{role}"
    admin_factory(username, role=role, status="suspended")

    response = _login(client, username)

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"


def test_existing_token_stops_working_after_suspension(
    client, db_session, admin_factory
):
    admin = admin_factory("management-token-suspension", role="owner")
    token = _login(client, admin.username).json()["access_token"]

    admin.status = "suspended"
    db_session.commit()

    response = client.get("/api/admin", headers=_auth(token))
    assert response.status_code == 401


def test_active_owner_can_manage_database_admins(client, admin_factory):
    owner = admin_factory("management-api-owner", role="owner")
    token = _login(client, owner.username).json()["access_token"]
    headers = _auth(token)

    listed = client.get("/api/admins", headers=headers)
    assert listed.status_code == 200

    created = client.post(
        "/api/admin",
        headers=headers,
        json={
            "username": "management-api-target",
            "password": TEST_PASSWORD,
            "role": "reseller",
            "status": "active",
            "is_sudo": False,
            "permissions": {},
        },
    )
    assert created.status_code == 200
    assert created.json()["role"] == "reseller"
    assert created.json()["is_sudo"] is False

    changed_role = client.put(
        "/api/admin/management-api-target",
        headers=headers,
        json={"is_sudo": True, "role": "owner", "status": "active"},
    )
    assert changed_role.status_code == 200
    assert changed_role.json()["role"] == "owner"
    assert changed_role.json()["is_sudo"] is True

    changed_status = client.put(
        "/api/admin/management-api-target",
        headers=headers,
        json={"is_sudo": True, "role": "owner", "status": "suspended"},
    )
    assert changed_status.status_code == 200
    assert changed_status.json()["status"] == "suspended"

    deleted = client.delete(
        "/api/admin/management-api-target",
        headers=headers,
    )
    assert deleted.status_code == 200


def test_old_is_sudo_only_client_remains_compatible(client, admin_factory):
    owner = admin_factory("management-compat-owner", role="owner")
    target = admin_factory("management-compat-target")
    headers = _auth(_login(client, owner.username).json()["access_token"])

    response = client.put(
        f"/api/admin/{target.username}",
        headers=headers,
        json={"is_sudo": True},
    )

    assert response.status_code == 200
    assert response.json()["role"] == "owner"
    assert response.json()["is_sudo"] is True


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("get", "/api/admins", None),
        (
            "post",
            "/api/admin",
            {
                "username": "management-forbidden-create",
                "password": TEST_PASSWORD,
                "role": "reseller",
                "status": "active",
                "is_sudo": False,
                "permissions": {},
            },
        ),
        (
            "put",
            "/api/admin/management-forbidden-target",
            {"is_sudo": False, "role": "reseller", "status": "active"},
        ),
        ("delete", "/api/admin/management-forbidden-target", None),
    ],
)
def test_reseller_cannot_manage_admins(
    client, admin_factory, method, path, payload
):
    reseller = admin_factory("management-forbidden-reseller")
    admin_factory("management-forbidden-target")
    headers = _auth(_login(client, reseller.username).json()["access_token"])

    request = getattr(client, method)
    response = (
        request(path, headers=headers, json=payload)
        if payload is not None
        else request(path, headers=headers)
    )

    assert response.status_code == 403


def test_unknown_role_is_denied_for_new_and_existing_tokens(
    client, db_session, admin_factory
):
    admin = admin_factory("management-unknown-role", role="owner")
    token = _login(client, admin.username).json()["access_token"]

    admin.role = "unknown"
    db_session.commit()

    assert _login(client, admin.username).status_code == 401
    assert client.get("/api/admin", headers=_auth(token)).status_code == 401


def test_environment_sudo_retains_owner_access(client):
    response = _login(client, "test-owner", "synthetic-test-password")

    assert response.status_code == 200
    token = response.json()["access_token"]
    current = client.get("/api/admin", headers=_auth(token))
    assert current.status_code == 200
    assert current.json()["role"] == "owner"
    assert current.json()["status"] == "active"
    assert client.get("/api/admins", headers=_auth(token)).status_code == 200


def test_final_active_owner_cannot_be_deleted_suspended_or_demoted(
    client, admin_factory
):
    owner = admin_factory("management-final-owner", role="owner")
    sudo_token = _login(
        client, "test-owner", "synthetic-test-password"
    ).json()["access_token"]
    headers = _auth(sudo_token)

    deleted = client.delete(f"/api/admin/{owner.username}", headers=headers)
    suspended = client.put(
        f"/api/admin/{owner.username}",
        headers=headers,
        json={"is_sudo": True, "role": "owner", "status": "suspended"},
    )
    demoted = client.put(
        f"/api/admin/{owner.username}",
        headers=headers,
        json={"is_sudo": False, "role": "reseller", "status": "active"},
    )

    assert deleted.status_code == 409
    assert suspended.status_code == 409
    assert demoted.status_code == 409
