import { Navigate } from "react-router-dom";
import type { PropsWithChildren } from "react";
import { useAuth } from "./AuthProvider";

export function ProtectedRoute({ children }: PropsWithChildren) {
  const { user, isLoading } = useAuth();
  if (isLoading) {
    return <div className="centered">Chargement...</div>;
  }
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

