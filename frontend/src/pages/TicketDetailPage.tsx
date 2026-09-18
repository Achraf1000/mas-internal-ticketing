import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { ticketApi } from "../api/services";
import { priorityLabel, statusLabel } from "../i18n/fr";
import type { TicketStatus } from "../types/api";

const STATUS_OPTIONS: TicketStatus[] = ["NEW", "IN_PROGRESS", "ON_HOLD", "RESOLVED"];

export function TicketDetailPage() {
  const { ticketId = "" } = useParams();
  const queryClient = useQueryClient();
  const [comment, setComment] = useState("");
  const [selectedStatus, setSelectedStatus] = useState<TicketStatus>("IN_PROGRESS");

  const ticket = useQuery({
    queryKey: ["ticket", ticketId],
    queryFn: () => ticketApi.get(ticketId),
    enabled: Boolean(ticketId)
  });

  const statusMutation = useMutation({
    mutationFn: (statusValue: TicketStatus) => ticketApi.changeStatus(ticketId, { to_status: statusValue }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ticket", ticketId] });
      queryClient.invalidateQueries({ queryKey: ["tickets"] });
    }
  });

  const commentMutation = useMutation({
    mutationFn: () => ticketApi.comment(ticketId, comment),
    onSuccess: () => {
      setComment("");
      queryClient.invalidateQueries({ queryKey: ["ticket", ticketId] });
    }
  });

  const attachmentMutation = useMutation({
    mutationFn: (file: File) => ticketApi.uploadAttachment(ticketId, file),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["ticket", ticketId] })
  });

  if (ticket.isLoading) return <p>Chargement du ticket...</p>;
  if (ticket.isError || !ticket.data) return <p>Ticket introuvable.</p>;

  return (
    <section className="stack">
      <h2>
        {ticket.data.ticket_code} - {ticket.data.title}
      </h2>
      <article className="card">
        <p>{ticket.data.description}</p>
        <p>
          Statut: <strong>{statusLabel(ticket.data.status)}</strong> | Priorite: <strong>{priorityLabel(ticket.data.priority)}</strong>
        </p>
      </article>

      <div className="grid-2">
        <article className="card stack">
          <h3>Transition de statut</h3>
          <p>La cloture finale est validee par l&apos;emetteur depuis la vue "Tickets envoyes".</p>
          <select value={selectedStatus} onChange={(event) => setSelectedStatus(event.target.value as TicketStatus)}>
            {STATUS_OPTIONS.map((statusOption) => (
              <option key={statusOption} value={statusOption}>
                {statusLabel(statusOption)}
              </option>
            ))}
          </select>
          <button onClick={() => statusMutation.mutate(selectedStatus)} disabled={statusMutation.isPending}>
            {statusMutation.isPending ? "Mise a jour..." : "Changer le statut"}
          </button>
        </article>
        <article className="card stack">
          <h3>Ajouter un commentaire</h3>
          <textarea rows={4} value={comment} onChange={(event) => setComment(event.target.value)} />
          <button onClick={() => commentMutation.mutate()} disabled={commentMutation.isPending || !comment.trim()}>
            {commentMutation.isPending ? "Envoi..." : "Envoyer"}
          </button>
        </article>
      </div>

      <article className="card stack">
        <h3>Pieces jointes</h3>
        <input
          type="file"
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) attachmentMutation.mutate(file);
          }}
        />
        <ul>
          {ticket.data.attachments.map((attachment) => (
            <li key={attachment.id}>
              <button
                onClick={() =>
                  ticketApi.downloadAttachment(ticketId, attachment.id, attachment.filename)
                }
              >
                Ouvrir {attachment.filename}
              </button>
            </li>
          ))}
        </ul>
      </article>

      <article className="card stack">
        <h3>Historique</h3>
        <ul>
          {ticket.data.status_history.map((entry) => (
            <li key={entry.id}>
              {entry.from_status ? statusLabel(entry.from_status) : "Aucun"} -&gt; {statusLabel(entry.to_status)} (
              {new Date(entry.changed_at).toLocaleString()})
            </li>
          ))}
        </ul>
      </article>

      <article className="card stack">
        <h3>Commentaires</h3>
        <ul>
          {ticket.data.comments.map((entry) => (
            <li key={entry.id}>
              <strong>{entry.author.full_name}</strong>: {entry.body}
            </li>
          ))}
        </ul>
      </article>
    </section>
  );
}
