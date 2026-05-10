export type AuditLogEntry = {
  id: string;
  table_name: string;
  record_id: string;
  action: 'insert' | 'update' | 'delete';
  change_summary: Record<string, unknown>;
  changed_at: string;
  user_id: string | null;
  mandant_id: string | null;
};

export type AuditLogResponse = {
  items: AuditLogEntry[];
  total: number;
  page: number;
  page_size: number;
};

export type AuditLogParams = {
  page?: number;
  table?: string;
  action?: string;
  date_from?: string;
  date_to?: string;
};
