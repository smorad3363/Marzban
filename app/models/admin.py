from enum import Enum
from typing import Dict, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.db import Session, crud, get_db
from app.utils.jwt import get_admin_payload
from config import SUDOERS

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/admin/token")  # Admin view url


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AdminRole(str, Enum):
    owner = "owner"
    reseller = "reseller"


class AdminStatus(str, Enum):
    active = "active"
    suspended = "suspended"


KNOWN_ADMIN_PERMISSIONS = frozenset({
    "user.create",
    "user.edit",
    "user.delete",
    "user.reset",
    "user.revoke",
    "user.view_usage",
    "user.create_unlimited",
    "user.create_on_hold",
})


class Admin(BaseModel):
    username: str
    is_sudo: bool
    role: AdminRole = AdminRole.reseller
    status: AdminStatus = AdminStatus.active
    permissions: Dict[str, object] = Field(default_factory=dict)
    telegram_id: Optional[int] = None
    discord_webhook: Optional[str] = None
    users_usage: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)

    @field_validator("users_usage",  mode='before')
    def cast_to_int(cls, v):
        if v is None:  # Allow None values
            return v
        if isinstance(v, float):  # Allow float to int conversion
            return int(v)
        if isinstance(v, int):  # Allow integers directly
            return v
        raise ValueError("must be an integer or a float, not a string")  # Reject strings

    @classmethod
    def get_admin(cls, token: str, db: Session):
        payload = get_admin_payload(token)
        if not payload:
            return

        if payload['username'] in SUDOERS and payload['is_sudo'] is True:
            return cls(
                username=payload['username'],
                is_sudo=True,
                role=AdminRole.owner,
                status=AdminStatus.active,
                permissions={},
            )

        dbadmin = crud.get_admin(db, payload['username'])
        if not dbadmin:
            return

        if dbadmin.password_reset_at:
            if not payload.get("created_at"):
                return
            if dbadmin.password_reset_at > payload.get("created_at"):
                return

        return cls.model_validate(dbadmin)

    @classmethod
    def get_current(cls,
                    db: Session = Depends(get_db),
                    token: str = Depends(oauth2_scheme)):
        admin = cls.get_admin(token, db)
        if not admin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return admin

    @classmethod
    def check_sudo_admin(cls,
                         db: Session = Depends(get_db),
                         token: str = Depends(oauth2_scheme)):
        admin = cls.get_admin(token, db)
        if not admin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not admin.is_sudo:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You're not allowed"
            )
        return admin


class AdminCreate(Admin):
    password: str
    telegram_id: Optional[int] = None
    discord_webhook: Optional[str] = None

    @property
    def hashed_password(self):
        return pwd_context.hash(self.password)

    @field_validator("discord_webhook")
    @classmethod
    def validate_discord_webhook(cls, value):
        if value and not value.startswith("https://discord.com"):
            raise ValueError("Discord webhook must start with 'https://discord.com'")
        return value


class AdminModify(BaseModel):
    password: Optional[str] = None
    is_sudo: bool
    role: Optional[AdminRole] = None
    status: Optional[AdminStatus] = None
    permissions: Optional[Dict[str, object]] = None
    telegram_id: Optional[int] = None
    discord_webhook: Optional[str] = None

    @property
    def hashed_password(self):
        if self.password:
            return pwd_context.hash(self.password)

    @field_validator("discord_webhook")
    @classmethod
    def validate_discord_webhook(cls, value):
        if value and not value.startswith("https://discord.com"):
            raise ValueError("Discord webhook must start with 'https://discord.com'")
        return value


class AdminPartialModify(AdminModify):
    __annotations__ = {k: Optional[v] for k, v in AdminModify.__annotations__.items()}


class AdminInDB(Admin):
    username: str
    hashed_password: str

    def verify_password(self, plain_password):
        return pwd_context.verify(plain_password, self.hashed_password)


class AdminValidationResult(BaseModel):
    username: str
    is_sudo: bool


def has_admin_permission(admin: Optional[Admin], permission: str) -> bool:
    try:
        if admin is None or admin.status != AdminStatus.active:
            return False
        if permission not in KNOWN_ADMIN_PERMISSIONS:
            return False
        if admin.role == AdminRole.owner:
            return True
        if admin.role != AdminRole.reseller:
            return False
        value = admin.permissions.get(permission)
        return value if type(value) is bool else False
    except Exception:
        return False
