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
  id: number;
  username: string;
  is_sudo: boolean;
  role: "OWNER" | "SUPER_ADMIN" | "ADMIN";
  parent_admin_id: number | null;
  external_api_enabled: boolean;
  telegram_id: number | null;
  discord_webhook: string | null;
  users_usage: number | null;
  user_count: number;
  capacity_used: number;
  policy: AdminPolicy;
  quota: AdminQuotaSummary;
  plan_category_ids: number[];
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

export type ManagedAdminPayload = Omit<
  ManagedAdmin,
  "id" | "parent_admin_id" | "external_api_enabled" | "users_usage" | "user_count" | "capacity_used" | "quota"
> & {
  password?: string;
};

export type HierarchyAdminNode = {
  id: number;
  username: string;
  role: "OWNER" | "SUPER_ADMIN" | "ADMIN";
  parent_admin_id: number | null;
  depth: number;
  external_api_enabled: boolean;
  account_status: "ACTIVE" | "SUSPENDED" | "DISABLED";
  total_traffic: number | null;
  delegated_traffic: number;
  own_spend: number;
  available_traffic: number | null;
  children: HierarchyAdminNode[];
};

export type AccountSummary = {
  username: string;
  role: "OWNER" | "SUPER_ADMIN" | "ADMIN";
  account_status: "ACTIVE" | "SUSPENDED" | "DISABLED";
  suspended_reason: string | null;
  suspended_at: string | null;
  own_users: number;
  subtree_users: number;
  total_traffic: number | null;
  delegated_traffic: number;
  own_spend: number;
  available_traffic: number | null;
  renewal_enabled: boolean;
  renewal_remaining: number | null;
  user_creation_mode: "FREE_FORM" | "PLAN_ONLY";
  can_manage_plans: boolean;
};

export type UserPlanVersion = {
  data_limit: number;
  duration_days: number;
  concurrent_user_limit: number | null;
  reset_strategy: "no_reset" | "day" | "week" | "month" | "year";
  renewal_volume_strategy: "replace";
  renewal_time_strategy: "extend_max";
  inbounds: string[];
};

export type UserPlan = {
  id: number;
  owner_admin_id: number;
  name: string;
  description: string | null;
  category_id: number | null;
  category_name: string | null;
  current_version_id: number;
  version_number: number;
  archived_at: string | null;
  version: UserPlanVersion;
  allowed_admin_ids: number[];
  include_subtree: boolean;
};

export type PlanCategory = {
  id: number;
  owner_admin_id: number;
  name: string;
  description: string | null;
  archived_at: string | null;
  plan_count: number;
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
