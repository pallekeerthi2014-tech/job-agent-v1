import type { ReactNode } from "react";

import type { User } from "../types";

type LayoutProps = {
  activePage: string;
  onNavigate: (page: string) => void;
  currentUser: User;
  onLogout: () => void;
  children: ReactNode;
};

const COMMON_NAV_ITEMS = [
  { id: "operations-dashboard", label: "📋 Operations Dashboard" },
  { id: "employee-work-queue", label: "🗂 Work Queue" },
  { id: "candidate-list", label: "👥 Candidate List" },
  { id: "candidate-detail", label: "🔍 Candidate Detail" },
  { id: "job-match-detail", label: "🎯 Job Match Detail" }
];

const ADMIN_NAV_ITEMS = [
  { id: "admin-candidates", label: "➕ Manage Candidates" },
  { id: "admin-users", label: "👤 User Admin" },
  { id: "admin-whatsapp", label: "📱 WhatsApp Alerts" },
  { id: "analytics", label: "📊 Analytics" }
];

export function Layout({ activePage, onNavigate, currentUser, onLogout, children }: LayoutProps) {
  const navItems =
    currentUser.role === "super_admin"
      ? [...COMMON_NAV_ITEMS, ...ADMIN_NAV_ITEMS]
      : COMMON_NAV_ITEMS;

  // Group admin items visually with a divider
  const isAdmin = currentUser.role === "super_admin";

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <img className="brand-logo" src="/brand/think-success-logo.jpg" alt="Think Success Consulting" />
          <p className="eyebrow">Operations Console</p>
          <h1>Think Success</h1>
          <span>Job matching operations dashboard</span>
        </div>

        <nav className="nav-list">
          {COMMON_NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              className={`nav-button ${activePage === item.id ? "nav-button-active" : ""}`}
              onClick={() => onNavigate(item.id)}
            >
              {item.label}
            </button>
          ))}

          {isAdmin ? (
            <>
              <div className="nav-divider">Admin</div>
              {ADMIN_NAV_ITEMS.map((item) => (
                <button
                  key={item.id}
                  className={`nav-button ${activePage === item.id ? "nav-button-active" : ""}`}
                  onClick={() => onNavigate(item.id)}
                >
                  {item.label}
                </button>
              ))}
            </>
          ) : null}
        </nav>

        <div className="sidebar-user-card">
          <strong>{currentUser.name}</strong>
          <span>{currentUser.role === "super_admin" ? "Super Admin" : "Employee Login"}</span>
          <small>{currentUser.email}</small>
          <button className="logout-button" onClick={onLogout}>
            Logout
          </button>
        </div>
      </aside>

      <div className="content-shell">{children}</div>
    </div>
  );
}
