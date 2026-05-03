import { useEffect, useRef, useState } from "react";

import type { ForgotPasswordResponse } from "../types";

// Minimal typings for Google Identity Services (loaded via index.html script tag)
declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: {
            client_id: string;
            callback: (response: { credential: string }) => void;
            auto_select?: boolean;
            cancel_on_tap_outside?: boolean;
          }) => void;
          renderButton: (
            element: HTMLElement,
            options: {
              theme?: string;
              size?: string;
              type?: string;
              text?: string;
              shape?: string;
              width?: number;
            }
          ) => void;
          prompt: () => void;
        };
      };
    };
  }
}

type AuthView = "login" | "register" | "forgot" | "reset";

type LoginPageProps = {
  error: string | null;
  successMessage: string | null;
  isSubmitting: boolean;
  initialResetToken?: string | null;
  initialInviteEmail?: string | null;
  forgotPasswordPreview: ForgotPasswordResponse | null;
  googleClientId?: string;
  onLogin: (payload: { email: string; password: string }) => Promise<void>;
  onRegister: (payload: { name: string; email: string; password: string }) => Promise<void>;
  onGoogleAuth: (credential: string) => Promise<void>;
  onForgotPassword: (payload: { email: string }) => Promise<void>;
  onResetPassword: (payload: { token: string; password: string }) => Promise<void>;
};

export function LoginPage({
  error,
  successMessage,
  isSubmitting,
  initialResetToken,
  initialInviteEmail,
  forgotPasswordPreview,
  googleClientId,
  onLogin,
  onRegister,
  onGoogleAuth,
  onForgotPassword,
  onResetPassword
}: LoginPageProps) {
  const [view, setView] = useState<AuthView>(initialResetToken ? "reset" : "login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [resetToken, setResetToken] = useState(initialResetToken ?? "");
  const [newPassword, setNewPassword] = useState("");

  // Register form state
  const [regName, setRegName] = useState("");
  const [regEmail, setRegEmail] = useState(initialInviteEmail ?? "");
  const [regPassword, setRegPassword] = useState("");
  const [regConfirm, setRegConfirm] = useState("");
  const [regPasswordError, setRegPasswordError] = useState<string | null>(null);

  // Google button container refs
  const googleSignInRef = useRef<HTMLDivElement>(null);
  const googleRegisterRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (initialResetToken) {
      setResetToken(initialResetToken);
      setView("reset");
    }
  }, [initialResetToken]);

  // Initialize Google Identity Services once the library is ready
  useEffect(() => {
    if (!googleClientId) return;

    function initGoogle() {
      if (!window.google) return;
      window.google.accounts.id.initialize({
        client_id: googleClientId!,
        callback: (response) => { void onGoogleAuth(response.credential); },
        auto_select: false,
        cancel_on_tap_outside: true,
      });
      renderGoogleButtons();
    }

    function renderGoogleButtons() {
      if (!window.google) return;
      if (googleSignInRef.current) {
        googleSignInRef.current.innerHTML = "";
        window.google.accounts.id.renderButton(googleSignInRef.current, {
          theme: "outline",
          size: "large",
          type: "standard",
          text: "signin_with",
          shape: "rectangular",
          width: 320,
        });
      }
      if (googleRegisterRef.current) {
        googleRegisterRef.current.innerHTML = "";
        window.google.accounts.id.renderButton(googleRegisterRef.current, {
          theme: "outline",
          size: "large",
          type: "standard",
          text: "signup_with",
          shape: "rectangular",
          width: 320,
        });
      }
    }

    // Poll for Google library to be loaded (it's async/defer in index.html)
    let attempts = 0;
    const poll = setInterval(() => {
      if (window.google) {
        clearInterval(poll);
        initGoogle();
      } else if (++attempts > 30) {
        clearInterval(poll);
      }
    }, 300);

    return () => clearInterval(poll);
  // Re-render buttons when the view changes so refs are populated
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [googleClientId, view]);

  // Re-render Google buttons whenever view switches to login or register
  useEffect(() => {
    if (!googleClientId || !window.google) return;
    if (view === "login" && googleSignInRef.current) {
      googleSignInRef.current.innerHTML = "";
      window.google.accounts.id.renderButton(googleSignInRef.current, {
        theme: "outline", size: "large", type: "standard",
        text: "signin_with", shape: "rectangular", width: 320,
      });
    }
    if (view === "register" && googleRegisterRef.current) {
      googleRegisterRef.current.innerHTML = "";
      window.google.accounts.id.renderButton(googleRegisterRef.current, {
        theme: "outline", size: "large", type: "standard",
        text: "signup_with", shape: "rectangular", width: 320,
      });
    }
  }, [googleClientId, view]);

  function handleRegisterSubmit(event: React.FormEvent) {
    event.preventDefault();
    setRegPasswordError(null);
    if (regPassword !== regConfirm) {
      setRegPasswordError("Passwords do not match");
      return;
    }
    if (regPassword.length < 8) {
      setRegPasswordError("Password must be at least 8 characters");
      return;
    }
    void onRegister({ name: regName, email: regEmail, password: regPassword });
  }

  return (
    <main className="login-shell">
      <section className="login-panel">
        <div className="brand-block login-brand-block">
          <img className="brand-logo" src="/brand/think-success-logo.jpg" alt="Think Success Consulting" />
          <p className="eyebrow">Candidate &amp; Team Access</p>
          <h1>Think Success</h1>
          <span>Sign in or register to find your next opportunity.</span>
        </div>

        <div className="auth-tabs">
          <button className={`link-button ${view === "login" ? "auth-tab-active" : ""}`} onClick={() => setView("login")}>
            Sign In
          </button>
          <button className={`link-button ${view === "register" ? "auth-tab-active" : ""}`} onClick={() => setView("register")}>
            Register
          </button>
          <button className={`link-button ${view === "forgot" ? "auth-tab-active" : ""}`} onClick={() => setView("forgot")}>
            Forgot Password
          </button>
          <button className={`link-button ${view === "reset" ? "auth-tab-active" : ""}`} onClick={() => setView("reset")}>
            Reset Password
          </button>
        </div>

        {/* ── Sign In ─────────────────────────────────────────────────────── */}
        {view === "login" ? (
          <>
            <form
              className="login-form"
              onSubmit={(event) => {
                event.preventDefault();
                void onLogin({ email, password });
              }}
            >
              <label className="filter-field">
                <span>Email</span>
                <input value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@email.com" />
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

            {googleClientId ? (
              <div className="google-auth-section">
                <div className="google-auth-divider"><span>or</span></div>
                <div ref={googleSignInRef} className="google-button-wrapper" />
              </div>
            ) : null}
          </>
        ) : null}

        {/* ── Register ────────────────────────────────────────────────────── */}
        {view === "register" ? (
          <>
            <form className="login-form" onSubmit={handleRegisterSubmit}>
              <label className="filter-field">
                <span>Full Name</span>
                <input value={regName} onChange={(e) => setRegName(e.target.value)} placeholder="Your full name" required />
              </label>

              <label className="filter-field">
                <span>Email</span>
                <input
                  type="email"
                  value={regEmail}
                  onChange={(e) => setRegEmail(e.target.value)}
                  placeholder="you@email.com"
                  required
                />
              </label>

              <label className="filter-field">
                <span>Password</span>
                <input
                  type="password"
                  value={regPassword}
                  onChange={(e) => setRegPassword(e.target.value)}
                  placeholder="At least 8 characters"
                  required
                />
              </label>

              <label className="filter-field">
                <span>Confirm Password</span>
                <input
                  type="password"
                  value={regConfirm}
                  onChange={(e) => setRegConfirm(e.target.value)}
                  placeholder="Repeat your password"
                  required
                />
              </label>

              {regPasswordError ? <div className="error-banner">{regPasswordError}</div> : null}

              <button className="primary-button" type="submit" disabled={isSubmitting}>
                {isSubmitting ? "Creating account..." : "Create Account"}
              </button>
            </form>

            {googleClientId ? (
              <div className="google-auth-section">
                <div className="google-auth-divider"><span>or register with</span></div>
                <div ref={googleRegisterRef} className="google-button-wrapper" />
              </div>
            ) : null}
          </>
        ) : null}

        {/* ── Forgot Password ──────────────────────────────────────────────── */}
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

        {/* ── Reset Password ───────────────────────────────────────────────── */}
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
