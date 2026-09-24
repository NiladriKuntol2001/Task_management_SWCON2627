import { useEffect, useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { Difficulty } from "../types";

const DIFFICULTIES: Difficulty[] = ["Easy", "Medium", "Hard", "Very Hard"];

function toLocalInputValue(iso: string): string {
  // datetime-local inputs need "YYYY-MM-DDTHH:mm" in local time, no timezone.
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export default function TaskFormPage() {
  const { taskId } = useParams();
  const isEditing = Boolean(taskId);
  const navigate = useNavigate();

  const [title, setTitle] = useState("");
  const [subject, setSubject] = useState("");
  const [deadline, setDeadline] = useState("");
  const [difficulty, setDifficulty] = useState<Difficulty>("Medium");
  const [estimatedHours, setEstimatedHours] = useState("1");
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(isEditing);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!taskId) return;
    api
      .getTask(taskId)
      .then((task) => {
        setTitle(task.title);
        setSubject(task.subject);
        setDeadline(toLocalInputValue(task.deadline));
        setDifficulty(task.difficulty);
        setEstimatedHours(String(task.estimated_hours));
      })
      .catch(() => setError("Could not load this task."))
      .finally(() => setLoading(false));
  }, [taskId]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setFieldErrors({});
    setSubmitting(true);

    const payload = {
      title,
      subject,
      deadline: new Date(deadline).toISOString(),
      difficulty,
      estimated_hours: Number(estimatedHours),
    };

    try {
      if (isEditing && taskId) {
        await api.updateTask(taskId, payload);
      } else {
        await api.createTask(payload);
      }
      navigate("/tasks");
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
        const fe: Record<string, string> = {};
        for (const fieldError of err.fieldErrors) {
          fe[fieldError.field] = fieldError.message;
        }
        setFieldErrors(fe);
      } else {
        setError("Could not save this task. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <div className="page-loading">Loading...</div>;

  return (
    <div className="page page-narrow">
      <h1>{isEditing ? "Edit task" : "New task"}</h1>

      <form className="task-form" onSubmit={handleSubmit}>
        {error && <div className="form-error" role="alert">{error}</div>}

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

        <label>
          Deadline
          <input
            type="datetime-local"
            value={deadline}
            onChange={(e) => setDeadline(e.target.value)}
            required
          />
          {fieldErrors.deadline && <span className="field-error">{fieldErrors.deadline}</span>}
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

        <label>
          Estimated hours
          <input
            type="number"
            min="0.25"
            step="0.25"
            value={estimatedHours}
            onChange={(e) => setEstimatedHours(e.target.value)}
            required
          />
          {fieldErrors.estimated_hours && <span className="field-error">{fieldErrors.estimated_hours}</span>}
        </label>

        <div className="form-actions">
          <button type="submit" className="btn btn-primary" disabled={submitting}>
            {submitting ? "Saving..." : isEditing ? "Save changes" : "Create task"}
          </button>
          <button type="button" className="btn btn-secondary" onClick={() => navigate(-1)}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
