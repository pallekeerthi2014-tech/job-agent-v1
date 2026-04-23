import type { ReactNode } from "react";

type LayoutProps = {
  activePage: string;
  onNavigate: (page: string) => void;
  children: ReactNode;
};

const NAV_ITEMS = [
  { id: "operations-dashboard", label: "Operations Dashboard" },
  { id: "candidate-list", label: "Candidate List" },
  { id: "candidate-detail", label: "Candidate Detail" },
  { id: "employee-work-queue", label: "Employee Work Queue" },
  { id: "job-match-detail", label: "Job Match Detail" }
];

export function Layout({ activePage, onNavigate, children }: LayoutProps) {
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
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              className={`nav-button ${activePage === item.id ? "nav-button-active" : ""}`}
              onClick={() => onNavigate(item.id)}
            >
              {item.label}
            </button>
          ))}
        </nav>
      </aside>

      <div className="content-shell">{children}</div>
    </div>
  );
}
