export type SubscriptionMode =
  | "limited_traffic_unlimited_devices"
  | "unlimited_traffic_limited_devices"
  | "limited_traffic_limited_devices"
  | "unlimited_traffic_unlimited_devices";

export type AdminPolicy = {
  total_traffic: number | null;
  expiry_date: string | null;
  user_limit: number | null;
  max_users: number | null;
  device_capacity_limit: number | null;
  admin_traffic_warning_percent: number;
  sudo_traffic_warning_percent: number;
  all_inbounds: boolean;
  allowed_inbounds: string[];
  all_user_limits: boolean;
  allowed_user_limits: number[];
  allowed_subscription_modes: SubscriptionMode[];
  view_full_client_ip: boolean;
  max_user_duration_days: number | null;
  calculate_volume: "used_traffic" | "created_traffic";
  prevent_user_creation: boolean;
  prevent_user_deletion: boolean;
  prevent_user_reset: boolean;
  prevent_revoke_subscription: boolean;
  prevent_unlimited_traffic: boolean;
};

export type ManagedAdmin = {
  username: string;
  is_sudo: boolean;
  telegram_id: number | null;
  discord_webhook: string | null;
  users_usage: number | null;
  user_count: number;
  capacity_used: number;
  policy: AdminPolicy;
  quota: AdminQuotaSummary;
};

export type AdminQuotaSummary = {
  current_users: number;
  max_users: number | null;
  remaining_user_slots: number | null;
  credit_limit: number | null;
  credit_used: number;
  credit_remaining: number | null;
  credit_usage_percent: number | null;
  credit_calculation_mode: "used_traffic" | "created_traffic";
  operation_allowance_remaining: number | null;
  admin_warning_percent: number;
  sudo_warning_percent: number;
  admin_warning_active: boolean;
  sudo_warning_active: boolean;
};

export type ManagedAdminList = {
  admins: ManagedAdmin[];
  total: number;
  offset: number;
  limit: number;
};

export type ManagedAdminPayload = Omit<ManagedAdmin, "users_usage" | "user_count" | "capacity_used" | "quota"> & {
  password?: string;
};

export type AdminCapabilities = {
  all_inbounds: boolean;
  allowed_inbounds: string[];
  all_user_limits: boolean;
  allowed_user_limits: number[];
  allowed_subscription_modes: SubscriptionMode[];
  view_full_client_ip: boolean;
  capacity_used: number;
  capacity_limit: number | null;
  capacity_remaining: number | null;
  quota: AdminQuotaSummary;
};
