import { useMemo, useState } from "react";
import { AxiosError } from "axios";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { referenceApi, ticketApi } from "../api/services";
import { useAuth } from "../components/AuthProvider";
import { ACTIVE_STATUS_VALUES, categoryLabel, priorityLabel, statusLabel } from "../i18n/fr";
import type { TicketCategory, TicketPriority, TicketStatus } from "../types/api";

export function ToAssignTicketsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const canFilterTargetDepartment = user?.role === "ADMIN" || user?.role === "IT_AGENT";

  const [statusFilter, setStatusFilter] = useState<string>("");
  const [priorityFilter, setPriorityFilter] = useState<string>("");
  const [categoryFilter, setCategoryFilter] = useState<string>("");
  const [targetDepartmentFilter, setTargetDepartmentFilter] = useState<number>(0);
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
    queryKey: ["assignable-users", "to-assign", user?.department_id || null],
    queryFn: () => referenceApi.assignableUsers(user?.is_department_head ? user?.department_id || undefined : undefined)
  });

  const toAssignParams = useMemo(
    () => ({
      status: statusFilter ? (statusFilter as TicketStatus) : undefined,
      priority: priorityFilter ? (priorityFilter as TicketPriority) : undefined,
      category: categoryFilter ? (categoryFilter as TicketCategory) : undefined,
      target_department_id:
        canFilterTargetDepartment && targetDepartmentFilter > 0 ? targetDepartmentFilter : undefined
    }),
    [statusFilter, priorityFilter, categoryFilter, canFilterTargetDepartment, targetDepartmentFilter]
  );

  const tickets = useQuery({
    queryKey: ["tickets-to-assign", toAssignParams],
    queryFn: () => ticketApi.listToAssign(toAssignParams)
  });

  const assignMutation = useMutation({
    mutationFn: ({ ticketId, assigneeId }: { ticketId: string; assigneeId: string }) =>
      ticketApi.patch(ticketId, { assignee_id: assigneeId }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tickets-to-assign"] });
      queryClient.invalidateQueries({ queryKey: ["tickets-received"] });
      queryClient.invalidateQueries({ queryKey: ["tickets-sent"] });
      queryClient.invalidateQueries({ queryKey: ["ticket"] });
    }
  });

  const mutationErrorMessage = useMemo(() => {
    const error = assignMutation.error;
    if (!error) return null;
    if (error instanceof AxiosError) {
      const detail = error.response?.data?.detail;
      if (typeof detail === "string" && detail.trim()) return detail;
    }
    return "Action impossible.";
  }, [assignMutation.error]);

  return (
    <section className="stack">
      <h2>Taches a assigner</h2>

      <article className="card stack">
        <h3>Filtres</h3>
        <div className="grid-2">
          <label>
            Statut
            <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
              <option value="">Tous</option>
              {ACTIVE_STATUS_VALUES.map((value) => (
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
          {canFilterTargetDepartment ? (
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
          ) : null}
        </div>
      </article>

      {mutationErrorMessage ? <p className="error">{mutationErrorMessage}</p> : null}

      <article className="card stack">
        <h3>Tickets en attente d&apos;affectation</h3>
        {tickets.isLoading ? <p>Chargement...</p> : null}
        {tickets.isError ? <p>Impossible de charger les tickets a assigner.</p> : null}
        <ul className="ticket-list">
          {(tickets.data || []).map((ticket) => {
            const selectedAssignee = assigneeSelectionByTicket[ticket.id] || "";
            return (
              <li key={ticket.id}>
                <div>
                  <strong>{ticket.ticket_code}</strong> - {ticket.title}
                  <div>
                    <span className={`status status-${ticket.status}`}>{statusLabel(ticket.status)}</span>
                    {" | "}
                    {priorityLabel(ticket.priority)}
                    {" | "}
                    cible: {ticket.target_department.name}
                    {" | "}
                    emetteur: {ticket.creator.full_name}
                  </div>
                </div>
                <div className="stack">
                  <div className="ticket-actions">
                    <select
                      value={selectedAssignee}
                      onChange={(event) =>
                        setAssigneeSelectionByTicket((prev) => ({
                          ...prev,
                          [ticket.id]: event.target.value
                        }))
                      }
                    >
                      <option value="">Selectionner un assigne</option>
                      {(assignableUsers.data || []).map((assignableUser) => (
                        <option key={assignableUser.id} value={assignableUser.id}>
                          {assignableUser.full_name}
                        </option>
                      ))}
                    </select>
                    <button
                      disabled={!selectedAssignee || assignMutation.isPending}
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
