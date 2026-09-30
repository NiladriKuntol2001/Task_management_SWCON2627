import { Link } from "react-router-dom";
import type { AdminTask } from "../../types";
import { formatDateTime, relativeTime } from "../../utils/format";
import PriorityBadge from "../PriorityBadge";

export default function AdminTaskTable({
  tasks,
  showOwner = true,
  onEdit,
  onDelete,
  onToggleComplete,
}: {
  tasks: AdminTask[];
  showOwner?: boolean;
  onEdit: (task: AdminTask) => void;
  onDelete: (task: AdminTask) => void;
  onToggleComplete: (task: AdminTask) => void;
}) {
  if (tasks.length === 0) {
    return <div className="empty-state">No tasks match these filters.</div>;
  }

  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            <th>Task</th>
            {showOwner && <th>Student</th>}
            <th>Deadline</th>
            <th>Difficulty</th>
            <th className="num">Hours</th>
            <th>Priority</th>
            <th>Status</th>
            <th aria-label="Actions" />
          </tr>
        </thead>
        <tbody>
          {tasks.map((t) => (
            <tr key={t.id} className={t.completed ? "row-muted" : ""}>
              <td>
                <div className="cell-title">{t.title}</div>
                <div className="cell-sub">{t.subject}</div>
              </td>
              {showOwner && (
                <td>
                  <Link to={`/admin/users/${t.owner_id}`} className="cell-link">
                    {t.owner_name}
                  </Link>
                  <div className="cell-sub">{t.owner_email}</div>
                </td>
              )}
              <td>
                <div>{formatDateTime(t.deadline)}</div>
                <div className={`cell-sub ${t.is_overdue ? "text-danger" : ""}`}>
                  {t.completed ? "—" : t.is_overdue ? `Overdue · ${relativeTime(t.deadline)}` : relativeTime(t.deadline)}
                </div>
              </td>
              <td>{t.difficulty}</td>
              <td className="num">{t.estimated_hours}</td>
              <td>
                <PriorityBadge level={t.priority_level} score={t.priority_score} />
              </td>
              <td>
                <span className={`status-pill ${t.completed ? "status-done" : t.is_overdue ? "status-overdue" : "status-open"}`}>
                  {t.completed ? "Completed" : t.is_overdue ? "Overdue" : "Open"}
                </span>
              </td>
              <td className="row-actions">
                <button type="button" className="btn btn-sm btn-secondary" onClick={() => onToggleComplete(t)}>
                  {t.completed ? "Reopen" : "Complete"}
                </button>
                <button type="button" className="btn btn-sm btn-secondary" onClick={() => onEdit(t)}>
                  Edit
                </button>
                <button type="button" className="btn btn-sm btn-danger" onClick={() => onDelete(t)}>
                  Delete
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
