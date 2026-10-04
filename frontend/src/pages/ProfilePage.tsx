import { useState, type FormEvent } from "react";
import { api, ApiError } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { formatDate, ROOT_ADMIN_ID } from "../utils/format";

type Feedback = { kind: "success" | "error"; text: string } | null;

function fieldErrorsOf(err: unknown): Record<string, string> {
  const out: Record<string, string> = {};
  if (err instanceof ApiError) {
    for (const f of err.fieldErrors) out[f.field] = f.message;
  }
  return out;
}

function ChangeEmailForm({ locked }: { locked: boolean }) {
  const { user, updateUser } = useAuth();
  const [newEmail, setNewEmail] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [feedback, setFeedback] = useState<Feedback>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setFeedback(null);
    setFieldErrors({});

    if (user && newEmail.trim().toLowerCase() === user.email.toLowerCase()) {
      setFeedback({ kind: "error", text: "That is already your email address." });
      return;
    }

    setSaving(true);
    try {
      const updated = await api.changeEmail(newEmail.trim(), currentPassword);
      updateUser(updated);
      setNewEmail("");
      setCurrentPassword("");
      setFeedback({ kind: "success", text: `Email changed. Use ${updated.email} to log in from now on.` });
    } catch (err) {
      setFeedback({ kind: "error", text: err instanceof ApiError ? err.message : "Could not change your email." });
      setFieldErrors(fieldErrorsOf(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="chart-card profile-card">
      <header className="chart-card-header">
        <div>
          <h3>Change email</h3>
          <p className="chart-card-subtitle">This is the email you log in with.</p>
        </div>
      </header>

      {locked ? (
        <p className="field-hint">The main administrator's email (user ID 1) is fixed and can't be changed.</p>
      ) : (
        <form className="task-form" onSubmit={handleSubmit}>
          {feedback && (
            <div className={feedback.kind === "success" ? "form-success" : "form-error"} role="status">
              {feedback.text}
            </div>
          )}
          <label>
            New email
            <input
              type="email"
              value={newEmail}
              onChange={(e) => setNewEmail(e.target.value)}
              required
              autoComplete="email"
            />
            {fieldErrors.new_email && <span className="field-error">{fieldErrors.new_email}</span>}
          </label>
          <label>
            Current password
            <input
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              required
              autoComplete="current-password"
            />
            <span className="field-hint">Needed to confirm it's you.</span>
          </label>
          <div className="form-actions">
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? "Saving..." : "Change email"}
            </button>
          </div>
        </form>
      )}
    </section>
  );
}

function ChangePasswordForm() {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [feedback, setFeedback] = useState<Feedback>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);

  // Instant checks while typing; the server repeats every one of them.
  const sameAsCurrent = newPassword.length > 0 && newPassword === currentPassword;
  const tooShort = newPassword.length > 0 && newPassword.length < 8;
  const mismatch = confirmPassword.length > 0 && confirmPassword !== newPassword;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setFeedback(null);
    setFieldErrors({});
    if (sameAsCurrent || tooShort || mismatch) return;

    setSaving(true);
    try {
      await api.changePassword(currentPassword, newPassword, confirmPassword);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setFeedback({ kind: "success", text: "Password changed. Use your new password next time you log in." });
    } catch (err) {
      setFeedback({ kind: "error", text: err instanceof ApiError ? err.message : "Could not change your password." });
      setFieldErrors(fieldErrorsOf(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="chart-card profile-card">
      <header className="chart-card-header">
        <div>
          <h3>Change password</h3>
          <p className="chart-card-subtitle">Your new password must be different from your current one.</p>
        </div>
      </header>
      <form className="task-form" onSubmit={handleSubmit}>
        {feedback && (
          <div className={feedback.kind === "success" ? "form-success" : "form-error"} role="status">
            {feedback.text}
          </div>
        )}
        <label>
          Current password
          <input
            type="password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            required
            autoComplete="current-password"
          />
        </label>
        <label>
          New password
          <input
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            required
            minLength={8}
            autoComplete="new-password"
            aria-invalid={sameAsCurrent || tooShort}
          />
          {sameAsCurrent ? (
            <span className="field-error">Your new password must be different from your current password.</span>
          ) : tooShort ? (
            <span className="field-error">At least 8 characters.</span>
          ) : (
            <span className="field-hint">At least 8 characters.</span>
          )}
          {fieldErrors.new_password && <span className="field-error">{fieldErrors.new_password}</span>}
        </label>
        <label>
          Confirm new password
          <input
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
            autoComplete="new-password"
            aria-invalid={mismatch}
          />
          {mismatch && <span className="field-error">Passwords don't match.</span>}
          {fieldErrors.confirm_new_password && <span className="field-error">{fieldErrors.confirm_new_password}</span>}
        </label>
        <div className="form-actions">
          <button type="submit" className="btn btn-primary" disabled={saving || sameAsCurrent || tooShort || mismatch}>
            {saving ? "Saving..." : "Change password"}
          </button>
        </div>
      </form>
    </section>
  );
}

export default function ProfilePage() {
  const { user } = useAuth();
  if (!user) return null;
  const isRoot = user.id === ROOT_ADMIN_ID;

  return (
    <div className="page page-narrow">
      <h1>My profile</h1>

      <section className="chart-card profile-card">
        <dl className="profile-details">
          <div>
            <dt>User ID</dt>
            <dd className="user-id">{user.id}</dd>
          </div>
          <div>
            <dt>Name</dt>
            <dd>{user.name}</dd>
          </div>
          <div>
            <dt>Email</dt>
            <dd>{user.email}</dd>
          </div>
          <div>
            <dt>Role</dt>
            <dd>
              <span className={`role-pill ${user.is_admin ? "role-admin" : ""}`}>
                {isRoot ? "Main administrator" : user.is_admin ? "Admin" : "Student"}
              </span>
            </dd>
          </div>
          <div>
            <dt>Member since</dt>
            <dd>{formatDate(user.created_at)}</dd>
          </div>
        </dl>
      </section>

      <ChangeEmailForm locked={isRoot} />
      <ChangePasswordForm />
    </div>
  );
}
