import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { ticketApi } from "../api/services";
import { priorityLabel, statusLabel } from "../i18n/fr";

const MONTH_OPTIONS = [
  { value: 1, label: "Janvier" },
  { value: 2, label: "Fevrier" },
  { value: 3, label: "Mars" },
  { value: 4, label: "Avril" },
  { value: 5, label: "Mai" },
  { value: 6, label: "Juin" },
  { value: 7, label: "Juillet" },
  { value: 8, label: "Aout" },
  { value: 9, label: "Septembre" },
  { value: 10, label: "Octobre" },
  { value: 11, label: "Novembre" },
  { value: 12, label: "Decembre" }
];

export function TicketArchivePage() {
  const navigate = useNavigate();
  const now = useMemo(() => new Date(), []);
  const [month, setMonth] = useState<number>(now.getMonth() + 1);
  const [year, setYear] = useState<number>(now.getFullYear());

  const archive = useQuery({
    queryKey: ["tickets-archive", year, month],
    queryFn: () => ticketApi.listArchive({ year, month })
  });

  return (
    <section className="stack">
      <h2>Archive mensuelle</h2>
      <article className="card stack">
        <h3>Filtres</h3>
        <div className="grid-2">
          <label>
            Mois
            <select value={month} onChange={(event) => setMonth(Number(event.target.value))}>
              {MONTH_OPTIONS.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Annee
            <input
              type="number"
              value={year}
              min={2000}
              max={2100}
              onChange={(event) => setYear(Number(event.target.value))}
            />
          </label>
        </div>
      </article>

      <article className="card stack">
        <h3>Tickets clotures</h3>
        {archive.isLoading ? <p>Chargement...</p> : null}
        {archive.isError ? <p>Impossible de charger l&apos;archive.</p> : null}
        {!archive.isLoading && !archive.isError && (archive.data || []).length === 0 ? (
          <p>Aucun ticket cloture pour cette periode.</p>
        ) : null}
        <ul className="ticket-list">
          {(archive.data || []).map((ticket) => (
            <li key={ticket.id}>
              <div>
                <strong>{ticket.ticket_code}</strong> - {ticket.title}
                <div>
                  <span className={`status status-${ticket.status}`}>{statusLabel(ticket.status)}</span>
                  {" | "}
                  {priorityLabel(ticket.priority)}
                  {" | "}
                  cloture le: {ticket.closed_at ? new Date(ticket.closed_at).toLocaleString() : "-"}
                </div>
              </div>
              <div className="ticket-actions">
                <button onClick={() => navigate(`/tickets/${ticket.id}`)}>Voir</button>
              </div>
            </li>
          ))}
        </ul>
      </article>
    </section>
  );
}
