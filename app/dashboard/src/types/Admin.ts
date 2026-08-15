export type AdminPolicy = {
  total_traffic: number | null;
  used_traffic: number;
  expiry_date: string | null;
  user_limit: number | null;
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
  policy: AdminPolicy;
};

export type ManagedAdminList = {
  admins: ManagedAdmin[];
  total: number;
  offset: number;
  limit: number;
};

export type ManagedAdminPayload = Omit<ManagedAdmin, "users_usage"> & {
  password?: string;
};
