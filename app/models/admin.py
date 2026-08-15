from datetime import date
from typing import Literal, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.db import Session, crud, get_db
from app.utils.jwt import get_admin_payload
from config import SUDOERS

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/admin/token")  # Admin view url


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class Admin(BaseModel):
    username: str
    is_sudo: bool
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
            return cls(username=payload['username'], is_sudo=True)

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


class MarzhelpAdminPolicy(BaseModel):
    """Editable MarzHelp limits exposed to sudo admins in the dashboard."""

    total_traffic: Optional[int] = Field(default=None, ge=0)
    used_traffic: int = Field(default=0, ge=0)
    expiry_date: Optional[date] = None
    user_limit: Optional[int] = Field(default=None, ge=0)
    max_users: Optional[int] = Field(default=None, ge=1)
    all_inbounds: bool = True
    allowed_inbounds: list[str] = Field(default_factory=list)
    all_user_limits: bool = True
    allowed_user_limits: list[int] = Field(default_factory=list)
    max_user_duration_days: Optional[int] = Field(default=None, ge=1)
    calculate_volume: Literal["used_traffic", "created_traffic"] = "used_traffic"
    prevent_user_creation: bool = False
    prevent_user_deletion: bool = False
    prevent_user_reset: bool = False
    prevent_revoke_subscription: bool = False
    prevent_unlimited_traffic: bool = False
    model_config = ConfigDict(from_attributes=True)

    @field_validator("allowed_inbounds")
    @classmethod
    def normalize_inbounds(cls, value: list[str]) -> list[str]:
        return sorted({tag.strip() for tag in value if tag.strip()})

    @field_validator("allowed_user_limits")
    @classmethod
    def normalize_user_limits(cls, value: list[int]) -> list[int]:
        if any(limit < 1 for limit in value):
            raise ValueError("Allowed user limits must be positive integers")
        return sorted(set(value))

    @model_validator(mode="after")
    def validate_selected_permissions(self):
        if not self.all_inbounds and not self.allowed_inbounds:
            raise ValueError("Select at least one inbound")
        if not self.all_user_limits and not self.allowed_user_limits:
            raise ValueError("Select at least one user limit")
        return self


class ManagedAdmin(Admin):
    user_count: int = 0
    capacity_used: int = 0
    policy: MarzhelpAdminPolicy


class AdminCapabilities(BaseModel):
    all_inbounds: bool = True
    allowed_inbounds: list[str] = Field(default_factory=list)
    all_user_limits: bool = True
    allowed_user_limits: list[int] = Field(default_factory=list)
    capacity_used: int = 0
    capacity_limit: Optional[int] = None
    capacity_remaining: Optional[int] = None


class ManagedAdminList(BaseModel):
    admins: list[ManagedAdmin]
    total: int
    offset: int
    limit: int


class ManagedAdminCreate(AdminCreate):
    policy: MarzhelpAdminPolicy = Field(default_factory=MarzhelpAdminPolicy)


class ManagedAdminModify(AdminModify):
    policy: MarzhelpAdminPolicy
