import { useState, type ReactNode } from "react";
import Modal from "./Modal";

/** In-app confirmation for destructive actions (instead of window.confirm),
 *  so the admin sees exactly what will be deleted. */
export default function ConfirmDialog({
  title,
  message,
  confirmLabel = "Delete",
  onConfirm,
  onClose,
}: {
  title: string;
  message: ReactNode;
  confirmLabel?: string;
  onConfirm: () => Promise<void>;
  onClose: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleConfirm = async () => {
    setBusy(true);
    setError(null);
    try {
      await onConfirm();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
      setBusy(false);
    }
  };

  return (
    <Modal
      title={title}
      onClose={onClose}
      footer={
        <>
          <button type="button" className="btn btn-secondary" onClick={onClose} disabled={busy}>
            Cancel
          </button>
          <button type="button" className="btn btn-danger-solid" onClick={handleConfirm} disabled={busy}>
            {busy ? "Working..." : confirmLabel}
          </button>
        </>
      }
    >
      {error && <div className="form-error" role="alert">{error}</div>}
      <div className="confirm-message">{message}</div>
    </Modal>
  );
}
