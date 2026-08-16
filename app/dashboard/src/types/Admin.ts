export type SubscriptionMode =
  | "limited_traffic_unlimited_devices"
  | "unlimited_traffic_limited_devices"
  | "limited_traffic_limited_devices"
  | "unlimited_traffic_unlimited_devices";

export type AdminPolicy = {
  total_traffic: number | null;
  used_traffic: number;
  expiry_date: string | null;
  user_limit: number | null;
  max_users: number | null;
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
};

export type ManagedAdminList = {
  admins: ManagedAdmin[];
  total: number;
  offset: number;
  limit: number;
};

export type ManagedAdminPayload = Omit<ManagedAdmin, "users_usage" | "user_count" | "capacity_used"> & {
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
};
