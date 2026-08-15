from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models import (
    Admin,
    MarzhelpAccountingTransaction,
    MarzhelpAdminSettings,
    MarzhelpDeletedUser,
    User,
    UserUsageResetLogs,
)
from app.models.user import UserStatus
from app.utils import marzhelp_policy as policy


GB = 1024**3


@pytest.fixture()
def session(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'policy.sqlite3'}",
        connect_args={"check_same_thread": False, "timeout": 10},
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    db = Session()
    db.info["session_factory"] = Session
    yield db
    db.close()
    engine.dispose()


def add_admin(db, allowance=None, **settings):
    admin = Admin(username=f"admin-{id(db)}-{db.query(Admin).count()}", hashed_password="x")
    db.add(admin)
    db.flush()
    row = MarzhelpAdminSettings(admin_id=admin.id, user_limit=allowance, **settings)
    db.add(row)
    db.commit()
    return admin, row


def plan(data_limit=10 * GB, expire=None, on_hold_expire_duration=None, next_plan=None):
    return SimpleNamespace(
        data_limit=data_limit,
        expire=expire,
        on_hold_expire_duration=on_hold_expire_duration,
        next_plan=next_plan,
    )


@pytest.mark.parametrize(
    ("used", "expected"),
    [(50 * GB, 0), (30 * GB, 20 * GB), (0, 50 * GB), (60 * GB, 0)],
)
def test_delete_refund_formula(used, expected):
    assert policy.calculate_delete_refund(50 * GB, used) == expected


def test_existing_user_count_limit_blocks_create_and_delete_frees_slot(session):
    admin, _ = add_admin(session, max_users=2)
    session.add_all(
        [
            User(username="counted-one", admin_id=admin.id, status=UserStatus.active),
            User(username="counted-two", admin_id=admin.id, status=UserStatus.disabled),
        ]
    )
    session.commit()

    with pytest.raises(policy.MarzhelpPolicyError) as exc:
        policy.validate_create(session, admin.id, plan())
    assert exc.value.code == "user_count_limit_reached"

    session.delete(session.query(User).filter(User.username == "counted-two").one())
    session.commit()
    assert policy.validate_create(session, admin.id, plan()) is not None


def test_delete_is_idempotent_and_records_actual_usage(session):
    admin, _ = add_admin(session)
    user = User(
        username="delete-me",
        admin_id=admin.id,
        status=UserStatus.active,
        data_limit=50 * GB,
        used_traffic=30 * GB,
    )
    session.add(user)
    session.commit()

    assert policy.capture_delete(session, user) == 20 * GB
    assert policy.capture_delete(session, user) == 0
    session.commit()

    ledger = session.query(MarzhelpDeletedUser).one()
    assert ledger.used_traffic_total == 30 * GB
    assert ledger.refunded_traffic == 20 * GB
    assert session.query(MarzhelpAccountingTransaction).count() == 1


def test_exactly_twenty_create_or_renew_operations(session):
    admin, _ = add_admin(session, allowance=20)
    for _ in range(12):
        policy.validate_create(session, admin.id, plan())
        session.commit()

    user = User(
        username="renew-me",
        admin_id=admin.id,
        status=UserStatus.active,
        data_limit=GB,
        used_traffic=0,
    )
    session.add(user)
    session.commit()
    for index in range(8):
        modification = plan(data_limit=(index + 2) * GB)
        renewal, consumed = policy.validate_update(session, user, modification)
        assert renewal and consumed
        user.data_limit = modification.data_limit
        session.commit()

    assert session.get(MarzhelpAdminSettings, admin.id).user_limit == 0
    with pytest.raises(policy.MarzhelpPolicyError, match="allowance"):
        policy.validate_create(session, admin.id, plan())


def test_failed_operation_rollback_does_not_consume_allowance(session):
    admin, _ = add_admin(session, allowance=1)
    policy.validate_create(session, admin.id, plan())
    session.rollback()
    assert session.get(MarzhelpAdminSettings, admin.id).user_limit == 1


def test_concurrent_last_allowance_only_one_wins(session):
    admin, _ = add_admin(session, allowance=1)
    Session = session.info["session_factory"]

    def attempt():
        db = Session()
        try:
            policy.validate_create(db, admin.id, plan())
            db.commit()
            return True
        except policy.MarzhelpPolicyError:
            db.rollback()
            return False
        finally:
            db.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: attempt(), range(2)))
    assert sorted(results) == [False, True]


def test_unlimited_traffic_rejected_on_create_edit_and_next_plan(session):
    admin, _ = add_admin(session, prevent_unlimited_traffic=True)
    policy.validate_create(session, admin.id, plan(data_limit=GB))
    session.rollback()
    with pytest.raises(policy.MarzhelpPolicyError, match="unlimited traffic"):
        policy.validate_create(session, admin.id, plan(data_limit=0))

    user = User(
        username="finite-user",
        admin_id=admin.id,
        status=UserStatus.active,
        data_limit=GB,
        used_traffic=0,
    )
    session.add(user)
    session.commit()
    with pytest.raises(policy.MarzhelpPolicyError, match="unlimited traffic"):
        policy.validate_update(session, user, plan(data_limit=0))
    with pytest.raises(policy.MarzhelpPolicyError, match="unlimited traffic"):
        policy.validate_update(
            session,
            user,
            plan(data_limit=GB, next_plan=SimpleNamespace(data_limit=0, expire=None)),
        )


def test_conversion_to_unlimited_counts_as_renewal(session):
    admin, _ = add_admin(session, allowance=1)
    user = User(
        username="upgrade-to-unlimited",
        admin_id=admin.id,
        status=UserStatus.active,
        data_limit=GB,
        used_traffic=0,
    )
    session.add(user)
    session.commit()

    renewal, consumed = policy.validate_update(session, user, plan(data_limit=0))

    assert renewal and consumed
    assert session.get(MarzhelpAdminSettings, admin.id).user_limit == 0


def test_created_traffic_counts_usage_and_resets_for_existing_unlimited_users(session):
    admin, _ = add_admin(
        session,
        total_traffic=10 * GB,
        calculate_volume="created_traffic",
    )
    user = User(
        username="legacy-unlimited",
        admin_id=admin.id,
        status=UserStatus.active,
        data_limit=None,
        used_traffic=8 * GB,
    )
    session.add(user)
    session.flush()
    session.add(UserUsageResetLogs(user_id=user.id, used_traffic_at_reset=3 * GB))
    session.commit()

    with pytest.raises(policy.MarzhelpPolicyError, match="credit is exhausted"):
        policy.validate_create(session, admin.id, plan(data_limit=GB))


def test_maximum_duration_create_and_renewal(session):
    admin, _ = add_admin(session, max_user_duration_days=31)
    now = int(datetime.now(timezone.utc).timestamp())
    policy.validate_create(session, admin.id, plan(expire=now + 31 * 86400))
    session.rollback()
    with pytest.raises(policy.MarzhelpPolicyError, match="31 days"):
        policy.validate_create(session, admin.id, plan(expire=now + 32 * 86400))
    with pytest.raises(policy.MarzhelpPolicyError, match="no-expiry"):
        policy.validate_create(session, admin.id, plan(expire=None))

    user = User(
        username="duration-user",
        admin_id=admin.id,
        status=UserStatus.active,
        data_limit=GB,
        expire=now + 20 * 86400,
        used_traffic=0,
    )
    session.add(user)
    session.commit()
    with pytest.raises(policy.MarzhelpPolicyError, match="31 days"):
        policy.validate_update(session, user, plan(data_limit=GB, expire=now + 32 * 86400))
