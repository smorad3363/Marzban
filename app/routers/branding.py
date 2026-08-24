from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.db import Session, crud, get_db
from app.db.models import Admin as DBAdmin
from app.models.admin import Admin, BrandingResponse, BrandingUpdate
from app.utils import responses
from config import BRANDING_LOGO_DIRECTORY


router = APIRouter(tags=["Branding"], prefix="/api", responses={401: responses._401})
MAX_LOGO_BYTES = 1024 * 1024
ALLOWED_LOGOS = {
    "png": ("image/png", b"\x89PNG\r\n\x1a\n"),
    "jpg": ("image/jpeg", b"\xff\xd8\xff"),
    "webp": ("image/webp", b"RIFF"),
}


def _directory() -> Path:
    path = Path(BRANDING_LOGO_DIRECTORY).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def _db_admin(db: Session, admin: Admin) -> DBAdmin:
    row = crud.get_admin(db, admin.username)
    if row is None:
        raise HTTPException(status_code=404, detail="Admin not found")
    return row


def _logo_type(payload: bytes) -> tuple[str, str] | None:
    if payload.startswith(ALLOWED_LOGOS["png"][1]):
        return "png", ALLOWED_LOGOS["png"][0]
    if payload.startswith(ALLOWED_LOGOS["jpg"][1]):
        return "jpg", ALLOWED_LOGOS["jpg"][0]
    if len(payload) >= 12 and payload.startswith(ALLOWED_LOGOS["webp"][1]) and payload[8:12] == b"WEBP":
        return "webp", ALLOWED_LOGOS["webp"][0]
    return None


@router.get("/branding", response_model=BrandingResponse)
def get_branding(
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
):
    row = _db_admin(db, admin)
    return BrandingResponse(
        dashboard_theme=row.dashboard_theme or "heisenberg",
        logo_url=row.logo_url,
    )


@router.put("/branding", response_model=BrandingResponse)
def update_branding(
    values: BrandingUpdate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
):
    row = _db_admin(db, admin)
    row.dashboard_theme = values.dashboard_theme
    db.commit()
    db.refresh(row)
    return BrandingResponse(dashboard_theme=row.dashboard_theme, logo_url=row.logo_url)


@router.post("/branding/logo", response_model=BrandingResponse)
async def upload_logo(
    logo: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
):
    payload = await logo.read(MAX_LOGO_BYTES + 1)
    if not payload or len(payload) > MAX_LOGO_BYTES:
        raise HTTPException(
            status_code=422,
            detail={"code": "invalid_logo_size", "message": "Logo must be at most 1 MiB"},
        )
    detected = _logo_type(payload)
    if detected is None:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "invalid_logo_type",
                "message": "Only PNG, JPEG, or WebP logos are accepted",
            },
        )
    extension, _ = detected
    row = _db_admin(db, admin)
    directory = _directory()
    filename = f"admin-{row.id}.{extension}"
    target = directory / filename
    temporary = directory / f".{filename}.upload"
    temporary.write_bytes(payload)
    temporary.replace(target)
    previous = row.logo_filename
    row.logo_filename = filename
    db.commit()
    if previous and previous != filename:
        previous_path = directory / Path(previous).name
        if previous_path.is_file():
            previous_path.unlink()
    return BrandingResponse(dashboard_theme=row.dashboard_theme, logo_url=row.logo_url)


@router.delete("/branding/logo", response_model=BrandingResponse)
def remove_logo(
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
):
    row = _db_admin(db, admin)
    previous = row.logo_filename
    row.logo_filename = None
    db.commit()
    if previous:
        target = _directory() / Path(previous).name
        if target.is_file():
            target.unlink()
    return BrandingResponse(dashboard_theme=row.dashboard_theme, logo_url=None)


@router.get("/branding/logo/{admin_id}", include_in_schema=False)
def branding_logo(admin_id: int, db: Session = Depends(get_db)):
    row = db.get(DBAdmin, admin_id)
    if row is None or not row.logo_filename:
        raise HTTPException(status_code=404, detail="Logo not found")
    target = _directory() / Path(row.logo_filename).name
    if not target.is_file():
        raise HTTPException(status_code=404, detail="Logo not found")
    detected = _logo_type(target.read_bytes()[:16])
    media_type = detected[1] if detected else "application/octet-stream"
    return FileResponse(target, media_type=media_type, headers={"Cache-Control": "public, max-age=300"})
