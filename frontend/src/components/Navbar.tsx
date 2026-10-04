import { NavLink, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const linkClass = ({ isActive }: { isActive: boolean }) => (isActive ? "active" : "");

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  if (!user) return null;

  const inAdmin = location.pathname.startsWith("/admin");

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <nav className={`navbar ${inAdmin ? "navbar-admin" : ""}`}>
      <div className="navbar-brand">
        Smart Student Task Manager
        {inAdmin && <span className="admin-tag">Admin</span>}
      </div>
      <div className="navbar-links">
        {inAdmin ? (
          <>
            <NavLink to="/admin" end className={linkClass}>
              Overview
            </NavLink>
            <NavLink to="/admin/users" className={linkClass}>
              Users
            </NavLink>
            <NavLink to="/admin/tasks" className={linkClass}>
              All tasks
            </NavLink>
            <NavLink to="/" end className="switch-link">
              My tasks →
            </NavLink>
          </>
        ) : (
          <>
            <NavLink to="/" end className={linkClass}>
              Dashboard
            </NavLink>
            <NavLink to="/tasks" end className={linkClass}>
              Tasks
            </NavLink>
            <NavLink to="/tasks/new" className={linkClass}>
              New Task
            </NavLink>
            {user.is_admin && (
              <NavLink to="/admin" className="switch-link">
                Admin panel →
              </NavLink>
            )}
          </>
        )}
      </div>
      <div className="navbar-user">
        <NavLink to="/profile" className={({ isActive }) => `profile-link ${isActive ? "active" : ""}`} title="My profile">
          <span className="avatar" aria-hidden="true">
            {user.name.trim().charAt(0).toUpperCase()}
          </span>
          <span>{user.name}</span>
          <span className="profile-id">ID {user.id}</span>
        </NavLink>
        <button className="btn btn-secondary btn-sm" onClick={handleLogout}>
          Log out
        </button>
      </div>
    </nav>
  );
}
