import { Navigate, Route, Routes } from "react-router-dom";
import { AppLayout } from "./components/AppLayout";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { AdminUsersPage } from "./pages/AdminUsersPage";
import { DashboardPage } from "./pages/DashboardPage";
import { LoginPage } from "./pages/LoginPage";
import { ProfilePage } from "./pages/ProfilePage";
import { ReceivedTicketsPage } from "./pages/ReceivedTicketsPage";
import { SentTicketsPage } from "./pages/SentTicketsPage";
import { TicketArchivePage } from "./pages/TicketArchivePage";
import { TicketDetailPage } from "./pages/TicketDetailPage";
import { ToAssignTicketsPage } from "./pages/ToAssignTicketsPage";
import { TicketsPage } from "./pages/TicketsPage";
import { useAuth } from "./components/AuthProvider";

function AdminOnly({ children }: { children: JSX.Element }) {
  const { user } = useAuth();
  if (user?.role !== "ADMIN") {
    return <Navigate to="/dashboard" replace />;
  }
  return children;
}

function TicketsLanding() {
  const { user } = useAuth();
  const isDepartmentHeadUser = !!user?.is_department_head && user?.role !== "ADMIN" && user?.role !== "IT_AGENT";
  if (isDepartmentHeadUser) {
    return <Navigate to="/tickets/to-assign" replace />;
  }
  return <Navigate to="/tickets/received" replace />;
}

function ReceivedTicketsEntry() {
  const { user } = useAuth();
  const isDepartmentHeadUser = !!user?.is_department_head && user?.role !== "ADMIN" && user?.role !== "IT_AGENT";
  if (isDepartmentHeadUser) {
    return <Navigate to="/tickets/to-assign" replace />;
  }
  return <ReceivedTicketsPage />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="tickets" element={<TicketsLanding />} />
        <Route path="tickets/new" element={<TicketsPage />} />
        <Route path="tickets/received" element={<ReceivedTicketsEntry />} />
        <Route path="tickets/to-assign" element={<ToAssignTicketsPage />} />
        <Route path="tickets/sent" element={<SentTicketsPage />} />
        <Route path="tickets/archive" element={<TicketArchivePage />} />
        <Route path="tickets/:ticketId" element={<TicketDetailPage />} />
        <Route path="profile" element={<ProfilePage />} />
        <Route
          path="admin/users"
          element={
            <AdminOnly>
              <AdminUsersPage />
            </AdminOnly>
          }
        />
      </Route>
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
