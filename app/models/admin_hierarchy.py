from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


AdminRoleCode = Literal["OWNER", "SUPER_ADMIN", "ADMIN"]


class HierarchyAdminNode(BaseModel):
    id: int
    username: str
    role: AdminRoleCode
    parent_admin_id: Optional[int] = None
    depth: int = 0
    external_api_enabled: bool = False
    account_status: Literal["ACTIVE", "SUSPENDED", "DISABLED"] = "ACTIVE"
    total_traffic: Optional[int] = None
    delegated_traffic: int = 0
    own_spend: int = 0
    available_traffic: Optional[int] = None
    children: list["HierarchyAdminNode"] = Field(default_factory=list)


class HierarchyChildCreate(BaseModel):
    username: str = Field(min_length=3, max_length=34)
    password: str = Field(min_length=6, max_length=128)
    role: Literal["SUPER_ADMIN", "ADMIN"] = "ADMIN"


class ReparentRequest(BaseModel):
    parent_username: str


class CreditTransferRequest(BaseModel):
    amount: int = Field(gt=0)
    idempotency_key: str = Field(min_length=8, max_length=128)
    note: Optional[str] = Field(default=None, max_length=512)


class CreditTransferResponse(BaseModel):
    id: int
    from_admin_id: Optional[int]
    to_admin_id: Optional[int]
    actor_admin_id: int
    amount: int
    operation_type: str
    idempotency_key: str
    created_at: datetime
    note: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class ExternalApiPolicy(BaseModel):
    enabled: bool


class ApiTokenCreate(BaseModel):
    name: str = Field(min_length=1, max_length=96)
    scopes: set[str] = Field(min_length=1)
    expires_at: datetime


class ApiTokenCreated(BaseModel):
    id: int
    name: str
    scopes: list[str]
    expires_at: datetime
    token: str


class ApiTokenSummary(BaseModel):
    id: int
    name: str
    scopes: list[str]
    expires_at: datetime
    last_used_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class RenewalPolicyUpdate(BaseModel):
    enabled: bool = True
    remaining: Optional[int] = Field(default=None, ge=0)


class UserCreationModeUpdate(BaseModel):
    mode: Literal["FREE_FORM", "PLAN_ONLY"]
    can_manage_plans: bool = False


class SuspendRequest(BaseModel):
    reason_id: int = Field(default=1, ge=1)
    include_subtree: bool = True


class BulkDisableRequest(BaseModel):
    include_subtree: bool = False
    idempotency_key: str = Field(min_length=8, max_length=128)
    batch_size: int = Field(default=500, ge=1, le=2000)


class AccountSummary(BaseModel):
    username: str
    role: AdminRoleCode
    account_status: Literal["ACTIVE", "SUSPENDED", "DISABLED"]
    suspended_reason: Optional[str] = None
    suspended_at: Optional[datetime] = None
    own_users: int = 0
    subtree_users: int = 0
    total_traffic: Optional[int] = None
    delegated_traffic: int = 0
    own_spend: int = 0
    available_traffic: Optional[int] = None
    renewal_enabled: bool = True
    renewal_remaining: Optional[int] = None
    user_creation_mode: Literal["FREE_FORM", "PLAN_ONLY"] = "FREE_FORM"
    can_manage_plans: bool = False


class PlanVersionInput(BaseModel):
    data_limit: int = Field(ge=0)
    duration_days: int = Field(ge=1, le=3650)
    concurrent_user_limit: Optional[int] = Field(default=None, ge=1)
    reset_strategy: Literal["no_reset", "day", "week", "month", "year"] = "no_reset"
    renewal_volume_strategy: Literal["replace"] = "replace"
    renewal_time_strategy: Literal["extend_max"] = "extend_max"
    inbounds: list[str] = Field(default_factory=list)

    @field_validator("inbounds")
    @classmethod
    def normalize_inbounds(cls, value: list[str]) -> list[str]:
        return sorted({item.strip() for item in value if item.strip()})


class PlanCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: Optional[str] = Field(default=None, max_length=512)
    version: PlanVersionInput
    allowed_admin_ids: list[int] = Field(default_factory=list)
    include_subtree: bool = False


class PlanUpdate(BaseModel):
    description: Optional[str] = Field(default=None, max_length=512)
    version: PlanVersionInput
    allowed_admin_ids: list[int] = Field(default_factory=list)
    include_subtree: bool = False


class PlanResponse(BaseModel):
    id: int
    owner_admin_id: int
    name: str
    description: Optional[str]
    current_version_id: int
    version_number: int
    archived_at: Optional[datetime]
    version: PlanVersionInput
    allowed_admin_ids: list[int]
    include_subtree: bool


class PlanUserCreate(BaseModel):
    username: str
    plan_id: int
    status: Literal["active", "on_hold"] = "active"
    note: Optional[str] = Field(default=None, max_length=500)
    idempotency_key: str = Field(min_length=8, max_length=128)


class PlanRenewRequest(BaseModel):
    plan_id: int
    idempotency_key: str = Field(min_length=8, max_length=128)
