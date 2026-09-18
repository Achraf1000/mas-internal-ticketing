import { NavLink, Outlet } from "react-router-dom";
import { roleLabel } from "../i18n/fr";
import { useAuth } from "./AuthProvider";

export function AppLayout() {
  const { user, logout } = useAuth();
  const isDepartmentHeadUser = !!user?.is_department_head && user?.role !== "ADMIN" && user?.role !== "IT_AGENT";
  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand">
          <img className="brand-logo" src="/branding/MAS-GROUP-LOGO.png" alt="Logo MAS" />
          <div className="brand-text">
            <h1>MAS Tickets</h1>
            <p>Plateforme interne de tickets</p>
          </div>
        </div>
        <div className="topbar-meta">
          <span>{user?.full_name}</span>
          <span className="pill">{user?.role ? roleLabel(user.role) : "-"}</span>
          <button onClick={() => logout()}>Se deconnecter</button>
        </div>
      </header>
      <div className="content-grid">
        <aside className="sidebar">
          <NavLink to="/dashboard">Tableau de bord</NavLink>
          <NavLink to="/tickets/new">Nouveau ticket</NavLink>
          {isDepartmentHeadUser ? (
            <NavLink to="/tickets/to-assign">Taches a assigner</NavLink>
          ) : (
            <NavLink to="/tickets/received">Recus a traiter</NavLink>
          )}
          <NavLink to="/tickets/sent">Tickets envoyes</NavLink>
          <NavLink to="/tickets/archive">Archive mensuelle</NavLink>
          <NavLink to="/profile">Mon profil</NavLink>
          {user?.role === "ADMIN" ? <NavLink to="/admin/users">Utilisateurs</NavLink> : null}
        </aside>
        <main className="main">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
