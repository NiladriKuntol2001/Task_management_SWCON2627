import { useState, type FormEvent } from "react";
import { adminApi, ApiError } from "../../api/client";
import type { AdminTask, Difficulty } from "../../types";
import Modal from "../Modal";

const DIFFICULTIES: Difficulty[] = ["Easy", "Medium", "Hard", "Very Hard"];

function toLocalInputValue(iso: string): string {
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/** Admin edit of any student's task. Priority is recalculated server-side. */
export default function TaskEditModal({
  task,
  onClose,
  onSaved,
}: {
  task: AdminTask;
  onClose: () => void;
  onSaved: (task: AdminTask) => void;
}) {
  const [title, setTitle] = useState(task.title);
  const [subject, setSubject] = useState(task.subject);
  const [deadline, setDeadline] = useState(toLocalInputValue(task.deadline));
  const [difficulty, setDifficulty] = useState<Difficulty>(task.difficulty);
  const [hours, setHours] = useState(String(task.estimated_hours));
  const [completed, setCompleted] = useState(task.completed);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setFieldErrors({});
    try {
      const saved = await adminApi.updateTask(task.id, {
        title,
        subject,
        deadline: new Date(deadline).toISOString(),
        difficulty,
        estimated_hours: Number(hours),
        completed,
      });
      onSaved(saved);
      onClose();
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
        const fe: Record<string, string> = {};
        for (const f of err.fieldErrors) fe[f.field] = f.message;
        setFieldErrors(fe);
      } else {
        setError("Could not save this task.");
      }
      setSaving(false);
    }
  };

  return (
    <Modal
      title="Edit task"
      onClose={onClose}
      footer={
        <>
          <button type="button" className="btn btn-secondary" onClick={onClose} disabled={saving}>
            Cancel
          </button>
          <button type="submit" form="task-edit-form" className="btn btn-primary" disabled={saving}>
            {saving ? "Saving..." : "Save changes"}
          </button>
        </>
      }
    >
      <form id="task-edit-form" className="task-form" onSubmit={handleSubmit}>
        {error && <div className="form-error" role="alert">{error}</div>}
        <div className="readonly-field">
          <span>Student</span>
          <span>
            {task.owner_name} · {task.owner_email}
          </span>
        </div>

        <label>
          Title
          <input type="text" value={title} onChange={(e) => setTitle(e.target.value)} required />
          {fieldErrors.title && <span className="field-error">{fieldErrors.title}</span>}
        </label>
        <label>
          Subject
          <input type="text" value={subject} onChange={(e) => setSubject(e.target.value)} required />
          {fieldErrors.subject && <span className="field-error">{fieldErrors.subject}</span>}
        </label>
        <div className="form-grid-2">
          <label>
            Deadline
            <input type="datetime-local" value={deadline} onChange={(e) => setDeadline(e.target.value)} required />
          </label>
          <label>
            Difficulty
            <select value={difficulty} onChange={(e) => setDifficulty(e.target.value as Difficulty)}>
              {DIFFICULTIES.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          </label>
        </div>
        <label>
          Estimated hours
          <input type="number" min="0.25" step="0.25" value={hours} onChange={(e) => setHours(e.target.value)} required />
          {fieldErrors.estimated_hours && <span className="field-error">{fieldErrors.estimated_hours}</span>}
        </label>
        <label className="checkbox-label">
          <input type="checkbox" checked={completed} onChange={(e) => setCompleted(e.target.checked)} />
          Completed
        </label>
      </form>
    </Modal>
  );
}
