import asyncio
from io import BytesIO

import sqlalchemy as sa
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models import Admin
from app.models.admin import Admin as APIAdmin, BrandingUpdate
from app.routers import branding


def test_admin_branding_theme_logo_upload_and_reset(tmp_path, monkeypatch):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'branding.sqlite3'}")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine, expire_on_commit=False)()
    row = Admin(username="brand-admin", hashed_password="x")
    other = Admin(username="other-admin", hashed_password="x")
    db.add_all([row, other])
    db.commit()
    actor = APIAdmin(username=row.username, is_sudo=False)
    monkeypatch.setattr(branding, "BRANDING_LOGO_DIRECTORY", str(tmp_path / "logos"))

    changed = branding.update_branding(BrandingUpdate(dashboard_theme="black_gold"), db, actor)
    assert changed.dashboard_theme == "black_gold"
    assert other.dashboard_theme == "heisenberg"

    uploaded = asyncio.run(
        branding.upload_logo(
            UploadFile(filename="logo.png", file=BytesIO(b"\x89PNG\r\n\x1a\ncontent")),
            db,
            actor,
        )
    )
    assert uploaded.logo_url == f"/api/branding/logo/{row.id}"
    assert (tmp_path / "logos" / f"admin-{row.id}.png").is_file()
    assert other.logo_filename is None

    removed = branding.remove_logo(db, actor)
    assert removed.logo_url is None
    assert not (tmp_path / "logos" / f"admin-{row.id}.png").exists()
    db.close()
    engine.dispose()


def test_admin_branding_rejects_non_image(tmp_path, monkeypatch):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'branding-invalid.sqlite3'}")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine, expire_on_commit=False)()
    row = Admin(username="brand-invalid", hashed_password="x")
    db.add(row)
    db.commit()
    monkeypatch.setattr(branding, "BRANDING_LOGO_DIRECTORY", str(tmp_path / "logos"))
    actor = APIAdmin(username=row.username, is_sudo=False)
    try:
        asyncio.run(
            branding.upload_logo(
                UploadFile(filename="logo.svg", file=BytesIO(b"<svg></svg>")),
                db,
                actor,
            )
        )
        raise AssertionError("invalid logo was accepted")
    except HTTPException as exc:
        assert exc.status_code == 422
        assert exc.detail["code"] == "invalid_logo_type"
    finally:
        db.close()
        engine.dispose()
