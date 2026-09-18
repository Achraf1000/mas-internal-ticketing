import type { Role, TicketCategory, TicketPriority, TicketStatus } from "../types/api";

export const STATUS_VALUES: TicketStatus[] = ["NEW", "IN_PROGRESS", "ON_HOLD", "RESOLVED", "CLOSED"];
export const ACTIVE_STATUS_VALUES: TicketStatus[] = ["NEW", "IN_PROGRESS", "ON_HOLD", "RESOLVED"];

const STATUS_LABELS: Record<TicketStatus, string> = {
  NEW: "Nouveau",
  IN_PROGRESS: "En cours",
  ON_HOLD: "En pause",
  RESOLVED: "Resolu",
  CLOSED: "Cloture"
};

const PRIORITY_LABELS: Record<TicketPriority, string> = {
  LOW: "Basse",
  MEDIUM: "Moyenne",
  HIGH: "Haute",
  CRITICAL: "Critique"
};

const CATEGORY_LABELS: Record<TicketCategory, string> = {
  REQUEST: "Demande",
  INCIDENT: "Incident",
  ANOMALY: "Anomalie",
  VALIDATION: "Validation"
};

const ROLE_LABELS: Record<Role, string> = {
  USER: "Utilisateur",
  IT_AGENT: "Agent informatique",
  ADMIN: "Administrateur"
};

export function statusLabel(value: TicketStatus | string): string {
  return STATUS_LABELS[value as TicketStatus] || value;
}

export function priorityLabel(value: TicketPriority | string): string {
  return PRIORITY_LABELS[value as TicketPriority] || value;
}

export function categoryLabel(value: TicketCategory | string): string {
  return CATEGORY_LABELS[value as TicketCategory] || value;
}

export function roleLabel(value: Role | string): string {
  return ROLE_LABELS[value as Role] || value;
}

export function modeLabel(isDepartmentBroadcast: boolean): string {
  return isDepartmentBroadcast ? "Pour le departement" : "Pour une personne";
}
