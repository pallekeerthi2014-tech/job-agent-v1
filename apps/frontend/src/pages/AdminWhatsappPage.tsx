import { useState } from "react";

import type { AlertRecipient, AlertRecipientCreatePayload } from "../types";

type AdminWhatsappPageProps = {
  recipients: AlertRecipient[];
  busy: boolean;
  error: string | null;
  onAdd: (payload: AlertRecipientCreatePayload) => Promise<void>;
  onToggle: (recipient: AlertRecipient) => Promise<void>;
  onDelete: (id: number) => Promise<void>;
};

export function AdminWhatsappPage({
  recipients,
  busy,
  error,
  onAdd,
  onToggle,
  onDelete
}: AdminWhatsappPageProps) {
  const [phone, setPhone] = useState("");
  const [label, setLabel] = useState("");
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);

  function validatePhone(value: string) {
    const cleaned = value.trim().replace(/\s/g, "");
    if (!cleaned.startsWith("+")) return "Phone must start with + and country code (e.g. +19182438313)";
    if (cleaned.length < 8) return "Phone number too short.";
    return null;
  }

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    setLocalError(null);
    const err = validatePhone(phone);
    if (err) { setLocalError(err); return; }
    await onAdd({ phone_number: phone.trim(), label: label.trim() || null, is_active: true });
    setPhone("");
    setLabel("");
  }

  const active = recipients.filter((r) => r.is_active);
  const inactive = recipients.filter((r) => !r.is_active);

  return (
    <section className="dashboard-stack">
      {/* ── Add number ─────────────────────────────────────────────────────────── */}
      <section className="panel">
        <div className="section-heading">
          <h3>WhatsApp Alert Recipients</h3>
          <p>
            Manage the phone numbers that receive job-match WhatsApp alerts. Numbers must be in E.164 format
            starting with the country code (e.g. +919182438313). The Twilio sandbox must have each number
            opted in before alerts will deliver.
          </p>
        </div>

        <form className="admin-user-form" onSubmit={(e) => { void handleAdd(e); }}>
          <div className="form-row">
            <label className="filter-field">
              <span>Phone Number *</span>
              <input
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="+919182438313"
                required
              />
            </label>
            <label className="filter-field">
              <span>Label (optional)</span>
              <input
                value={label}
                onChange={(e) => setLabel(e.target.value)}
                placeholder="e.g. Priya – Recruiter Lead"
              />
            </label>
          </div>

          {(localError ?? error) ? (
            <div className="error-banner">{localError ?? error}</div>
          ) : null}

          <button className="primary-button" type="submit" disabled={busy}>
            {busy ? "Adding..." : "Add Number"}
          </button>
        </form>
      </section>

      {/* ── Active numbers ──────────────────────────────────────────────────────── */}
      <section className="panel">
        <div className="section-heading">
          <h3>Active Recipients ({active.length})</h3>
          <p>These numbers currently receive WhatsApp job-match alerts.</p>
        </div>

        <div className="whatsapp-recipient-list">
          {active.length === 0 ? (
            <p className="empty-state">No active recipients. Add a number above.</p>
          ) : (
            active.map((r) => (
              <article key={r.id} className="admin-user-card">
                <div>
                  <strong>{r.phone_number}</strong>
                  {r.label ? <p>{r.label}</p> : null}
                  <span className="queue-status-pill queue-status-pending">Active</span>
                </div>
                <div className="admin-user-actions">
                  <button className="secondary-button" disabled={busy} onClick={() => void onToggle(r)}>
                    Pause
                  </button>
                  {deleteConfirmId === r.id ? (
                    <>
                      <button
                        className="danger-button"
                        disabled={busy}
                        onClick={() => { void onDelete(r.id).then(() => setDeleteConfirmId(null)); }}
                      >
                        Confirm Delete
                      </button>
                      <button className="secondary-button" onClick={() => setDeleteConfirmId(null)}>Cancel</button>
                    </>
                  ) : (
                    <button className="danger-button" onClick={() => setDeleteConfirmId(r.id)}>Remove</button>
                  )}
                </div>
              </article>
            ))
          )}
        </div>
      </section>

      {/* ── Paused numbers ──────────────────────────────────────────────────────── */}
      {inactive.length > 0 ? (
        <section className="panel">
          <div className="section-heading">
            <h3>Paused Recipients ({inactive.length})</h3>
            <p>These numbers are saved but currently not receiving alerts.</p>
          </div>
          <div className="whatsapp-recipient-list">
            {inactive.map((r) => (
              <article key={r.id} className="admin-user-card">
                <div>
                  <strong>{r.phone_number}</strong>
                  {r.label ? <p>{r.label}</p> : null}
                  <span className="queue-status-pill queue-status-skipped">Paused</span>
                </div>
                <div className="admin-user-actions">
                  <button className="secondary-button" disabled={busy} onClick={() => void onToggle(r)}>
                    Re-activate
                  </button>
                  {deleteConfirmId === r.id ? (
                    <>
                      <button
                        className="danger-button"
                        disabled={busy}
                        onClick={() => { void onDelete(r.id).then(() => setDeleteConfirmId(null)); }}
                      >
                        Confirm Delete
                      </button>
                      <button className="secondary-button" onClick={() => setDeleteConfirmId(null)}>Cancel</button>
                    </>
                  ) : (
                    <button className="danger-button" onClick={() => setDeleteConfirmId(r.id)}>Remove</button>
                  )}
                </div>
              </article>
            ))}
          </div>
        </section>
      ) : null}
    </section>
  );
}
