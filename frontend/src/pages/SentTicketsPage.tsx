import { useMemo, useState } from "react";
import { AxiosError } from "axios";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { referenceApi, ticketApi } from "../api/services";
import { ACTIVE_STATUS_VALUES, categoryLabel, modeLabel, priorityLabel, statusLabel } from "../i18n/fr";
import type { TicketCategory, TicketPriority, TicketStatus } from "../types/api";

export function SentTicketsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [statusFilter, setStatusFilter] = useState<string>("");
  const [priorityFilter, setPriorityFilter] = useState<string>("");
  const [categoryFilter, setCategoryFilter] = useState<string>("");
  const [closeReasonByTicket, setCloseReasonByTicket] = useState<Record<string, string>>({});

  const categories = useQuery({
    queryKey: ["categories"],
    queryFn: () => referenceApi.categories()
  });
  const priorities = useQuery({
    queryKey: ["priorities"],
    queryFn: () => referenceApi.priorities()
  });

  const sentParams = useMemo(
    () => ({
      status: statusFilter ? (statusFilter as TicketStatus) : undefined,
      priority: priorityFilter ? (priorityFilter as TicketPriority) : undefined,
      category: categoryFilter ? (categoryFilter as TicketCategory) : undefined,
      include_closed: false
    }),
    [statusFilter, priorityFilter, categoryFilter]
  );

  const tickets = useQuery({
    queryKey: ["tickets-sent", sentParams],
    queryFn: () => ticketApi.listSent(sentParams)
  });

  const closeMutation = useMutation({
    mutationFn: ({ ticketId, reason }: { ticketId: string; reason?: string }) =>
      ticketApi.changeStatus(ticketId, { to_status: "CLOSED", reason }),
    onSuccess: (_, variables) => {
      setCloseReasonByTicket((prev) => ({ ...prev, [variables.ticketId]: "" }));
      queryClient.invalidateQueries({ queryKey: ["tickets-sent"] });
      queryClient.invalidateQueries({ queryKey: ["tickets-archive"] });
      queryClient.invalidateQueries({ queryKey: ["tickets-received"] });
      queryClient.invalidateQueries({ queryKey: ["ticket"] });
    }
  });

  const mutationErrorMessage = useMemo(() => {
    const error = closeMutation.error;
    if (!error) return null;
    if (error instanceof AxiosError) {
      const detail = error.response?.data?.detail;
      if (typeof detail === "string" && detail.trim()) return detail;
    }
    return "Action impossible.";
  }, [closeMutation.error]);

  return (
    <section className="stack">
      <h2>Tickets envoyes</h2>

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
        </div>
      </article>

      {mutationErrorMessage ? <p className="error">{mutationErrorMessage}</p> : null}
      <p className="muted">
        Les tickets clotures sont deplaces dans l&apos;archive mensuelle.
        <button className="inline-action-btn" onClick={() => navigate("/tickets/archive")} type="button">
          Ouvrir archive
        </button>
      </p>

      <article className="card stack">
        <h3>Suivi des etats</h3>
        {tickets.isLoading ? <p>Chargement...</p> : null}
        {tickets.isError ? <p>Impossible de charger les tickets envoyes.</p> : null}
        <ul className="ticket-list">
          {(tickets.data || []).map((ticket) => {
            const closeReason = closeReasonByTicket[ticket.id] || "";
            return (
              <li key={ticket.id}>
                <div>
                  <strong>{ticket.ticket_code}</strong> - {ticket.title}
                  <div>
                    <span className={`status status-${ticket.status}`}>{statusLabel(ticket.status)}</span>
                    {" | "}
                    {priorityLabel(ticket.priority)}
                    {" | "}
                    departement cible: {ticket.target_department.name}
                    {" | "}
                    mode: {modeLabel(ticket.is_department_broadcast)}
                  </div>
                </div>
                <div className="stack">
                  {ticket.status === "RESOLVED" ? (
                    <div className="stack">
                      <div className="ticket-actions">
                        <input
                          placeholder="Note simple (optionnel)"
                          value={closeReason}
                          onChange={(event) =>
                            setCloseReasonByTicket((prev) => ({ ...prev, [ticket.id]: event.target.value }))
                          }
                        />
                        <button
                          disabled={closeMutation.isPending}
                          onClick={() =>
                            closeMutation.mutate({
                              ticketId: ticket.id,
                              reason: closeReason.trim() || undefined
                            })
                          }
                        >
                          {closeMutation.isPending ? "Confirmation..." : "Valider le travail et cloturer"}
                        </button>
                      </div>
                    </div>
                  ) : null}
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
