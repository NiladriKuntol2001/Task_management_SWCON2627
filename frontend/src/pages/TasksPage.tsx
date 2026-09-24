import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import type { Task } from "../types";
import TaskCard from "../components/TaskCard";

type CompletionFilter = "all" | "incomplete" | "completed";

export default function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [subject, setSubject] = useState("");
  const [completion, setCompletion] = useState<CompletionFilter>("incomplete");
  const [overdueOnly, setOverdueOnly] = useState(false);
  const [sortBy, setSortBy] = useState<"priority" | "deadline">("priority");

  const load = () => {
    api
      .listTasks({
        subject: subject || undefined,
        completed: completion === "all" ? undefined : completion === "completed",
        overdueOnly,
        sortBy,
      })
      .then(setTasks)
      .catch(() => setError("Could not load your tasks. Please try again."));
  };

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(load, [subject, completion, overdueOnly, sortBy]);

  const subjects = useMemo(
    () => Array.from(new Set(tasks.map((t) => t.subject))).sort(),
    [tasks]
  );

  const handleComplete = async (id: string) => {
    await api.completeTask(id);
    load();
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm("Delete this task? This cannot be undone.")) return;
    await api.deleteTask(id);
    load();
  };

  return (
    <div className="page">
      <div className="page-header">
        <h1>Tasks</h1>
      </div>

      <div className="filter-bar">
        <label>
          Subject
          <select value={subject} onChange={(e) => setSubject(e.target.value)}>
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
          <select value={completion} onChange={(e) => setCompletion(e.target.value as CompletionFilter)}>
            <option value="incomplete">Incomplete</option>
            <option value="completed">Completed</option>
            <option value="all">All</option>
          </select>
        </label>

        <label>
          Sort by
          <select value={sortBy} onChange={(e) => setSortBy(e.target.value as "priority" | "deadline")}>
            <option value="priority">Priority</option>
            <option value="deadline">Deadline</option>
          </select>
        </label>

        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={overdueOnly}
            onChange={(e) => setOverdueOnly(e.target.checked)}
          />
          Overdue only
        </label>
      </div>

      {error && <div className="page-error">{error}</div>}

      {tasks.length === 0 ? (
        <div className="empty-state">
          <p>No tasks match these filters.</p>
        </div>
      ) : (
        <div className="task-list">
          {tasks.map((task) => (
            <TaskCard key={task.id} task={task} onComplete={handleComplete} onDelete={handleDelete} />
          ))}
        </div>
      )}
    </div>
  );
}
