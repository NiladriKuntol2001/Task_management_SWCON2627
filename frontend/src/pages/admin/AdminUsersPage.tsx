import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { adminApi, type AdminUserQuery } from "../../api/client";
import type { AdminUser } from "../../types";
import { useAuth } from "../../context/AuthContext";
import UserFormModal from "../../components/admin/UserFormModal";
import ConfirmDialog from "../../components/ConfirmDialog";
import { formatDate, relativeTime, ROOT_ADMIN_ID } from "../../utils/format";

type Role = NonNullable<AdminUserQuery["role"]>;
type Status = NonNullable<AdminUserQuery["status"]>;
type Sort = NonNullable<AdminUserQuery["sort_by"]>;

export default function AdminUsersPage() {
  const { user: me } = useAuth();
  const [params, setParams] = useSearchParams();
  const role = (params.get("role") as Role) || "all";
  const status = (params.get("status") as Status) || "all";
  const sortBy = (params.get("sort_by") as Sort) || "created";

  const [searchInput, setSearchInput] = useState(params.get("search") ?? "");
  const [users, setUsers] = useState<AdminUser[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<AdminUser | null | undefined>(undefined); // undefined = closed, null = create
  const [deleting, setDeleting] = useState<AdminUser | null>(null);
  const search = params.get("search") ?? "";

  const setParam = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value && value !== "all") next.set(key, value);
    else next.delete(key);
    setParams(next, { replace: true });
  };

  // Debounce the search box into the URL so typing doesn't fire a request per key.
  useEffect(() => {
    const t = setTimeout(() => {
      if (searchInput !== search) setParam("search", searchInput.trim());
    }, 300);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchInput]);

  const load = () => {
    setError(null);
    adminApi
      .listUsers({ search: search || undefined, role, status, sort_by: sortBy })
      .then(setUsers)
      .catch(() => setError("Could not load users."));
  };

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(load, [search, role, status, sortBy]);

  const totals = users
    ? {
        students: users.filter((u) => !u.is_admin).length,
        overdue: users.filter((u) => u.overdue_tasks > 0).length,
      }
    : null;

  return (
    <div className="page page-wide">
      <div className="page-header">
        <div>
          <h1>Users</h1>
          {totals && (
            <p className="page-subtitle">
              {users?.length} shown · {totals.students} students · {totals.overdue} with overdue work
            </p>
          )}
        </div>
        <button type="button" className="btn btn-primary" onClick={() => setEditing(null)}>
          Add user
        </button>
      </div>

      <div className="filter-bar">
        <label className="grow">
          Search
          <input
            type="search"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Name, email, or user ID (e.g. 3)"
          />
        </label>
        <label>
          Role
          <select value={role} onChange={(e) => setParam("role", e.target.value)}>
            <option value="all">All roles</option>
            <option value="student">Students</option>
            <option value="admin">Admins</option>
          </select>
        </label>
        <label>
          Status
          <select value={status} onChange={(e) => setParam("status", e.target.value)}>
            <option value="all">Any status</option>
            <option value="active">Active</option>
            <option value="inactive">Deactivated</option>
          </select>
        </label>
        <label>
          Sort by
          <select value={sortBy} onChange={(e) => setParam("sort_by", e.target.value)}>
            <option value="created">Newest</option>
            <option value="name">Name</option>
            <option value="open">Most open tasks</option>
            <option value="overdue">Most overdue</option>
          </select>
        </label>
      </div>

      {error && <div className="page-error">{error}</div>}
      {!users && !error && <div className="page-loading">Loading...</div>}

      {users && users.length === 0 && <div className="empty-state">No users match these filters.</div>}

      {users && users.length > 0 && (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>User</th>
                <th className="num">User ID</th>
                <th>Role</th>
                <th>Status</th>
                <th className="num">Open</th>
                <th className="num">Done</th>
                <th className="num">Overdue</th>
                <th>Last activity</th>
                <th>Joined</th>
                <th aria-label="Actions" />
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className={u.is_active ? "" : "row-muted"}>
                  <td>
                    <Link to={`/admin/users/${u.id}`} className="cell-link cell-title">
                      {u.name}
                    </Link>
                    {u.id === me?.id && <span className="you-tag">you</span>}
                    <div className="cell-sub">{u.email}</div>
                  </td>
                  <td className="num">
                    <span className="id-chip">{u.id}</span>
                  </td>
                  <td>
                    <span className={`role-pill ${u.is_admin ? "role-admin" : ""}`}>
                      {u.id === ROOT_ADMIN_ID ? "Main admin" : u.is_admin ? "Admin" : "Student"}
                    </span>
                  </td>
                  <td>
                    <span className={`status-pill ${u.is_active ? "status-open" : "status-inactive"}`}>
                      {u.is_active ? "Active" : "Deactivated"}
                    </span>
                  </td>
                  <td className="num">{u.open_tasks}</td>
                  <td className="num">{u.completed_tasks}</td>
                  <td className={`num ${u.overdue_tasks ? "text-danger strong" : ""}`}>{u.overdue_tasks}</td>
                  <td className="cell-sub">{u.last_activity ? relativeTime(u.last_activity) : "—"}</td>
                  <td className="cell-sub">{formatDate(u.created_at)}</td>
                  <td className="row-actions">
                    <Link to={`/admin/users/${u.id}`} className="btn btn-sm btn-secondary">
                      View
                    </Link>
                    <button type="button" className="btn btn-sm btn-secondary" onClick={() => setEditing(u)}>
                      Edit
                    </button>
                    <button
                      type="button"
                      className="btn btn-sm btn-danger"
                      onClick={() => setDeleting(u)}
                      disabled={u.id === me?.id || u.id === ROOT_ADMIN_ID}
                      title={
                        u.id === ROOT_ADMIN_ID
                          ? "The main administrator (user ID 1) can't be deleted"
                          : u.id === me?.id
                            ? "You can't delete your own account"
                            : undefined
                      }
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {editing !== undefined && me && (
        <UserFormModal
          user={editing}
          currentUserId={me.id}
          onClose={() => setEditing(undefined)}
          onSaved={load}
        />
      )}

      {deleting && (
        <ConfirmDialog
          title="Delete user?"
          message={
            <>
              <p>
                <strong>{deleting.name}</strong> ({deleting.email}) and all{" "}
                <strong>{deleting.total_tasks}</strong> of their tasks will be permanently deleted.
              </p>
              <p className="cell-sub">To keep their data but block access, edit the user and uncheck “Account active” instead.</p>
            </>
          }
          confirmLabel="Delete user"
          onConfirm={async () => {
            await adminApi.deleteUser(deleting.id);
            load();
          }}
          onClose={() => setDeleting(null)}
        />
      )}
    </div>
  );
}
