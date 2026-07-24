import pytest


def _admin(**overrides):
    from app.models.admin import Admin

    values = {
        "username": "admin",
        "is_sudo": False,
        "role": "reseller",
        "status": "active",
        "permissions": {},
    }
    values.update(overrides)
    return Admin(**values)


def _database_owner(db_session, username):
    from app.db.models import Admin

    owner = Admin(
        username=username,
        hashed_password="test-hash",
        is_sudo=True,
        role="owner",
        status="active",
        permissions={},
    )
    db_session.add(owner)
    db_session.commit()
    db_session.refresh(owner)
    return owner


def test_missing_admin_denies():
    from app.models.admin import has_admin_permission

    assert has_admin_permission(None, "user.create") is False


def test_suspended_admin_denies():
    from app.models.admin import has_admin_permission

    assert has_admin_permission(
        _admin(
            status="suspended",
            permissions={"user.create": True},
        ),
        "user.create",
    ) is False


def test_unknown_permission_denies():
    from app.models.admin import has_admin_permission

    assert has_admin_permission(
        _admin(role="owner", is_sudo=True),
        "unknown.permission",
    ) is False


def test_owner_allows_known_permission():
    from app.models.admin import has_admin_permission

    assert has_admin_permission(
        _admin(role="owner", is_sudo=True),
        "user.create",
    ) is True


@pytest.mark.parametrize(
    ("stored", "expected"),
    [
        (True, True),
        (False, False),
        (None, False),
        ("true", False),
    ],
)
def test_reseller_permission_override_is_strict(stored, expected):
    from app.models.admin import has_admin_permission

    permissions = {} if stored is None else {"user.edit": stored}
    assert has_admin_permission(
        _admin(permissions=permissions),
        "user.edit",
    ) is expected


def test_environment_sudo_is_active_owner(monkeypatch, application):
    from app.models import admin as admin_model

    monkeypatch.setattr(
        admin_model,
        "get_admin_payload",
        lambda _: {
            "username": "test-owner",
            "is_sudo": True,
        },
    )

    admin = admin_model.Admin.get_admin("synthetic-token", db=None)

    assert admin.role == admin_model.AdminRole.owner
    assert admin.status == admin_model.AdminStatus.active
    assert admin.permissions == {}
    assert admin_model.has_admin_permission(admin, "user.create") is True


def test_final_active_owner_deletion_is_protected(db_session):
    from app.db import crud

    owner = _database_owner(db_session, "final-delete-owner")

    with pytest.raises(crud.FinalActiveOwnerError):
        crud.remove_admin(db_session, owner)
    db_session.delete(owner)
    db_session.commit()


def test_final_active_owner_suspension_is_protected(db_session):
    from app.db import crud
    from app.models.admin import AdminModify, AdminStatus

    owner = _database_owner(db_session, "final-suspend-owner")

    with pytest.raises(crud.FinalActiveOwnerError):
        crud.update_admin(
            db_session,
            owner,
            AdminModify(is_sudo=True, status=AdminStatus.suspended),
        )
    db_session.delete(owner)
    db_session.commit()


def test_final_active_owner_demotion_is_protected(db_session):
    from app.db import crud
    from app.models.admin import AdminModify

    owner = _database_owner(db_session, "final-demote-owner")

    with pytest.raises(crud.FinalActiveOwnerError):
        crud.update_admin(
            db_session,
            owner,
            AdminModify(is_sudo=False),
        )
    db_session.delete(owner)
    db_session.commit()
