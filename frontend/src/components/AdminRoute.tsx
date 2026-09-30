import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

/** Client-side guard for admin pages. The real enforcement is server-side
 *  (every /admin endpoint returns 403 for non-admins); this just keeps
 *  students from landing on a broken page. */
export default function AdminRoute({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="page-loading">Loading...</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (!user.is_admin) return <Navigate to="/" replace />;
  return <>{children}</>;
}
