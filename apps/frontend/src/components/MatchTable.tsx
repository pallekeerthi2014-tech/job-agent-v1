import { useState } from "react";

import { MatchScoreBadge } from "./MatchScoreBadge";
import type { Candidate, Job, Match } from "../types";

type MatchTableProps = {
  matches: Match[];
  candidateMap: Map<number, Candidate>;
  jobMap: Map<number, Job>;
  onSelectMatch: (match: Match) => void;
};

const PAGE_SIZE_OPTIONS = [20, 50, 100];

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

export function MatchTable({ matches, candidateMap, jobMap, onSelectMatch }: MatchTableProps) {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  const total = matches.length;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const safePage = Math.min(page, totalPages);
  const startIdx = (safePage - 1) * pageSize;
  const pageMatches = matches.slice(startIdx, startIdx + pageSize);
  const startItem = total === 0 ? 0 : startIdx + 1;
  const endItem = Math.min(startIdx + pageSize, total);

  function handlePageSizeChange(next: number) {
    setPageSize(next);
    setPage(1);
  }

  return (
    <section className="panel">
      <div className="section-heading">
        <h3>Candidate List</h3>
        <p>Top matching opportunities with source, score, and analyst context.</p>
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Candidate</th>
              <th>Score</th>
              <th>Job</th>
              <th>Company</th>
              <th>Source</th>
              <th>Posted</th>
              <th>Priority</th>
            </tr>
          </thead>
          <tbody>
            {pageMatches.map((match) => {
              const candidate = candidateMap.get(match.candidate_id);
              const job = jobMap.get(match.job_id);
              const priorityLabel = match.status ?? "Low";

              return (
                <tr key={match.id} onClick={() => onSelectMatch(match)} className="clickable-row">
                  <td>{candidate?.name ?? `Candidate ${match.candidate_id}`}</td>
                  <td>
                    <MatchScoreBadge score={match.score} priorityLabel={priorityLabel} />
                  </td>
                  <td>{job?.title ?? `Job ${match.job_id}`}</td>
                  <td>{job?.company ?? "—"}</td>
                  <td>{job?.source ?? "—"}</td>
                  <td>{job?.posted_date ?? "—"}</td>
                  <td>{priorityLabel}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {total > pageSize && (
        <div className="ops-pagination">
          <span className="ops-page-info">
            {startItem}–{endItem} of {total}
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

          <div className="ops-per-page">
            <span>Rows:</span>
            <select
              value={pageSize}
              onChange={(e) => handlePageSizeChange(Number(e.target.value))}
            >
              {PAGE_SIZE_OPTIONS.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
        </div>
      )}
    </section>
  );
}
