import pytest


def _admin(db_session, username):
    from app.db.models import Admin

    admin = Admin(username=username, hashed_password="test-hash")
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    return admin


def _user_payload(username):
    from app.models.user import UserCreate

    return UserCreate(username=username, proxies={"vless": {}}, inbounds={})


def test_new_user_assigns_creator_and_both_owner_fields(db_session):
    from app.db import crud

    owner = _admin(db_session, "owner-one")

    user = crud.create_user(
        db_session,
        _user_payload("owned-user"),
        admin=owner,
    )

    assert user.created_by_admin_id == owner.id
    assert user.owner_admin_id == owner.id
    assert user.admin_id == owner.id
    assert user.current_owner is owner


def test_new_user_requires_database_backed_owner(db_session):
    from app.db import crud
    from app.db.models import Admin

    with pytest.raises(crud.OwnershipIdentityError):
        crud.create_user(
            db_session,
            _user_payload("missing-owner"),
            admin=None,
        )

    transient_admin = Admin(username="transient", hashed_password="test-hash")
    with pytest.raises(crud.OwnershipIdentityError):
        crud.create_user(
            db_session,
            _user_payload("transient-owner"),
            admin=transient_admin,
        )


def test_creator_is_immutable_while_owner_dual_write_stays_consistent(
    db_session,
):
    from app.db import crud

    creator = _admin(db_session, "creator")
    destination = _admin(db_session, "destination")
    user = crud.create_user(
        db_session,
        _user_payload("transfer-compatible"),
        admin=creator,
    )

    changed = crud.set_owner(db_session, user, destination)

    assert changed.created_by_admin_id == creator.id
    assert changed.admin_id == destination.id
    assert changed.owner_admin_id == destination.id
    assert changed.current_owner is destination
    with pytest.raises(
        ValueError, match="created_by_admin_id is immutable once assigned"
    ):
        changed.created_by_admin_id = destination.id
    with pytest.raises(
        ValueError, match="created_by_admin_id is immutable once assigned"
    ):
        changed.created_by_admin = destination
        db_session.flush()


def test_current_owner_read_falls_back_to_legacy_field(db_session):
    from app.db.models import User

    owner = _admin(db_session, "legacy-owner")
    user = User(
        username="legacy-read",
        status="active",
        admin=owner,
        owner_admin=None,
    )
    db_session.add(user)
    db_session.flush()

    assert user.current_owner_id == owner.id
    assert user.current_owner is owner


def test_existing_api_response_keeps_legacy_admin_field():
    from app.models.user import UserResponse

    assert "admin" in UserResponse.model_fields
    assert "created_by_admin_id" not in UserResponse.model_fields
    assert "owner_admin_id" not in UserResponse.model_fields
