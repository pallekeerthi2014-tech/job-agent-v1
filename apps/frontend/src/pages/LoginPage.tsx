import { useEffect, useState } from "react";

import type { ForgotPasswordResponse } from "../types";

type AuthView = "login" | "forgot" | "reset";

type LoginPageProps = {
  error: string | null;
  successMessage: string | null;
  isSubmitting: boolean;
  initialResetToken?: string | null;
  forgotPasswordPreview: ForgotPasswordResponse | null;
  onLogin: (payload: { email: string; password: string }) => Promise<void>;
  onForgotPassword: (payload: { email: string }) => Promise<void>;
  onResetPassword: (payload: { token: string; password: string }) => Promise<void>;
};

export function LoginPage({
  error,
  successMessage,
  isSubmitting,
  initialResetToken,
  forgotPasswordPreview,
  onLogin,
  onForgotPassword,
  onResetPassword
}: LoginPageProps) {
  const [view, setView] = useState<AuthView>(initialResetToken ? "reset" : "login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [resetToken, setResetToken] = useState(initialResetToken ?? "");
  const [newPassword, setNewPassword] = useState("");

  useEffect(() => {
    if (initialResetToken) {
      setResetToken(initialResetToken);
      setView("reset");
    }
  }, [initialResetToken]);

  return (
    <main className="login-shell">
      <section className="login-panel">
        <div className="brand-block login-brand-block">
          <img className="brand-logo" src="/brand/think-success-logo.jpg" alt="Think Success Consulting" />
          <p className="eyebrow">Secure Team Access</p>
          <h1>Think Success</h1>
          <span>Sign in to the job matching operations dashboard.</span>
        </div>

        <div className="auth-tabs">
          <button className={`link-button ${view === "login" ? "auth-tab-active" : ""}`} onClick={() => setView("login")}>
            Sign In
          </button>
          <button className={`link-button ${view === "forgot" ? "auth-tab-active" : ""}`} onClick={() => setView("forgot")}>
            Forgot Password
          </button>
          <button className={`link-button ${view === "reset" ? "auth-tab-active" : ""}`} onClick={() => setView("reset")}>
            Reset Password
          </button>
        </div>

        {view === "login" ? (
          <form
            className="login-form"
            onSubmit={(event) => {
              event.preventDefault();
              void onLogin({ email, password });
            }}
          >
            <label className="filter-field">
              <span>Email</span>
              <input value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@company.com" />
            </label>

            <label className="filter-field">
              <span>Password</span>
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Enter your password"
              />
            </label>

            <button className="primary-button" type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Signing in..." : "Sign In"}
            </button>
          </form>
        ) : null}

        {view === "forgot" ? (
          <form
            className="login-form"
            onSubmit={(event) => {
              event.preventDefault();
              void onForgotPassword({ email });
            }}
          >
            <label className="filter-field">
              <span>Work Email</span>
              <input value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@company.com" />
            </label>

            <button className="primary-button" type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Preparing..." : "Send Reset Link"}
            </button>

            {forgotPasswordPreview?.delivery === "preview" && forgotPasswordPreview.reset_token ? (
              <div className="auth-helper-card">
                <strong>Local reset preview</strong>
                <p>SMTP is not configured yet, so your local reset token is shown below.</p>
                <code>{forgotPasswordPreview.reset_token}</code>
                {forgotPasswordPreview.reset_url ? <a href={forgotPasswordPreview.reset_url}>{forgotPasswordPreview.reset_url}</a> : null}
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => {
                    setResetToken(forgotPasswordPreview.reset_token ?? "");
                    setView("reset");
                  }}
                >
                  Continue To Reset
                </button>
              </div>
            ) : null}
          </form>
        ) : null}

        {view === "reset" ? (
          <form
            className="login-form"
            onSubmit={(event) => {
              event.preventDefault();
              void onResetPassword({ token: resetToken, password: newPassword });
            }}
          >
            <label className="filter-field">
              <span>Reset Token</span>
              <input value={resetToken} onChange={(event) => setResetToken(event.target.value)} placeholder="Paste the reset token" />
            </label>

            <label className="filter-field">
              <span>New Password</span>
              <input
                type="password"
                value={newPassword}
                onChange={(event) => setNewPassword(event.target.value)}
                placeholder="Choose a new password"
              />
            </label>

            <button className="primary-button" type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Updating..." : "Reset Password"}
            </button>
          </form>
        ) : null}

        {successMessage ? <div className="success-banner">{successMessage}</div> : null}
        {error ? <div className="error-banner">{error}</div> : null}
      </section>
    </main>
  );
}
