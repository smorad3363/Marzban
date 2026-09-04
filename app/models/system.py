from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class SystemStats(BaseModel):
    version: str
    mem_total: int
    mem_used: int
    cpu_cores: int
    cpu_usage: float
    total_user: int
    online_users: int
    users_active: int
    users_on_hold: int
    users_disabled: int
    users_expired: int
    users_limited: int
    incoming_bandwidth: int
    outgoing_bandwidth: int
    incoming_bandwidth_speed: int
    outgoing_bandwidth_speed: int


class DashboardWeekTrend(BaseModel):
    current: int
    previous: int
    change_percent: float | None = None


class DashboardBillingModeMetric(BaseModel):
    billing_mode: Literal[
        "LEGACY_COMPAT", "SEAT_CREDIT", "USED_TRAFFIC", "ALLOCATED_TRAFFIC", "USER_CREDIT"
    ]
    admin_count: int = 0
    user_count: int = 0
    active_users: int = 0
    current_used_traffic: int | None = 0
    allocated_quota: int = 0


class DashboardOverview(BaseModel):
    generated_at: datetime
    timezone_offset_minutes: int = Field(ge=-840, le=840)
    current_week_start: datetime
    previous_week_start: datetime
    total_users: int
    active_users: int
    online_users: int
    disabled_users: int
    expired_users: int
    limited_users: int
    on_hold_users: int
    current_used_traffic: int | None
    allocated_quota: int
    new_users: DashboardWeekTrend
    billing_modes: list[DashboardBillingModeMetric]
