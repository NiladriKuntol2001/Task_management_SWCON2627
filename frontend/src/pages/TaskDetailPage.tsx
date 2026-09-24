import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { Task } from "../types";
import PriorityBadge from "../components/PriorityBadge";

export default function TaskDetailPage() {
  const { taskId } = useParams();
  const navigate = useNavigate();
  const [task, setTask] = useState<Task | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    if (!taskId) return;
    api
      .getTask(taskId)
      .then(setTask)
      .catch(() => setError("This task could not be found."));
  };

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(load, [taskId]);

  const handleComplete = async () => {
    if (!taskId) return;
    await api.completeTask(taskId);
    load();
  };

  const handleDelete = async () => {
    if (!taskId || !window.confirm("Delete this task? This cannot be undone.")) return;
    await api.deleteTask(taskId);
    navigate("/tasks");
  };

  if (error) return <div className="page-error">{error}</div>;
  if (!task) return <div className="page-loading">Loading...</div>;

  return (
    <div className="page page-narrow">
      <div className="task-detail-header">
        <h1>{task.title}</h1>
        <PriorityBadge level={task.priority_level} score={task.priority_score} />
      </div>

      <dl className="detail-list">
        <dt>Subject</dt>
        <dd>{task.subject}</dd>

        <dt>Deadline</dt>
        <dd>
          {new Date(task.deadline).toLocaleString()}
          {task.is_overdue && <span className="text-danger"> &middot; Overdue</span>}
        </dd>

        <dt>Difficulty</dt>
        <dd>{task.difficulty}</dd>

        <dt>Estimated time</dt>
        <dd>{task.estimated_hours} hours</dd>

        <dt>Status</dt>
        <dd>{task.completed ? "Completed" : "Incomplete"}</dd>
      </dl>

      <div className="form-actions">
        {!task.completed && (
          <button className="btn btn-primary" onClick={handleComplete}>
            Mark complete
          </button>
        )}
        <Link className="btn btn-secondary" to={`/tasks/${task.id}/edit`}>
          Edit
        </Link>
        <button className="btn btn-danger" onClick={handleDelete}>
          Delete
        </button>
        <Link className="btn btn-secondary" to="/tasks">
          Back to tasks
        </Link>
      </div>
    </div>
  );
}
