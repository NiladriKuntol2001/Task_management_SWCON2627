import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { adminApi, type AdminTaskQuery } from "../../api/client";
import type { AdminTask, AdminTaskPage, PriorityLevel } from "../../types";
import AdminTaskTable from "../../components/admin/AdminTaskTable";
import TaskEditModal from "../../components/admin/TaskEditModal";
import ConfirmDialog from "../../components/ConfirmDialog";

const PAGE_SIZE = 25;

export default function AdminTasksPage() {
  const [params, setParams] = useSearchParams();
  const subject = params.get("subject") ?? "";
  const completedParam = params.get("completed"); // "true" | "false" | null
  const priority = (params.get("priority_level") as PriorityLevel | null) ?? "";
  const overdueOnly = params.get("overdue_only") === "true";
  const sortBy = (params.get("sort_by") as AdminTaskQuery["sort_by"]) || "priority";
  const ownerId = params.get("owner_id") ?? "";
  const page = Math.max(0, Number(params.get("page") ?? 0));
  const search = params.get("search") ?? "";

  const [searchInput, setSearchInput] = useState(search);
  const [data, setData] = useState<AdminTaskPage | null>(null);
  const [subjects, setSubjects] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<AdminTask | null>(null);
  const [deleting, setDeleting] = useState<AdminTask | null>(null);

  const setParam = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    if (key !== "page") next.delete("page"); // any filter change returns to page 1
    setParams(next, { replace: true });
  };

  useEffect(() => {
    const t = setTimeout(() => {
      if (searchInput.trim() !== search) setParam("search", searchInput.trim());
    }, 300);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchInput]);

  useEffect(() => {
    adminApi.listSubjects().then(setSubjects).catch(() => setSubjects([]));
  }, []);

  const load = () => {
    setError(null);
    adminApi
      .listTasks({
        search: search || undefined,
        subject: subject || undefined,
        completed: completedParam === null ? undefined : completedParam === "true",
        priority_level: priority || undefined,
        overdue_only: overdueOnly || undefined,
        owner_id: ownerId || undefined,
        sort_by: sortBy,
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
      })
      .then(setData)
      .catch(() => setError("Could not load tasks."));
  };

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(load, [search, subject, completedParam, priority, overdueOnly, sortBy, ownerId, page]);

  const toggleComplete = async (t: AdminTask) => {
    await adminApi.updateTask(t.id, { completed: !t.completed });
    load();
  };

  const pageCount = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;
  const hasFilters = Boolean(search || subject || completedParam || priority || overdueOnly || ownerId);

  return (
    <div className="page page-wide">
      <div className="page-header">
        <div>
          <h1>All tasks</h1>
          <p className="page-subtitle">
            {data ? `${data.total} task${data.total === 1 ? "" : "s"}` : "Loading"} across all students
            {ownerId && data?.items[0] && <> · filtered to {data.items[0].owner_name}</>}
          </p>
        </div>
        {hasFilters && (
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => {
              setSearchInput("");
              setParams(new URLSearchParams(), { replace: true });
            }}
          >
            Clear filters
          </button>
        )}
      </div>

      <div className="filter-bar">
        <label className="grow">
          Search
          <input
            type="search"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Title, subject, student name or email"
          />
        </label>
        <label>
          Subject
          <select value={subject} onChange={(e) => setParam("subject", e.target.value)}>
            <option value="">All subjects</option>
            {subjects.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
        <label>
          Status
          <select value={completedParam ?? ""} onChange={(e) => setParam("completed", e.target.value)}>
            <option value="">Any status</option>
            <option value="false">Open</option>
            <option value="true">Completed</option>
          </select>
        </label>
        <label>
          Priority
          <select value={priority} onChange={(e) => setParam("priority_level", e.target.value)}>
            <option value="">Any priority</option>
            <option value="Critical">Critical</option>
            <option value="High">High</option>
            <option value="Medium">Medium</option>
            <option value="Low">Low</option>
          </select>
        </label>
        <label>
          Sort by
          <select value={sortBy} onChange={(e) => setParam("sort_by", e.target.value)}>
            <option value="priority">Priority</option>
            <option value="deadline">Deadline</option>
            <option value="created">Newest</option>
          </select>
        </label>
        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={overdueOnly}
            onChange={(e) => setParam("overdue_only", e.target.checked ? "true" : "")}
          />
          Overdue only
        </label>
      </div>

      {error && <div className="page-error">{error}</div>}
      {!data && !error && <div className="page-loading">Loading...</div>}

      {data && (
        <>
          <AdminTaskTable
            tasks={data.items}
            onEdit={setEditing}
            onDelete={setDeleting}
            onToggleComplete={toggleComplete}
          />
          {pageCount > 1 && (
            <div className="pagination">
              <button
                type="button"
                className="btn btn-sm btn-secondary"
                disabled={page === 0}
                onClick={() => setParam("page", String(page - 1))}
              >
                Previous
              </button>
              <span>
                Page {page + 1} of {pageCount}
              </span>
              <button
                type="button"
                className="btn btn-sm btn-secondary"
                disabled={page + 1 >= pageCount}
                onClick={() => setParam("page", String(page + 1))}
              >
                Next
              </button>
            </div>
          )}
        </>
      )}

      {editing && <TaskEditModal task={editing} onClose={() => setEditing(null)} onSaved={load} />}

      {deleting && (
        <ConfirmDialog
          title="Delete task?"
          message={
            <p>
              <strong>{deleting.title}</strong> ({deleting.subject}) belonging to <strong>{deleting.owner_name}</strong> will be
              permanently deleted.
            </p>
          }
          confirmLabel="Delete task"
          onConfirm={async () => {
            await adminApi.deleteTask(deleting.id);
            load();
          }}
          onClose={() => setDeleting(null)}
        />
      )}
    </div>
  );
}
