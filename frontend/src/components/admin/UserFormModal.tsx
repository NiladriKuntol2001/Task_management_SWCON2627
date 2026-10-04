import { useState, type FormEvent } from "react";
import { adminApi, ApiError } from "../../api/client";
import type { AdminUser, AdminUserPatch } from "../../types";
import Modal from "../Modal";
import { useAuth } from "../../context/AuthContext";
import { ROOT_ADMIN_ID } from "../../utils/format";

/** Create a new account, or edit an existing one (name, email, role, status,
 *  password reset). Self-lockout options are disabled for the signed-in admin. */
export default function UserFormModal({
  user,
  currentUserId,
  onClose,
  onSaved,
}: {
  user: AdminUser | null; // null = create
  currentUserId: number;
  onClose: () => void;
  onSaved: (user: AdminUser) => void;
}) {
  const { updateUser } = useAuth();
  const isEdit = user !== null;
  const isSelf = user?.id === currentUserId;
  // The main administrator (user ID 1): fixed email, always an active admin,
  // password changed only from their own profile page. The API enforces this too.
  const isRoot = user?.id === ROOT_ADMIN_ID;

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
        if (saved.id === currentUserId) updateUser(saved); // keep the navbar in sync
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
            <span className="id-chip">{user?.id}</span>
          </div>
        )}

        <label>
          Name
          <input type="text" value={name} onChange={(e) => setName(e.target.value)} required />
          {fieldErrors.name && <span className="field-error">{fieldErrors.name}</span>}
        </label>

        <label>
          Email
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required disabled={isRoot} />
          {isRoot && <span className="field-hint">The main administrator's email is fixed.</span>}
          {fieldErrors.email && <span className="field-error">{fieldErrors.email}</span>}
        </label>

        {isRoot ? (
          <p className="field-hint">The main administrator changes their password from their own profile page.</p>
        ) : (
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
          {isEdit && <span className="field-hint">Must be different from the user's current password.</span>}
          {fieldErrors.password && <span className="field-error">{fieldErrors.password}</span>}
        </label>
        )}

        <div className="toggle-row">
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={isAdmin}
              onChange={(e) => setIsAdmin(e.target.checked)}
              disabled={isSelf || isRoot}
            />
            Administrator
          </label>
          {isEdit && (
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={isActive}
                onChange={(e) => setIsActive(e.target.checked)}
                disabled={isSelf || isRoot}
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
