export type BillingMode = "LEGACY_COMPAT" | "SEAT_CREDIT" | "USED_TRAFFIC" | "ALLOCATED_TRAFFIC" | "USER_CREDIT";

export type DashboardOverview = {
  generated_at: string;
  timezone_offset_minutes: number;
  current_week_start: string;
  previous_week_start: string;
  total_users: number;
  active_users: number;
  online_users: number;
  disabled_users: number;
  expired_users: number;
  limited_users: number;
  on_hold_users: number;
  current_used_traffic: number;
  allocated_quota: number;
  new_users: { current: number; previous: number; change_percent: number | null };
  billing_modes: Array<{
    billing_mode: BillingMode;
    admin_count: number;
    user_count: number;
    active_users: number;
    current_used_traffic: number;
    allocated_quota: number;
  }>;
};
