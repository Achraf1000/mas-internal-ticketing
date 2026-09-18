import { useQuery } from "@tanstack/react-query";
import { AxiosError } from "axios";
import { tokenStorage } from "../api/client";
import { useAuth } from "../components/AuthProvider";
import { adminApi } from "../api/services";
import { roleLabel } from "../i18n/fr";

export function AdminUsersPage() {
  const { user } = useAuth();
  const canLoadUsers = user?.role === "ADMIN" && !!tokenStorage.getAccessToken();

  const users = useQuery({
    queryKey: ["admin-users"],
    queryFn: () => adminApi.users(),
    enabled: canLoadUsers
  });

  if (!canLoadUsers) return <p>Session invalide. Reconnecte-toi.</p>;
  if (users.isLoading) return <p>Chargement utilisateurs...</p>;
  if (users.isError || !users.data) {
    if (users.error instanceof AxiosError && users.error.response?.status === 401) {
      return <p>Session expiree. Reconnecte-toi.</p>;
    }
    return <p>Impossible de charger les utilisateurs.</p>;
  }

  return (
    <section className="stack">
      <h2>Administration des utilisateurs</h2>
      <article className="card">
        <table>
          <thead>
            <tr>
              <th>Nom</th>
              <th>Email</th>
              <th>Role</th>
              <th>Departement</th>
              <th>Actif</th>
            </tr>
          </thead>
          <tbody>
            {users.data.map((user) => (
              <tr key={user.id}>
                <td>{user.full_name}</td>
                <td>{user.email}</td>
                <td>{roleLabel(user.role)}</td>
                <td>{user.department_id || "-"}</td>
                <td>{user.is_active ? "Oui" : "Non"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </article>
    </section>
  );
}
