import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import ProtectedRoute from "./components/ProtectedRoute";
import AdminRoute from "./components/AdminRoute";
import Navbar from "./components/Navbar";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import DashboardPage from "./pages/DashboardPage";
import TasksPage from "./pages/TasksPage";
import TaskFormPage from "./pages/TaskFormPage";
import TaskDetailPage from "./pages/TaskDetailPage";
import AdminDashboardPage from "./pages/admin/AdminDashboardPage";
import AdminUsersPage from "./pages/admin/AdminUsersPage";
import AdminUserDetailPage from "./pages/admin/AdminUserDetailPage";
import AdminTasksPage from "./pages/admin/AdminTasksPage";

function AppRoutes() {
  const { user } = useAuth();

  return (
    <>
      <Navbar />
      <main className="app-main">
        <Routes>
          <Route path="/login" element={user ? <Navigate to="/" replace /> : <LoginPage />} />
          <Route path="/register" element={user ? <Navigate to="/" replace /> : <RegisterPage />} />

          <Route
            path="/"
            element={
              <ProtectedRoute>
                <DashboardPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/tasks"
            element={
              <ProtectedRoute>
                <TasksPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/tasks/new"
            element={
              <ProtectedRoute>
                <TaskFormPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/tasks/:taskId"
            element={
              <ProtectedRoute>
                <TaskDetailPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/tasks/:taskId/edit"
            element={
              <ProtectedRoute>
                <TaskFormPage />
              </ProtectedRoute>
            }
          />

          <Route path="/admin" element={<AdminRoute><AdminDashboardPage /></AdminRoute>} />
          <Route path="/admin/users" element={<AdminRoute><AdminUsersPage /></AdminRoute>} />
          <Route path="/admin/users/:userId" element={<AdminRoute><AdminUserDetailPage /></AdminRoute>} />
          <Route path="/admin/tasks" element={<AdminRoute><AdminTasksPage /></AdminRoute>} />

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}
