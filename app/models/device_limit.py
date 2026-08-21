from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.device_limit.constants import PenaltyAction, PenaltyStatus


class DeviceLimitSettingsResponse(BaseModel):
    enabled: bool
    enforcement_mode: Literal["ip", "slots", "hybrid"]
    device_slots_enabled: bool
    ip_detection_enabled: bool
    client_fingerprint_enabled: bool
    check_interval_seconds: int
    active_window_seconds: int
    hit_threshold: int
    min_successful_connections: int
    handoff_grace_seconds: int
    warning_auto_delete_seconds: int
    strike_reset_seconds: int
    full_ip_retention_days: int
    incident_retention_days: int
    audit_retention_days: int
    auto_delete_enabled: bool
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class DeviceLimitSettingsUpdate(BaseModel):
    enabled: bool
    enforcement_mode: Literal["ip", "slots", "hybrid"] | None = None
    device_slots_enabled: bool = True
    ip_detection_enabled: bool = True
    client_fingerprint_enabled: bool = False
    check_interval_seconds: int = Field(ge=10, le=3600)
    active_window_seconds: int = Field(ge=30, le=86400)
    hit_threshold: int | None = Field(default=None, ge=1, le=100)
    min_successful_connections: int = Field(default=3, ge=1, le=100)
    handoff_grace_seconds: int = Field(default=90, ge=0, le=600)
    warning_auto_delete_seconds: int = Field(default=86400, ge=0, le=31536000)
    strike_reset_seconds: int = Field(ge=300, le=31536000)
    full_ip_retention_days: int = Field(ge=1, le=30)
    incident_retention_days: int = Field(ge=7, le=3650)
    audit_retention_days: int = Field(ge=30, le=3650)
    auto_delete_enabled: bool = False

    @model_validator(mode="after")
    def validate_window(self):
        if self.active_window_seconds < self.check_interval_seconds:
            raise ValueError("Active window must be at least the check interval")
        if self.enabled and not (
            self.device_slots_enabled
            or self.ip_detection_enabled
            or self.client_fingerprint_enabled
        ):
            raise ValueError("Enable at least one device capability")
        if (
            self.hit_threshold is not None
            and "min_successful_connections" not in self.model_fields_set
        ):
            self.min_successful_connections = self.hit_threshold
        return self


class DeviceLimitDiagnosticsResponse(BaseModel):
    runtime_enabled: bool
    ip_detection_enabled: bool
    active_collectors: list[str]
    received_lines: int
    accepted_lines: int
    rejected_runtime_disabled: int
    rejected_not_accepted: int
    rejected_source_parse: int
    rejected_identity_parse: int
    rejected_invalid_ip: int
    rejected_private_or_loopback: int
    rejected_user_not_limited: int
    recorded_events: int
    dropped_buffer_events: int
    hit_buffer_capacity: int
    last_log_seen_at: datetime | None
    last_valid_match_at: datetime | None


class DeviceClientObservationResponse(BaseModel):
    id: int
    slot_id: int | None
    slot_key: int
    client_name: str
    client_version: str | None
    platform: str | None
    os_token: str | None
    network_stack: str | None
    raw_user_agent: str | None
    first_seen_at: datetime
    last_seen_at: datetime
    seen_count: int
    model_config = ConfigDict(from_attributes=True)


class DeviceLimitPenaltyStageInput(BaseModel):
    violation_count: int = Field(ge=1, le=100)
    action: PenaltyAction
    duration_seconds: int | None = Field(default=None, ge=60, le=31536000)
    enabled: bool = True

    @model_validator(mode="after")
    def validate_duration(self):
        if self.action == PenaltyAction.temporary_disable and self.duration_seconds is None:
            raise ValueError("Temporary-disable stages require a duration")
        if self.action != PenaltyAction.temporary_disable:
            self.duration_seconds = None
        return self


class DeviceLimitPenaltyStageResponse(DeviceLimitPenaltyStageInput):
    id: int
    model_config = ConfigDict(from_attributes=True)


class DeviceLimitPenaltyStagesUpdate(BaseModel):
    stages: list[DeviceLimitPenaltyStageInput] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def validate_unique_counts(self):
        counts = [stage.violation_count for stage in self.stages]
        if len(counts) != len(set(counts)):
            raise ValueError("Penalty violation counts must be unique")
        return self


class DeviceSlotResponse(BaseModel):
    id: int
    slot_index: int
    label: str | None
    enabled: bool
    last_seen_at: datetime | None
    last_ip: str | None
    subscription_url: str
    created_at: datetime
    client_observations: list[DeviceClientObservationResponse] = Field(default_factory=list)


class DeviceSlotModify(BaseModel):
    label: str | None = Field(default=None, max_length=64)


class DeviceLimitStateResponse(BaseModel):
    violation_count: int = 0
    current_stage: int = 0
    penalty_status: PenaltyStatus = PenaltyStatus.clear
    blocked_until: datetime | None = None
    last_violation_at: datetime | None = None
    last_seen_at: datetime | None = None
    active_ip_count: int = 0
    last_reason: str | None = None
    pending_handoff_started_at: datetime | None = None
    pending_ip_addresses: list[str] | None = None
    pending_source_nodes: list[str] | None = None
    pending_risk_score: int | None = None
    model_config = ConfigDict(from_attributes=True)


class DeviceLimitIncidentResponse(BaseModel):
    id: int
    user_id: int | None
    admin_id: int | None
    username: str
    stage: int
    action: PenaltyAction
    configured_limit: int
    observed_count: int
    ip_addresses: list[str] | None
    source_nodes: list[str] | None
    event_state: str
    risk_score: int | None
    signal_summary: dict | None
    reason: str
    expires_at: datetime | None
    resolved_at: datetime | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class DeviceLimitIncidentList(BaseModel):
    incidents: list[DeviceLimitIncidentResponse]
    total: int
    offset: int
    limit: int


class DeviceLimitUserSummary(BaseModel):
    username: str
    configured_limit: int | None
    enabled: bool
    live_active_ip_count: int
    live_ip_addresses: list[str]
    live_source_nodes: list[str]
    state: DeviceLimitStateResponse
    slots: list[DeviceSlotResponse]
    user_client_observations: list[DeviceClientObservationResponse] = Field(default_factory=list)
