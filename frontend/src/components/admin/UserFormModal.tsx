import { useState, type FormEvent } from "react";
import { adminApi, ApiError } from "../../api/client";
import type { AdminUser, AdminUserPatch } from "../../types";
import Modal from "../Modal";

/** Create a new account, or edit an existing one (name, email, role, status,
 *  password reset). Self-lockout options are disabled for the signed-in admin. */
export default function UserFormModal({
  user,
  currentUserId,
  onClose,
  onSaved,
}: {
  user: AdminUser | null; // null = create
  currentUserId: string;
  onClose: () => void;
  onSaved: (user: AdminUser) => void;
}) {
  const isEdit = user !== null;
  const isSelf = user?.id === currentUserId;

  const [name, setName] = useState(user?.name ?? "");
  const [email, setEmail] = useState(user?.email ?? "");
  const [isAdmin, setIsAdmin] = useState(user?.is_admin ?? false);
  const [isActive, setIsActive] = useState(user?.is_active ?? true);
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setFieldErrors({});
    try {
      let saved: AdminUser;
      if (isEdit && user) {
        const patch: AdminUserPatch = {};
        if (name !== user.name) patch.name = name;
        if (email !== user.email) patch.email = email;
        if (isAdmin !== user.is_admin) patch.is_admin = isAdmin;
        if (isActive !== user.is_active) patch.is_active = isActive;
        if (password) patch.password = password;
        saved = await adminApi.updateUser(user.id, patch);
      } else {
        saved = await adminApi.createUser({ name, email, password, is_admin: isAdmin });
      }
      onSaved(saved);
      onClose();
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
        const fe: Record<string, string> = {};
        for (const f of err.fieldErrors) fe[f.field] = f.message;
        setFieldErrors(fe);
      } else {
        setError("Could not save this user.");
      }
      setSaving(false);
    }
  };

  return (
    <Modal
      title={isEdit ? `Edit ${user?.name}` : "Add user"}
      onClose={onClose}
      footer={
        <>
          <button type="button" className="btn btn-secondary" onClick={onClose} disabled={saving}>
            Cancel
          </button>
          <button type="submit" form="user-form" className="btn btn-primary" disabled={saving}>
            {saving ? "Saving..." : isEdit ? "Save changes" : "Create user"}
          </button>
        </>
      }
    >
      <form id="user-form" className="task-form" onSubmit={handleSubmit}>
        {error && <div className="form-error" role="alert">{error}</div>}

        {isEdit && (
          <div className="readonly-field">
            <span>User ID</span>
            <code>{user?.id}</code>
          </div>
        )}

        <label>
          Name
          <input type="text" value={name} onChange={(e) => setName(e.target.value)} required />
          {fieldErrors.name && <span className="field-error">{fieldErrors.name}</span>}
        </label>

        <label>
          Email
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          {fieldErrors.email && <span className="field-error">{fieldErrors.email}</span>}
        </label>

        <label>
          {isEdit ? "New password" : "Password"}
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            minLength={8}
            required={!isEdit}
            autoComplete="new-password"
            placeholder={isEdit ? "Leave blank to keep the current password" : ""}
          />
          <span className="field-hint">At least 8 characters.</span>
          {fieldErrors.password && <span className="field-error">{fieldErrors.password}</span>}
        </label>

        <div className="toggle-row">
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={isAdmin}
              onChange={(e) => setIsAdmin(e.target.checked)}
              disabled={isSelf}
            />
            Administrator
          </label>
          {isEdit && (
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={isActive}
                onChange={(e) => setIsActive(e.target.checked)}
                disabled={isSelf}
              />
              Account active
            </label>
          )}
        </div>
        {isSelf && <span className="field-hint">You can't remove your own admin access or deactivate yourself.</span>}
        {isEdit && !isActive && user?.is_active && (
          <span className="field-hint">Deactivated users can't log in. Their tasks are kept.</span>
        )}
      </form>
    </Modal>
  );
}
