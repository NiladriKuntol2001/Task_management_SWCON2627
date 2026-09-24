import { Link } from "react-router-dom";
import type { Task } from "../types";
import PriorityBadge from "./PriorityBadge";

function formatDeadline(deadline: string): string {
  return new Date(deadline).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export default function TaskCard({
  task,
  onComplete,
  onDelete,
}: {
  task: Task;
  onComplete?: (id: string) => void;
  onDelete?: (id: string) => void;
}) {
  return (
    <div className={`task-card ${task.completed ? "task-card-completed" : ""} ${task.is_overdue ? "task-card-overdue" : ""}`}>
      <div className="task-card-main">
        <Link to={`/tasks/${task.id}`} className="task-card-title">
          {task.title}
        </Link>
        <div className="task-card-meta">
          <span>{task.subject}</span>
          <span>&middot;</span>
          <span>{task.difficulty}</span>
          <span>&middot;</span>
          <span>{task.estimated_hours}h</span>
          <span>&middot;</span>
          <span>Due {formatDeadline(task.deadline)}</span>
          {task.is_overdue && <span className="text-danger">&middot; Overdue</span>}
        </div>
      </div>
      <div className="task-card-side">
        <PriorityBadge level={task.priority_level} score={task.priority_score} />
        <div className="task-card-actions">
          {!task.completed && onComplete && (
            <button className="btn btn-sm btn-primary" onClick={() => onComplete(task.id)}>
              Complete
            </button>
          )}
          <Link className="btn btn-sm btn-secondary" to={`/tasks/${task.id}/edit`}>
            Edit
          </Link>
          {onDelete && (
            <button className="btn btn-sm btn-danger" onClick={() => onDelete(task.id)}>
              Delete
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
