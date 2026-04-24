import { useState } from "react";

import type { User, UserCreatePayload } from "../types";

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

  return (
    <section className="dashboard-stack">
      <section className="panel">
        <div className="section-heading">
          <h3>Super Admin User Management</h3>
          <p>Create employee logins, activate or pause access, and reset passwords from one place.</p>
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
                  {user.email} · {user.role === "super_admin" ? "Super Admin" : "Employee"}
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
