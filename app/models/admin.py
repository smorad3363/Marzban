from datetime import date
from typing import Literal, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.db import Session, crud, get_db
from app.device_limit.constants import (
    DEFAULT_ADMIN_SUBSCRIPTION_MODES,
    SubscriptionMode,
)
from app.utils.admin_billing import BillingMode
from app.utils.jwt import get_admin_payload
from config import SUDOERS

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/admin/token")  # Admin view url


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class Admin(BaseModel):
    id: Optional[int] = None
    username: str
    is_sudo: bool = False
    role: Optional[Literal["OWNER", "SUPER_ADMIN", "ADMIN"]] = None
    parent_admin_id: Optional[int] = None
    external_api_enabled: bool = False
    auth_method: Literal["session", "automation"] = Field(default="session", exclude=True)
    api_scopes: set[str] = Field(default_factory=set, exclude=True)
    telegram_id: Optional[int] = None
    phone: Optional[str] = None
    discord_webhook: Optional[str] = None
    users_usage: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)

    @field_validator("role", mode="before")
    @classmethod
    def normalize_role(cls, value):
        return getattr(value, "code", value)

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
        from app.utils import admin_hierarchy

        payload = get_admin_payload(token)
        if payload:
            if (
                not admin_hierarchy.hierarchy_enabled(db)
                and payload['username'] in SUDOERS
                and payload['is_sudo'] is True
            ):
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

        authenticated = admin_hierarchy.authenticate_api_token(db, token)
        if authenticated is None:
            return
        dbadmin, scopes = authenticated
        result = cls.model_validate(dbadmin)
        result.auth_method = "automation"
        result.api_scopes = scopes
        return result

    @classmethod
    def get_current(cls,
                    request: Request,
                    db: Session = Depends(get_db),
                    token: str = Depends(oauth2_scheme)):
        from app.utils import admin_hierarchy

        admin = cls.get_admin(token, db)
        if not admin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        dbadmin = crud.get_admin(db, admin.username)
        if dbadmin is not None and admin_hierarchy.hierarchy_enabled(db):
            state = admin_hierarchy.account_status_code(db, dbadmin.id)
            read_only_paths = {"/api/admin", "/api/admin/logout", "/api/account/summary", "/api/account/activity"}
            if state != admin_hierarchy.ACTIVE and request.url.path not in read_only_paths:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={"code": "account_read_only", "message": f"Administrative account is {state.lower()}"},
                )
        if admin.auth_method == "automation":
            required_scope = cls._required_api_scope(request.method, request.url.path)
            if required_scope is None or required_scope not in admin.api_scopes:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={"code": "api_scope_forbidden", "message": "Automation token lacks endpoint scope"},
                )
        return admin

    @staticmethod
    def _required_api_scope(method: str, path: str) -> Optional[str]:
        write = method.upper() not in {"GET", "HEAD", "OPTIONS"}
        if path.startswith("/api/account"):
            return "account:read"
        if path.startswith("/api/user-plans") or path.startswith("/api/plan-network-options"):
            return "plans:write" if write else "plans:read"
        if path.startswith("/api/user") or path.startswith("/api/users"):
            return "users:write" if write else "users:read"
        if path.startswith("/api/admin-management") or path.startswith("/api/admins"):
            return None if write else "admins:read"
        if path.startswith("/api/audit"):
            return "audit:read" if not write else None
        return None

    @classmethod
    def check_sudo_admin(cls,
                         request: Request,
                         db: Session = Depends(get_db),
                         token: str = Depends(oauth2_scheme)):
        from app.utils import admin_hierarchy

        admin = cls.get_current(request, db, token)
        dbadmin = crud.get_admin(db, admin.username)
        if dbadmin is not None and admin_hierarchy.hierarchy_enabled(db):
            allowed = admin_hierarchy.is_owner(db, dbadmin)
        else:
            allowed = admin.is_sudo
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You're not allowed"
            )
        return admin

    @classmethod
    def check_admin_manager(cls,
                            request: Request,
                            db: Session = Depends(get_db),
                            token: str = Depends(oauth2_scheme)):
        from app.utils import admin_hierarchy

        admin = cls.get_current(request, db, token)
        dbadmin = crud.get_admin(db, admin.username)
        if dbadmin is None or not admin_hierarchy.can_manage_children(db, dbadmin):
            raise HTTPException(status_code=403, detail="You're not allowed")
        return admin


class AdminCreate(Admin):
    password: str
    telegram_id: Optional[int] = None
    phone: Optional[str] = Field(default=None, max_length=32)
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

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, value):
        value = value.strip() if value else None
        return value or None


class AdminModify(BaseModel):
    password: Optional[str] = None
    is_sudo: Optional[bool] = None
    telegram_id: Optional[int] = None
    phone: Optional[str] = Field(default=None, max_length=32)
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

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, value):
        value = value.strip() if value else None
        return value or None


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

    billing_mode: BillingMode = BillingMode.LEGACY_COMPAT
    total_traffic: Optional[int] = Field(default=None, ge=0)
    expiry_date: Optional[date] = None
    user_limit: Optional[int] = Field(default=None, ge=0)
    max_users: Optional[int] = Field(default=None, ge=1)
    device_capacity_limit: Optional[int] = Field(default=None, ge=1)
    admin_traffic_warning_percent: int = Field(default=80, ge=1, le=100)
    sudo_traffic_warning_percent: int = Field(default=80, ge=1, le=100)
    all_inbounds: bool = True
    allowed_inbounds: list[str] = Field(default_factory=list)
    all_user_limits: bool = True
    allowed_user_limits: list[int] = Field(default_factory=list)
    allowed_subscription_modes: list[SubscriptionMode] = Field(
        default_factory=lambda: list(DEFAULT_ADMIN_SUBSCRIPTION_MODES)
    )
    view_full_client_ip: bool = False
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

    @field_validator("allowed_subscription_modes")
    @classmethod
    def normalize_subscription_modes(
        cls, value: list[SubscriptionMode]
    ) -> list[SubscriptionMode]:
        return sorted(set(value), key=lambda item: item.value)

    @model_validator(mode="after")
    def validate_selected_permissions(self):
        if not self.all_inbounds and not self.allowed_inbounds:
            raise ValueError("Select at least one inbound")
        if not self.all_user_limits and not self.allowed_user_limits:
            raise ValueError("Select at least one user limit")
        if not self.allowed_subscription_modes:
            raise ValueError("Select at least one subscription mode")
        return self


class AdminQuotaSummary(BaseModel):
    current_users: int
    max_users: Optional[int] = None
    remaining_user_slots: Optional[int] = None
    credit_limit: Optional[int] = None
    credit_used: int = 0
    credit_remaining: Optional[int] = None
    credit_usage_percent: Optional[float] = None
    credit_calculation_mode: Literal["used_traffic", "created_traffic"] = "used_traffic"
    billing_mode: BillingMode = BillingMode.LEGACY_COMPAT
    operation_allowance_remaining: Optional[int] = None
    admin_warning_percent: int = 80
    sudo_warning_percent: int = 80
    admin_warning_active: bool = False
    sudo_warning_active: bool = False


class ManagedAdmin(Admin):
    user_count: int = 0
    capacity_used: int = 0
    policy: MarzhelpAdminPolicy
    quota: AdminQuotaSummary
    plan_category_ids: list[int] = Field(default_factory=list)


class AdminCapabilities(BaseModel):
    all_inbounds: bool = True
    allowed_inbounds: list[str] = Field(default_factory=list)
    all_user_limits: bool = True
    allowed_user_limits: list[int] = Field(default_factory=list)
    allowed_subscription_modes: list[SubscriptionMode] = Field(
        default_factory=lambda: list(DEFAULT_ADMIN_SUBSCRIPTION_MODES)
    )
    view_full_client_ip: bool = False
    capacity_used: int = 0
    capacity_limit: Optional[int] = None
    capacity_remaining: Optional[int] = None
    quota: AdminQuotaSummary = Field(
        default_factory=lambda: AdminQuotaSummary(
            current_users=0,
        )
    )


class ManagedAdminList(BaseModel):
    admins: list[ManagedAdmin]
    total: int
    offset: int
    limit: int


class ManagedAdminCreate(AdminCreate):
    phone: str = Field(min_length=1, max_length=32)
    policy: MarzhelpAdminPolicy = Field(default_factory=MarzhelpAdminPolicy)
    plan_category_ids: list[int] = Field(default_factory=list)

    @field_validator("phone")
    @classmethod
    def require_phone(cls, value):
        value = value.strip() if value else ""
        if not value:
            raise ValueError("Phone is required for new Admins")
        return value


class ManagedAdminModify(AdminModify):
    policy: MarzhelpAdminPolicy
    plan_category_ids: Optional[list[int]] = None


class AdminDeleteRequest(BaseModel):
    strategy: Literal["delete_users", "disable_users", "keep_users"] = "keep_users"
