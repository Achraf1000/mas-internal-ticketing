import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { useAuth } from "../components/AuthProvider";

interface LoginForm {
  email: string;
  password: string;
}

export function LoginPage() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const { register, handleSubmit, formState } = useForm<LoginForm>({
    defaultValues: { email: "", password: "" }
  });

  const onSubmit = async (values: LoginForm) => {
    setError(null);
    try {
      await login(values.email, values.password);
      navigate("/dashboard", { replace: true });
    } catch {
      setError("Email ou mot de passe invalide");
    }
  };

  return (
    <div className="login-wrap">
      <form className="card" onSubmit={handleSubmit(onSubmit)}>
        <div className="login-brand">
          <img className="login-logo" src="/branding/MAS-GROUP-LOGO.png" alt="Logo MAS" />
          <p>Plateforme interne de tickets</p>
        </div>
        <h2>Connexion interne MAS</h2>
        <label>
          Email
          <input type="email" {...register("email", { required: true })} />
        </label>
        <label>
          Mot de passe
          <input type="password" {...register("password", { required: true })} />
        </label>
        {error ? <p className="error">{error}</p> : null}
        <button disabled={formState.isSubmitting} type="submit">
          {formState.isSubmitting ? "Connexion..." : "Se connecter"}
        </button>
      </form>
    </div>
  );
}
