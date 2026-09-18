import { useQuery } from "@tanstack/react-query";
import { reportApi } from "../api/services";
import { useAuth } from "../components/AuthProvider";
import { priorityLabel, statusLabel } from "../i18n/fr";

function GlobalManagementDashboard() {
  const overview = useQuery({
    queryKey: ["report-overview"],
    queryFn: () => reportApi.overview()
  });

  if (overview.isLoading) return <p>Chargement du tableau de bord...</p>;
  if (overview.isError || !overview.data) return <p>Impossible de charger le tableau de bord.</p>;

  return (
    <section className="stack">
      <h2>Tableau de bord global</h2>
      <div className="kpi-grid">
        <article className="card">
          <h3>Total tickets</h3>
          <strong>{overview.data.total_tickets}</strong>
        </article>
        <article className="card">
          <h3>Tickets ouverts</h3>
          <strong>{overview.data.open_tickets}</strong>
        </article>
        <article className="card">
          <h3>Tickets en retard SLA</h3>
          <strong>{overview.data.overdue_tickets}</strong>
        </article>
      </div>
      <div className="grid-2">
        <article className="card">
          <h3>Par statut</h3>
          <ul>
            {overview.data.by_status.map((item) => (
              <li key={item.key}>
                {statusLabel(item.key)}: <strong>{item.count}</strong>
              </li>
            ))}
          </ul>
        </article>
        <article className="card">
          <h3>Par priorite</h3>
          <ul>
            {overview.data.by_priority.map((item) => (
              <li key={item.key}>
                {priorityLabel(item.key)}: <strong>{item.count}</strong>
              </li>
            ))}
          </ul>
        </article>
      </div>
      <article className="card">
        <h3>Utilisateurs x etats</h3>
        <table>
          <thead>
            <tr>
              <th>Utilisateur</th>
              <th>Departement</th>
              <th>Nouveau</th>
              <th>En cours</th>
              <th>En pause</th>
              <th>Resolu</th>
              <th>Cloture</th>
              <th>Total</th>
            </tr>
          </thead>
          <tbody>
            {overview.data.by_user_status.map((row) => (
              <tr key={row.user_id}>
                <td>{row.user_name}</td>
                <td>{row.department_name || "-"}</td>
                <td>{row.new_count}</td>
                <td>{row.in_progress_count}</td>
                <td>{row.on_hold_count}</td>
                <td>{row.resolved_count}</td>
                <td>{row.closed_count}</td>
                <td>{row.total_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </article>
    </section>
  );
}

function DepartmentHeadDashboard() {
  const report = useQuery({
    queryKey: ["department-head-overview"],
    queryFn: () => reportApi.departmentHeadOverview()
  });

  if (report.isLoading) return <p>Chargement du tableau chef...</p>;
  if (report.isError || !report.data) return <p>Impossible de charger les indicateurs du departement.</p>;

  return (
    <section className="stack">
      <h2>
        Tableau chef - {report.data.department_name} ({report.data.month}/{report.data.year})
      </h2>
      <div className="kpi-grid">
        <article className="card">
          <h3>Recus (mois)</h3>
          <strong>{report.data.kpi.received_count}</strong>
        </article>
        <article className="card">
          <h3>Ouverts</h3>
          <strong>{report.data.kpi.open_count}</strong>
        </article>
        <article className="card">
          <h3>Resolus</h3>
          <strong>{report.data.kpi.resolved_count}</strong>
        </article>
      </div>
      <div className="kpi-grid">
        <article className="card">
          <h3>Clotures</h3>
          <strong>{report.data.kpi.closed_count}</strong>
        </article>
        <article className="card">
          <h3>En retard SLA</h3>
          <strong>{report.data.kpi.sla_overdue_count}</strong>
        </article>
        <article className="card">
          <h3>Delai moyen (h)</h3>
          <strong>{report.data.kpi.avg_resolution_hours ?? "-"}</strong>
        </article>
      </div>
      <div className="grid-2">
        <article className="card">
          <h3>Par statut</h3>
          <ul>
            {report.data.by_status.map((item) => (
              <li key={item.key}>
                {statusLabel(item.key)}: <strong>{item.count}</strong>
              </li>
            ))}
          </ul>
        </article>
        <article className="card">
          <h3>Par priorite</h3>
          <ul>
            {report.data.by_priority.map((item) => (
              <li key={item.key}>
                {priorityLabel(item.key)}: <strong>{item.count}</strong>
              </li>
            ))}
          </ul>
        </article>
      </div>
      <article className="card">
        <h3>Performance membres</h3>
        <table>
          <thead>
            <tr>
              <th>Membre</th>
              <th>Nouveau</th>
              <th>En cours</th>
              <th>En pause</th>
              <th>Resolu</th>
              <th>Cloture</th>
              <th>Ouverts assignes</th>
              <th>Resolus/Clotures</th>
              <th>Retard SLA</th>
              <th>Delai moyen (h)</th>
            </tr>
          </thead>
          <tbody>
            {report.data.members.map((member) => (
              <tr key={member.member_id}>
                <td>{member.member_name}</td>
                <td>{member.new_count}</td>
                <td>{member.in_progress_count}</td>
                <td>{member.on_hold_count}</td>
                <td>{member.resolved_count}</td>
                <td>{member.closed_count}</td>
                <td>{member.assigned_open}</td>
                <td>{member.resolved_closed}</td>
                <td>{member.sla_overdue}</td>
                <td>{member.avg_resolution_hours ?? "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </article>
    </section>
  );
}

export function DashboardPage() {
  const { user } = useAuth();
  const isDepartmentHead = !!user?.is_department_head && !!user.department_id;
  const canViewGlobalReports = user?.role === "ADMIN" || user?.role === "IT_AGENT";

  if (canViewGlobalReports) {
    return <GlobalManagementDashboard />;
  }
  if (isDepartmentHead) {
    return <DepartmentHeadDashboard />;
  }

  return (
    <section className="stack">
      <h2>Tableau de bord</h2>
      <p>Ce tableau est pour chef de departement, IT et admin.</p>
    </section>
  );
}
