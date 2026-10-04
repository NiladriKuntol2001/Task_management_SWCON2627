import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { adminApi } from "../../api/client";
import type { AdminTask, AdminUserDetail } from "../../types";
import { useAuth } from "../../context/AuthContext";
import StatTile from "../../components/StatTile";
import AdminTaskTable from "../../components/admin/AdminTaskTable";
import TaskEditModal from "../../components/admin/TaskEditModal";
import UserFormModal from "../../components/admin/UserFormModal";
import ConfirmDialog from "../../components/ConfirmDialog";
import { formatDate, relativeTime, ROOT_ADMIN_ID } from "../../utils/format";

export default function AdminUserDetailPage() {
  const { userId } = useParams();
  const navigate = useNavigate();
  const { user: me } = useAuth();
  const [detail, setDetail] = useState<AdminUserDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [editingUser, setEditingUser] = useState(false);
  const [deletingUser, setDeletingUser] = useState(false);
  const [editingTask, setEditingTask] = useState<AdminTask | null>(null);
  const [deletingTask, setDeletingTask] = useState<AdminTask | null>(null);
  const [showCompleted, setShowCompleted] = useState(false);

  const load = () => {
    const id = Number(userId);
    if (!Number.isInteger(id) || id < 1) {
      setError("This user could not be found.");
      return;
    }
    adminApi
      .getUser(id)
      .then(setDetail)
      .catch(() => setError("This user could not be found."));
  };

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(load, [userId]);

  if (error) return <div className="page-error">{error}</div>;
  if (!detail) return <div className="page-loading">Loading...</div>;

  const { user, tasks } = detail;
  const isSelf = user.id === me?.id;
  const isRoot = user.id === ROOT_ADMIN_ID;
  const visible = showCompleted ? tasks : tasks.filter((t) => !t.completed);
  const completionRate = user.total_tasks ? Math.round((100 * user.completed_tasks) / user.total_tasks) : 0;

  return (
    <div className="page page-wide">
      <Link to="/admin/users" className="back-link">
        ← All users
      </Link>

      <div className="page-header">
        <div>
          <h1>
            {user.name} {isSelf && <span className="you-tag">you</span>}
          </h1>
          <p className="page-subtitle">
            {user.email} · <span className={`role-pill ${user.is_admin ? "role-admin" : ""}`}>{isRoot ? "Main admin" : user.is_admin ? "Admin" : "Student"}</span>{" "}
            <span className={`status-pill ${user.is_active ? "status-open" : "status-inactive"}`}>
              {user.is_active ? "Active" : "Deactivated"}
            </span>
          </p>
          <p className="page-subtitle">
            User ID <span className="id-chip">{user.id}</span> · joined {formatDate(user.created_at)}
            {user.last_activity && <> · last activity {relativeTime(user.last_activity)}</>}
          </p>
        </div>
        <div className="header-actions">
          <button type="button" className="btn btn-secondary" onClick={() => setEditingUser(true)}>
            Edit user
          </button>
          <button
            type="button"
            className="btn btn-danger"
            onClick={() => setDeletingUser(true)}
            disabled={isSelf || isRoot}
            title={
              isRoot
                ? "The main administrator (user ID 1) can't be deleted"
                : isSelf
                  ? "You can't delete your own account"
                  : undefined
            }
          >
            Delete user
          </button>
        </div>
      </div>

      <div className="stat-grid stat-grid-5">
        <StatTile label="Open tasks" value={user.open_tasks} />
        <StatTile label="Completed" value={user.completed_tasks} hint={`${completionRate}% completion`} />
        <StatTile label="Overdue" value={user.overdue_tasks} tone={user.overdue_tasks ? "danger" : "default"} />
        <StatTile label="Critical open" value={user.critical_open} tone={user.critical_open ? "warning" : "default"} />
        <StatTile label="Total tasks" value={user.total_tasks} />
      </div>

      <div className="section-header">
        <h2>Tasks</h2>
        <label className="checkbox-label">
          <input type="checkbox" checked={showCompleted} onChange={(e) => setShowCompleted(e.target.checked)} />
          Show completed ({user.completed_tasks})
        </label>
      </div>

      <AdminTaskTable
        tasks={visible}
        showOwner={false}
        onEdit={setEditingTask}
        onDelete={setDeletingTask}
        onToggleComplete={async (t) => {
          await adminApi.updateTask(t.id, { completed: !t.completed });
          load();
        }}
      />

      {editingUser && me && (
        <UserFormModal
          user={user}
          currentUserId={me.id}
          onClose={() => setEditingUser(false)}
          onSaved={load}
        />
      )}

      {deletingUser && (
        <ConfirmDialog
          title="Delete user?"
          message={
            <p>
              <strong>{user.name}</strong> and all <strong>{user.total_tasks}</strong> of their tasks will be permanently
              deleted.
            </p>
          }
          confirmLabel="Delete user"
          onConfirm={async () => {
            await adminApi.deleteUser(user.id);
            navigate("/admin/users");
          }}
          onClose={() => setDeletingUser(false)}
        />
      )}

      {editingTask && <TaskEditModal task={editingTask} onClose={() => setEditingTask(null)} onSaved={load} />}

      {deletingTask && (
        <ConfirmDialog
          title="Delete task?"
          message={
            <p>
              <strong>{deletingTask.title}</strong> will be permanently deleted.
            </p>
          }
          confirmLabel="Delete task"
          onConfirm={async () => {
            await adminApi.deleteTask(deletingTask.id);
            load();
          }}
          onClose={() => setDeletingTask(null)}
        />
      )}
    </div>
  );
}
