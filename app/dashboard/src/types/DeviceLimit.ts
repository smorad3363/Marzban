export type PenaltyAction =
  | "warn"
  | "temporary_disable"
  | "permanent_disable"
  | "delete";

export interface DeviceLimitSettings {
  enabled: boolean;
  enforcement_mode: "ip" | "slots" | "hybrid";
  device_slots_enabled: boolean;
  ip_detection_enabled: boolean;
  client_fingerprint_enabled: boolean;
  check_interval_seconds: number;
  active_window_seconds: number;
  hit_threshold: number;
  min_successful_connections: number;
  handoff_grace_seconds: number;
  warning_auto_delete_seconds: number;
  strike_reset_seconds: number;
  full_ip_retention_days: number;
  incident_retention_days: number;
  audit_retention_days: number;
  auto_delete_enabled: boolean;
  updated_at: string;
}

export interface DeviceLimitPenaltyStage {
  id?: number;
  violation_count: number;
  action: PenaltyAction;
  duration_seconds: number | null;
  enabled: boolean;
}

export interface DeviceSlot {
  id: number;
  slot_index: number;
  label: string | null;
  enabled: boolean;
  last_seen_at: string | null;
  last_ip: string | null;
  subscription_url: string;
  created_at: string;
  client_observations: DeviceClientObservation[];
}

export interface DeviceClientObservation {
  id: number;
  slot_id: number | null;
  slot_key: number;
  client_name: string;
  client_version: string | null;
  platform: string | null;
  os_token: string | null;
  network_stack: string | null;
  raw_user_agent: string | null;
  first_seen_at: string;
  last_seen_at: string;
  seen_count: number;
}

export interface DeviceLimitState {
  violation_count: number;
  current_stage: number;
  penalty_status:
    | "clear"
    | "pending_handoff"
    | "warning"
    | "temporarily_disabled"
    | "permanently_disabled"
    | "deleted";
  blocked_until: string | null;
  last_violation_at: string | null;
  last_seen_at: string | null;
  active_ip_count: number;
  last_reason: string | null;
  pending_handoff_started_at: string | null;
  pending_ip_addresses: string[] | null;
  pending_source_nodes: string[] | null;
  pending_risk_score: number | null;
}

export interface DeviceLimitIncident {
  id: number;
  user_id: number | null;
  admin_id: number | null;
  username: string;
  stage: number;
  action: PenaltyAction;
  configured_limit: number;
  observed_count: number;
  ip_addresses: string[] | null;
  source_nodes: string[] | null;
  event_state: string;
  risk_score: number | null;
  signal_summary: Record<string, unknown> | null;
  reason: string;
  expires_at: string | null;
  resolved_at: string | null;
  created_at: string;
}

export interface DeviceLimitIncidentList {
  incidents: DeviceLimitIncident[];
  total: number;
  offset: number;
  limit: number;
}

export interface DeviceLimitUserSummary {
  username: string;
  configured_limit: number | null;
  enabled: boolean;
  live_active_ip_count: number;
  live_ip_addresses: string[];
  live_source_nodes: string[];
  state: DeviceLimitState;
  slots: DeviceSlot[];
  user_client_observations: DeviceClientObservation[];
}
