import { useState } from "react";

import { apiClient } from "../api/client";
import type { InviteCandidatePayload, User, UserCreatePayload } from "../types";

type AdminUsersPageProps = {
  users: User[];
  busy: boolean;
  error: string | null;
  onCreateUser: (payload: UserCreatePayload) => Promise<void>;
  onToggleUser: (user: User) => Promise<void>;
  onResetPassword: (user: User, newPassword: string) => Promise<void>;
};

const INITIAL_FORM: UserCreatePayload = {
  name: "",
  email: "",
  password: "",
  role: "employee",
  is_active: true,
  employee_id: null
};

// ── Invite Candidate Modal ────────────────────────────────────────────────────

function InviteModal({ onClose }: { onClose: () => void }) {
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteName, setInviteName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  async function handleInvite(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setPreviewUrl(null);
    try {
      const payload: InviteCandidatePayload = {
        email: inviteEmail,
        name: inviteName || null,
      };
      const result = await apiClient.inviteCandidate(payload);
      if (result.delivery === "preview" && result.invite_url) {
        setPreviewUrl(result.invite_url);
      } else {
        // Email was sent
        onClose();
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to send invite");
    } finally {
      setBusy(false);
    }
  }

  function copyLink() {
    if (!previewUrl) return;
    void navigator.clipboard.writeText(previewUrl).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  return (
    <div className="modal-backdrop" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="modal-box" style={{ maxWidth: 480 }}>
        <div className="modal-header">
          <h3>Invite Candidate</h3>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>

        {!previewUrl ? (
          <form onSubmit={handleInvite} className="modal-body">
            <p style={{ marginBottom: "1rem", color: "var(--text-muted, #64748b)", fontSize: "0.9rem" }}>
              Send a registration invitation link to a candidate's email address.
            </p>

            <label className="filter-field">
              <span>Candidate Email *</span>
              <input
                type="email"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
                placeholder="candidate@email.com"
                required
              />
            </label>

            <label className="filter-field" style={{ marginTop: "0.75rem" }}>
              <span>Candidate Name (optional)</span>
              <input
                value={inviteName}
                onChange={(e) => setInviteName(e.target.value)}
                placeholder="e.g. Jane Smith"
              />
            </label>

            {error && <div className="error-banner" style={{ marginTop: "0.75rem" }}>{error}</div>}

            <div className="modal-footer">
              <button className="secondary-button" type="button" onClick={onClose}>
                Cancel
              </button>
              <button className="primary-button" type="submit" disabled={busy || !inviteEmail}>
                {busy ? "Sending…" : "Send Invite"}
              </button>
            </div>
          </form>
        ) : (
          <div className="modal-body">
            <div className="auth-helper-card" style={{ marginBottom: "1rem" }}>
              <strong>📧 SMTP not configured — preview link</strong>
              <p style={{ fontSize: "0.85rem", color: "var(--text-muted, #64748b)", marginTop: 8 }}>
                Email delivery is not set up yet. Share this link directly with the candidate.
              </p>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 12 }}>
                <code style={{ flex: 1, padding: "8px 12px", borderRadius: 8, background: "var(--surface-inset, #f1f5f9)", fontSize: "0.78rem", wordBreak: "break-all" }}>
                  {previewUrl}
                </code>
                <button className="secondary-button" onClick={copyLink} style={{ whiteSpace: "nowrap", flexShrink: 0 }}>
                  {copied ? "✓ Copied" : "Copy Link"}
                </button>
              </div>
            </div>
            <div className="modal-footer">
              <button className="primary-button" onClick={onClose}>Done</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────────────────────

export function AdminUsersPage({
  users,
  busy,
  error,
  onCreateUser,
  onToggleUser,
  onResetPassword
}: AdminUsersPageProps) {
  const [form, setForm] = useState<UserCreatePayload>(INITIAL_FORM);
  const [resetTargetId, setResetTargetId] = useState<number | null>(null);
  const [resetPassword, setResetPasswordValue] = useState("");
  const [showInviteModal, setShowInviteModal] = useState(false);

  return (
    <section className="dashboard-stack">
      {showInviteModal && <InviteModal onClose={() => setShowInviteModal(false)} />}

      <section className="panel">
        <div className="section-heading">
          <div>
            <h3>Super Admin User Management</h3>
            <p>Create employee logins, activate or pause access, and reset passwords from one place.</p>
          </div>
          <button
            className="primary-button"
            style={{ marginLeft: "auto", flexShrink: 0 }}
            onClick={() => setShowInviteModal(true)}
          >
            ✉ Invite Candidate
          </button>
        </div>

        <form
          className="admin-user-form"
          onSubmit={(event) => {
            event.preventDefault();
            void onCreateUser(form).then(() => setForm(INITIAL_FORM));
          }}
        >
          <label className="filter-field">
            <span>Name</span>
            <input
              value={form.name}
              onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
              placeholder="Employee or admin name"
            />
          </label>

          <label className="filter-field">
            <span>Email</span>
            <input
              value={form.email}
              onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))}
              placeholder="employee@thinksuccessitconsulting.com"
            />
          </label>

          <label className="filter-field">
            <span>Role</span>
            <select
              value={form.role}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  role: event.target.value as UserCreatePayload["role"],
                  employee_id: null
                }))
              }
            >
              <option value="employee">Employee</option>
              <option value="super_admin">Super Admin</option>
            </select>
          </label>

          <label className="filter-field">
            <span>Temporary Password</span>
            <input
              value={form.password}
              onChange={(event) => setForm((current) => ({ ...current, password: event.target.value }))}
              placeholder="Set first password"
            />
          </label>

          <button className="primary-button" type="submit" disabled={busy}>
            {busy ? "Saving..." : "Create User"}
          </button>
        </form>

        {error ? <div className="error-banner">{error}</div> : null}
      </section>

      <section className="panel">
        <div className="section-heading">
          <h3>Current Users</h3>
          <p>Employee logins are linked to employee queue ownership. Super admins can see all candidates and jobs.</p>
        </div>

        <div className="admin-user-list">
          {users.map((user) => (
            <article key={user.id} className="admin-user-card">
              <div>
                <strong>{user.name}</strong>
                <p>
                  {user.email} · {user.role === "super_admin" ? "Super Admin" : user.role === "candidate" ? "Candidate" : "Employee"}
                </p>
                <span className={`queue-status-pill queue-status-${user.is_active ? "pending" : "skipped"}`}>
                  {user.is_active ? "Active" : "Inactive"}
                </span>
              </div>

              <div className="admin-user-actions">
                <button className="secondary-button" disabled={busy} onClick={() => void onToggleUser(user)}>
                  {user.is_active ? "Deactivate" : "Activate"}
                </button>
                <input
                  value={resetTargetId === user.id ? resetPassword : ""}
                  onFocus={() => setResetTargetId(user.id)}
                  onChange={(event) => {
                    setResetTargetId(user.id);
                    setResetPasswordValue(event.target.value);
                  }}
                  placeholder="New password"
                />
                <button
                  className="primary-button"
                  disabled={busy || resetTargetId !== user.id || !resetPassword}
                  onClick={() =>
                    void onResetPassword(user, resetPassword).then(() => {
                      setResetTargetId(null);
                      setResetPasswordValue("");
                    })
                  }
                >
                  Reset Password
                </button>
              </div>
            </article>
          ))}
        </div>
      </section>
    </section>
  );
}
