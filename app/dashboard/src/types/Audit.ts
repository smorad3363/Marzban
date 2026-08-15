export type AuditValue = Record<string, unknown> | unknown[] | string | number | boolean | null;

export interface AuditLog {
  id: number;
  admin_id: number | null;
  admin_username: string;
  action: string;
  target_type: string;
  target_id: string | null;
  target_name: string | null;
  description: string;
  previous_value: AuditValue;
  new_value: AuditValue;
  details: AuditValue;
  ip_address: string | null;
  status: "success" | "failed" | string;
  created_at: string;
}

export interface AuditLogList {
  logs: AuditLog[];
  total: number;
  offset: number;
  limit: number;
}

export interface AuditLogOptions {
  admins: string[];
  actions: string[];
}
