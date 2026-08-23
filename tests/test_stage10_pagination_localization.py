from datetime import datetime
from pathlib import Path

import pytest
import sqlalchemy as sa
from fastapi import HTTPException
from sqlalchemy.orm import sessionmaker

from app.db import crud
from app.db.base import Base
from app.db.models import Admin, AdminHierarchySettings, User
from app.models.admin import Admin as APIAdmin
from app.models.user import UserStatus, UsersResponse
from app.routers.user import get_users as route_get_users
from app.utils import marzhelp_policy


@pytest.fixture()
def db(tmp_path, monkeypatch):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'stage10.sqlite3'}")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    monkeypatch.setattr(marzhelp_policy, "allowed_inbound_tags", lambda *_args: None)
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _seed(db, count=60):
    owner = Admin(username="owner", hashed_password="x", is_sudo=True)
    other = Admin(username="other", hashed_password="x")
    db.add_all([owner, other])
    db.flush()
    db.add(AdminHierarchySettings(id=1, enabled=False, max_depth=64))
    stamp = datetime(2026, 8, 23, 12, 0)
    db.add_all([
        User(
            username=f"customer-{index:03d}",
            admin_id=owner.id if index % 3 else other.id,
            status=UserStatus.active if index % 2 else UserStatus.disabled,
            created_at=stamp,
            used_traffic=index,
        )
        for index in range(count)
    ])
    db.commit()
    return owner, other


@pytest.mark.parametrize("page_size", [10, 25, 50])
def test_route_supports_only_documented_page_sizes_and_returns_page_metadata(db, page_size):
    owner, _ = _seed(db)
    response = route_get_users(
        offset=page_size,
        limit=page_size,
        username=None,
        search=None,
        owner=None,
        status=None,
        sort="-created_at",
        db=db,
        admin=APIAdmin.model_validate(owner),
    )
    assert response["page"] == 2
    assert response["page_size"] == page_size
    assert response["pages"] == (60 + page_size - 1) // page_size
    assert response["total"] == 60
    assert len(response["users"]) == min(page_size, 60 - page_size)


@pytest.mark.parametrize("limit", [0, 9, 51, 500])
def test_route_rejects_invalid_or_oversized_page(limit):
    with pytest.raises(HTTPException) as exc:
        route_get_users(offset=0, limit=limit)
    assert exc.value.status_code == 422
    assert exc.value.detail["code"] == "pagination_size_invalid"


def test_route_rejects_misaligned_offset():
    with pytest.raises(HTTPException) as exc:
        route_get_users(offset=11, limit=10)
    assert exc.value.detail["code"] == "pagination_offset_invalid"


def test_search_filter_sort_total_payload_and_stable_tie_breaker(db):
    owner, _ = _seed(db)
    statement_count = 0
    def count_statement(*_args, **_kwargs):
        nonlocal statement_count
        statement_count += 1
    sa.event.listen(db.get_bind(), "before_cursor_execute", count_statement)
    rows, total = crud.get_users(
        db,
        offset=0,
        limit=10,
        search="customer-0",
        status=UserStatus.active,
        admins=[owner.username],
        sort=[crud.UsersSortingOptions["-created_at"]],
        return_with_count=True,
    )
    sa.event.remove(db.get_bind(), "before_cursor_execute", count_statement)
    assert total == 20
    assert len(rows) == 10
    # Count + page plus two bounded relationship loads required by UserResponse;
    # the count does not grow with page rows (no per-User N+1).
    assert statement_count == 4
    ids = [row.id for row in rows]
    assert ids == sorted(ids, reverse=True)
    assert len(set(ids)) == len(ids)


def test_response_contract_and_farsi_error_unlimited_sources():
    response = UsersResponse(users=[], total=0, page=1, page_size=10, pages=0)
    assert response.model_dump() == {"users": [], "total": 0, "page": 1, "page_size": 10, "pages": 0}
    locale = Path("app/dashboard/public/statics/locales/fa.json").read_text(encoding="utf-8")
    error_utility = Path("app/dashboard/src/utils/apiError.ts").read_text(encoding="utf-8")
    pagination = Path("app/dashboard/src/components/Pagination.tsx").read_text(encoding="utf-8")
    credit = Path("app/dashboard/src/components/AdminCreditSummary.tsx").read_text(encoding="utf-8")
    assert '"unlimited": "نامحدود"' in locale
    assert 'errors.codes.pagination_size_invalid' in locale
    assert "detail.message" not in error_utility
    assert "errors.unknownCode" in error_utility
    assert "<option>10</option>" in pagination
    assert "<option>25</option>" in pagination
    assert "<option>50</option>" in pagination
    assert "<option>500</option>" not in pagination
    assert 'account.available_traffic' in credit and 'creditValue' in credit
