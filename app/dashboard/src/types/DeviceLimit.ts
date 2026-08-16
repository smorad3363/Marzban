export type PenaltyAction =
  | "warn"
  | "temporary_disable"
  | "permanent_disable"
  | "delete";

export interface DeviceLimitSettings {
  enabled: boolean;
  enforcement_mode: "ip" | "slots" | "hybrid";
  check_interval_seconds: number;
  active_window_seconds: number;
  hit_threshold: number;
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
}

export interface DeviceLimitState {
  violation_count: number;
  current_stage: number;
  penalty_status:
    | "clear"
    | "warning"
    | "temporarily_disabled"
    | "permanently_disabled"
    | "deleted";
  blocked_until: string | null;
  last_violation_at: string | null;
  last_seen_at: string | null;
  active_ip_count: number;
  last_reason: string | null;
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
  reason: string;
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
}
