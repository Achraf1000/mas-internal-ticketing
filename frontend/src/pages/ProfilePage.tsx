import { useAuth } from "../components/AuthProvider";
import { roleLabel } from "../i18n/fr";

export function ProfilePage() {
  const { user } = useAuth();
  if (!user) return null;

  return (
    <section className="stack">
      <h2>Mon profil</h2>
      <article className="card">
        <p>
          <strong>Nom:</strong> {user.full_name}
        </p>
        <p>
          <strong>Email:</strong> {user.email}
        </p>
        <p>
          <strong>Role:</strong> {roleLabel(user.role)}
        </p>
        <p>
          <strong>Departement:</strong> {user.department_name || "-"}
        </p>
        <p>
          <strong>Chef de departement:</strong> {user.is_department_head ? "Oui" : "Non"}
        </p>
      </article>
    </section>
  );
}
