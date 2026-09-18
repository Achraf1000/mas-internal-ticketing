export type Role = "USER" | "IT_AGENT" | "ADMIN";
export type TicketStatus = "NEW" | "IN_PROGRESS" | "ON_HOLD" | "RESOLVED" | "CLOSED";
export type TicketPriority = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type TicketCategory = "REQUEST" | "INCIDENT" | "ANOMALY" | "VALIDATION";

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  access_token_expires_at: string;
  refresh_token_expires_at: string;
}

export interface MeResponse {
  department_name: string | null;
  id: string;
  email: string;
  full_name: string;
  role: Role;
  department_id: number | null;
  is_department_head: boolean;
}

export interface Department {
  id: number;
  code: string;
  name: string;
  is_active: boolean;
}

export interface UserSummary {
  id: string;
  email: string;
  full_name: string;
}

export interface Ticket {
  id: string;
  ticket_code: string;
  title: string;
  description: string;
  category: TicketCategory;
  priority: TicketPriority;
  status: TicketStatus;
  is_department_broadcast: boolean;
  emitter_department: Department;
  target_department: Department;
  creator: UserSummary;
  assignee: UserSummary | null;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
  closed_at: string | null;
}

export interface TicketComment {
  id: number;
  ticket_id: string;
  author: UserSummary;
  body: string;
  is_internal: boolean;
  created_at: string;
}

export interface TicketAttachment {
  id: number;
  filename: string;
  mime_type: string;
  size_bytes: number;
  uploaded_by: string;
  uploaded_at: string;
}

export interface TicketStatusHistory {
  id: number;
  from_status: TicketStatus | null;
  to_status: TicketStatus;
  changed_by: string;
  reason: string | null;
  changed_at: string;
}

export interface TicketDetail extends Ticket {
  comments: TicketComment[];
  attachments: TicketAttachment[];
  status_history: TicketStatusHistory[];
}

export interface ReportOverview {
  total_tickets: number;
  open_tickets: number;
  overdue_tickets: number;
  by_status: { key: string; count: number }[];
  by_priority: { key: string; count: number }[];
  by_user_status: UserStatusRow[];
}

export interface DepartmentHeadKpi {
  received_count: number;
  open_count: number;
  resolved_count: number;
  closed_count: number;
  sla_overdue_count: number;
  avg_resolution_hours: number | null;
}

export interface DepartmentHeadMemberRow {
  member_id: string;
  member_name: string;
  assigned_open: number;
  resolved_closed: number;
  sla_overdue: number;
  avg_resolution_hours: number | null;
  new_count: number;
  in_progress_count: number;
  on_hold_count: number;
  resolved_count: number;
  closed_count: number;
}

export interface UserStatusRow {
  user_id: string;
  user_name: string;
  department_name: string | null;
  new_count: number;
  in_progress_count: number;
  on_hold_count: number;
  resolved_count: number;
  closed_count: number;
  total_count: number;
}

export interface DepartmentHeadOverview {
  year: number;
  month: number;
  department_id: number;
  department_name: string;
  kpi: DepartmentHeadKpi;
  by_status: { key: string; count: number }[];
  by_priority: { key: string; count: number }[];
  members: DepartmentHeadMemberRow[];
}

export interface AdminUser {
  id: string;
  email: string;
  full_name: string;
  role: Role;
  department_id: number | null;
  is_department_head: boolean;
  is_active: boolean;
  ldap_groups: string;
  last_login_at: string | null;
  created_at: string;
  updated_at: string;
}
