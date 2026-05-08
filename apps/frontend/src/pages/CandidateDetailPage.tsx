import { useState } from "react";

import { MatchScoreBadge } from "../components/MatchScoreBadge";
import type { Application, Candidate, Job, Match } from "../types";

type CandidateDetailPageProps = {
  candidate: Candidate | null;
  matches: Match[];
  jobMap: Map<number, Job>;
  applications: Application[];
  onSelectMatch: (match: Match) => void;
};

const MATCHES_PER_PAGE = 10;

function buildPageNumbers(current: number, total: number): (number | "…")[] {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
  const pages: (number | "…")[] = [];
  pages.push(1);
  if (current > 3) pages.push("…");
  for (let p = Math.max(2, current - 1); p <= Math.min(total - 1, current + 1); p++) {
    pages.push(p);
  }
  if (current < total - 2) pages.push("…");
  pages.push(total);
  return pages;
}

export function CandidateDetailPage({
  candidate,
  matches,
  jobMap,
  applications,
  onSelectMatch
}: CandidateDetailPageProps) {
  const [page, setPage] = useState(1);

  if (!candidate) {
    return (
      <section className="panel empty-state">
        <h3>Candidate Detail</h3>
        <p>Select a candidate from the filters or pick a match from the list to inspect their details.</p>
      </section>
    );
  }

  const total = matches.length;
  const totalPages = Math.max(1, Math.ceil(total / MATCHES_PER_PAGE));
  const safePage = Math.min(page, totalPages);
  const startIdx = (safePage - 1) * MATCHES_PER_PAGE;
  const pageMatches = matches.slice(startIdx, startIdx + MATCHES_PER_PAGE);

  return (
    <div className="detail-grid">
      <section className="panel">
        <div className="section-heading">
          <h3>{candidate.name}</h3>
          <p>
            {candidate.work_authorization ?? "Authorization unspecified"} • {candidate.years_experience ?? 0} years
            experience
          </p>
        </div>

        <div className="stack-list">
          <div className="metric-row">
            <span>Salary floor</span>
            <strong>
              {candidate.salary_min ? `${candidate.salary_min.toLocaleString()} ${candidate.salary_unit ?? ""}` : "N/A"}
            </strong>
          </div>
          <div className="metric-row">
            <span>Status</span>
            <strong>{candidate.active ? "Active" : "Inactive"}</strong>
          </div>
          <div className="metric-row">
            <span>Applications</span>
            <strong>{applications.length}</strong>
          </div>
          <div className="metric-row">
            <span>Total Matches</span>
            <strong>{total}</strong>
          </div>
        </div>
      </section>

      <section className="panel">
        <div className="section-heading">
          <h3>Candidate Match Detail</h3>
          <p>
            {total > 0
              ? `${total} job match${total !== 1 ? "es" : ""} — showing ${startIdx + 1}–${Math.min(startIdx + MATCHES_PER_PAGE, total)}`
              : "No matches yet for this candidate."}
          </p>
        </div>

        <ul className="match-list">
          {pageMatches.map((match) => {
            const job = jobMap.get(match.job_id);
            const priorityLabel = match.status ?? "Low";

            return (
              <li key={match.id} className="match-card" onClick={() => onSelectMatch(match)}>
                <div className="match-card-header">
                  <div>
                    <strong>{job?.title ?? `Job ${match.job_id}`}</strong>
                    <span>
                      {job?.company ?? "—"} • {job?.source ?? "—"}
                    </span>
                  </div>
                  <MatchScoreBadge score={match.score} priorityLabel={priorityLabel} />
                </div>
                <p>{match.explanation ?? "No explanation available yet."}</p>
              </li>
            );
          })}
        </ul>

        {/* Pagination */}
        {total > MATCHES_PER_PAGE && (
          <div className="ops-pagination" style={{ marginTop: "1rem" }}>
            <span className="ops-page-info">
              {startIdx + 1}–{Math.min(startIdx + MATCHES_PER_PAGE, total)} of {total}
            </span>
            <div className="ops-page-controls">
              <button
                className="ops-page-btn"
                disabled={safePage <= 1}
                onClick={() => setPage((p) => p - 1)}
              >‹</button>
              {buildPageNumbers(safePage, totalPages).map((p, i) =>
                p === "…" ? (
                  <span key={`ellipsis-${i}`} className="ops-page-ellipsis">…</span>
                ) : (
                  <button
                    key={p}
                    className={`ops-page-btn${safePage === p ? " ops-page-btn-active" : ""}`}
                    onClick={() => setPage(Number(p))}
                  >
                    {p}
                  </button>
                )
              )}
              <button
                className="ops-page-btn"
                disabled={safePage >= totalPages}
                onClick={() => setPage((p) => p + 1)}
              >›</button>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
