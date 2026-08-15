from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class AuditLogResponse(BaseModel):
    id: int
    admin_id: Optional[int] = None
    admin_username: str
    action: str
    target_type: str
    target_id: Optional[str] = None
    target_name: Optional[str] = None
    description: str
    previous_value: Optional[Any] = None
    new_value: Optional[Any] = None
    details: Optional[Any] = None
    ip_address: Optional[str] = None
    status: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AuditLogList(BaseModel):
    logs: List[AuditLogResponse]
    total: int
    offset: int
    limit: int


class AuditLogOptions(BaseModel):
    admins: List[str] = Field(default_factory=list)
    actions: List[str] = Field(default_factory=list)
