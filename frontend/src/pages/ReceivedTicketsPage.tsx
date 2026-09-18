import { useMemo, useState } from "react";
import { AxiosError } from "axios";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { referenceApi, ticketApi } from "../api/services";
import { useAuth } from "../components/AuthProvider";
import { categoryLabel, modeLabel, priorityLabel, STATUS_VALUES, statusLabel } from "../i18n/fr";
import type { Ticket, TicketCategory, TicketPriority, TicketStatus } from "../types/api";

const RECEIVED_TRANSITIONS: Record<TicketStatus, TicketStatus[]> = {
  NEW: ["IN_PROGRESS"],
  IN_PROGRESS: ["ON_HOLD", "RESOLVED"],
  ON_HOLD: ["IN_PROGRESS"],
  RESOLVED: ["IN_PROGRESS"],
  CLOSED: []
};

function assignmentTypeLabel(ticket: Ticket): string {
  if (!ticket.assignee) {
    if (ticket.is_department_broadcast) {
      return "En attente d'affectation par le chef";
    }
    return "Non assigne";
  }
  if (ticket.is_department_broadcast) {
    return "Affecte par le chef du departement";
  }
  return "Affectation directe";
}

export function ReceivedTicketsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();

  const [statusFilter, setStatusFilter] = useState<string>("");
  const [priorityFilter, setPriorityFilter] = useState<string>("");
  const [categoryFilter, setCategoryFilter] = useState<string>("");
  const [targetDepartmentFilter, setTargetDepartmentFilter] = useState<number>(0);
  const [assigneeFilter, setAssigneeFilter] = useState<string>("");
  const [statusSelectionByTicket, setStatusSelectionByTicket] = useState<Record<string, TicketStatus>>({});
  const [assigneeSelectionByTicket, setAssigneeSelectionByTicket] = useState<Record<string, string>>({});

  const departments = useQuery({
    queryKey: ["departments"],
    queryFn: () => referenceApi.departments()
  });
  const categories = useQuery({
    queryKey: ["categories"],
    queryFn: () => referenceApi.categories()
  });
  const priorities = useQuery({
    queryKey: ["priorities"],
    queryFn: () => referenceApi.priorities()
  });
  const assignableUsers = useQuery({
    queryKey: ["assignable-users", "received"],
    queryFn: () => referenceApi.assignableUsers()
  });

  const receivedParams = useMemo(
    () => ({
      status: statusFilter ? (statusFilter as TicketStatus) : undefined,
      priority: priorityFilter ? (priorityFilter as TicketPriority) : undefined,
      category: categoryFilter ? (categoryFilter as TicketCategory) : undefined,
      target_department_id: targetDepartmentFilter > 0 ? targetDepartmentFilter : undefined,
      assignee_id: assigneeFilter || undefined
    }),
    [statusFilter, priorityFilter, categoryFilter, targetDepartmentFilter, assigneeFilter]
  );

  const tickets = useQuery({
    queryKey: ["tickets-received", receivedParams],
    queryFn: () => ticketApi.listReceived(receivedParams)
  });

  const statusMutation = useMutation({
    mutationFn: ({ ticketId, toStatus }: { ticketId: string; toStatus: TicketStatus }) =>
      ticketApi.changeStatus(ticketId, { to_status: toStatus }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tickets-received"] });
      queryClient.invalidateQueries({ queryKey: ["tickets-sent"] });
      queryClient.invalidateQueries({ queryKey: ["ticket"] });
    }
  });

  const assignMutation = useMutation({
    mutationFn: ({ ticketId, assigneeId }: { ticketId: string; assigneeId: string }) =>
      ticketApi.patch(ticketId, { assignee_id: assigneeId }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tickets-received"] });
      queryClient.invalidateQueries({ queryKey: ["tickets-sent"] });
      queryClient.invalidateQueries({ queryKey: ["ticket"] });
    }
  });

  const mutationErrorMessage = useMemo(() => {
    const error = statusMutation.error || assignMutation.error;
    if (!error) return null;
    if (error instanceof AxiosError) {
      const detail = error.response?.data?.detail;
      if (typeof detail === "string" && detail.trim()) return detail;
    }
    return "Action impossible.";
  }, [statusMutation.error, assignMutation.error]);

  return (
    <section className="stack">
      <h2>Tickets recus a traiter</h2>
      <p className="muted">Ici, vous voyez l&apos;origine du ticket et son mode d&apos;affectation.</p>

      <article className="card stack">
        <h3>Filtres</h3>
        <div className="grid-2">
          <label>
            Statut
            <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
              <option value="">Tous</option>
              {STATUS_VALUES.map((value) => (
                <option key={value} value={value}>
                  {statusLabel(value)}
                </option>
              ))}
            </select>
          </label>
          <label>
            Priorite
            <select value={priorityFilter} onChange={(event) => setPriorityFilter(event.target.value)}>
              <option value="">Toutes</option>
              {(priorities.data || []).map((item) => (
                <option key={item} value={item}>
                  {priorityLabel(item)}
                </option>
              ))}
            </select>
          </label>
          <label>
            Categorie
            <select value={categoryFilter} onChange={(event) => setCategoryFilter(event.target.value)}>
              <option value="">Toutes</option>
              {(categories.data || []).map((item) => (
                <option key={item} value={item}>
                  {categoryLabel(item)}
                </option>
              ))}
            </select>
          </label>
          <label>
            Departement cible
            <select
              value={targetDepartmentFilter}
              onChange={(event) => setTargetDepartmentFilter(Number(event.target.value))}
            >
              <option value={0}>Tous</option>
              {(departments.data || []).map((department) => (
                <option key={department.id} value={department.id}>
                  {department.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Assigne a
            <select value={assigneeFilter} onChange={(event) => setAssigneeFilter(event.target.value)}>
              <option value="">Tous</option>
              {(assignableUsers.data || []).map((user) => (
                <option key={user.id} value={user.id}>
                  {user.full_name}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="ticket-actions">
          <button
            type="button"
            onClick={() => {
              setStatusFilter("");
              setPriorityFilter("");
              setCategoryFilter("");
              setTargetDepartmentFilter(0);
              setAssigneeFilter("");
            }}
          >
            Reinitialiser les filtres
          </button>
        </div>
      </article>

      {mutationErrorMessage ? <p className="error">{mutationErrorMessage}</p> : null}

      <article className="card stack">
        <h3>Liste</h3>
        {tickets.isLoading ? <p>Chargement...</p> : null}
        {tickets.isError ? <p>Impossible de charger les tickets recus.</p> : null}
        <ul className="ticket-list ticket-list-received">
          {(tickets.data || []).map((ticket) => {
            const allowedTransitions = RECEIVED_TRANSITIONS[ticket.status] || [];
            const selectedStatus =
              statusSelectionByTicket[ticket.id] || allowedTransitions[0] || ("NEW" as TicketStatus);
            const selectedAssignee = assigneeSelectionByTicket[ticket.id] || ticket.assignee?.id || "";
            const assignmentInfo = assignmentTypeLabel(ticket);
            const createdAtLabel = new Date(ticket.created_at).toLocaleString();

            return (
              <li key={ticket.id} className="ticket-card">
                <div className="ticket-main">
                  <h4 className="ticket-title">{ticket.title}</h4>
                  <p className="ticket-subline">
                    Recu le {createdAtLabel} - categorie: {categoryLabel(ticket.category)}
                  </p>
                  <div className="ticket-info-grid">
                    <span className={`status status-${ticket.status}`}>{statusLabel(ticket.status)}</span>
                    <span className="info-chip">Priorite: {priorityLabel(ticket.priority)}</span>
                    <span className="info-chip">Source: {ticket.emitter_department.name}</span>
                    <span className="info-chip">Emetteur: {ticket.creator.full_name}</span>
                    <span className="info-chip">Cible: {ticket.target_department.name}</span>
                    <span className="info-chip">Mode: {modeLabel(ticket.is_department_broadcast)}</span>
                    <span className="info-chip">Affectation: {assignmentInfo}</span>
                    <span className="info-chip">Assigne: {ticket.assignee?.full_name || "Aucun"}</span>
                  </div>
                </div>
                <div className="action-panel stack">
                  <div className="ticket-actions action-group">
                    {ticket.is_department_broadcast && !ticket.assignee ? (
                      <small className="ticket-note">Le chef doit d&apos;abord affecter ce ticket.</small>
                    ) : null}
                    <select
                      value={selectedStatus}
                      disabled={allowedTransitions.length === 0 || (ticket.is_department_broadcast && !ticket.assignee)}
                      onChange={(event) =>
                        setStatusSelectionByTicket((prev) => ({
                          ...prev,
                          [ticket.id]: event.target.value as TicketStatus
                        }))
                      }
                    >
                      {allowedTransitions.length === 0 ? <option value="">Aucune transition</option> : null}
                      {allowedTransitions.map((item) => (
                        <option key={item} value={item}>
                          {statusLabel(item)}
                        </option>
                      ))}
                    </select>
                    <button
                      disabled={
                        allowedTransitions.length === 0 ||
                        statusMutation.isPending ||
                        (ticket.is_department_broadcast && !ticket.assignee)
                      }
                      onClick={() => statusMutation.mutate({ ticketId: ticket.id, toStatus: selectedStatus })}
                    >
                      Traiter
                    </button>
                  </div>
                  <div className="ticket-actions action-group">
                    <select
                      value={selectedAssignee}
                      onChange={(event) =>
                        setAssigneeSelectionByTicket((prev) => ({
                          ...prev,
                          [ticket.id]: event.target.value
                        }))
                      }
                    >
                      <option value="">Aucun assigne</option>
                      {(assignableUsers.data || []).map((user) => (
                        <option key={user.id} value={user.id}>
                          {user.full_name}
                        </option>
                      ))}
                    </select>
                    <button
                      disabled={
                        !selectedAssignee ||
                        assignMutation.isPending ||
                        !(
                          user?.role === "ADMIN" ||
                          user?.role === "IT_AGENT" ||
                          (user?.is_department_head && user.department_id === ticket.target_department.id)
                        )
                      }
                      onClick={() => assignMutation.mutate({ ticketId: ticket.id, assigneeId: selectedAssignee })}
                    >
                      Affecter
                    </button>
                  </div>
                  <button onClick={() => navigate(`/tickets/${ticket.id}`)}>Voir</button>
                </div>
              </li>
            );
          })}
        </ul>
      </article>
    </section>
  );
}
