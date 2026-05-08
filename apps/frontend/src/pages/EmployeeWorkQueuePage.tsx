import { useState } from "react";

import { JobCard } from "../components/JobCard";
import type { Candidate, Job, Match, WorkQueueItem, WorkQueueReportPayload } from "../types";

type EmployeeWorkQueuePageProps = {
  matches: Match[];
  workQueueItems: WorkQueueItem[];
  candidateMap: Map<number, Candidate>;
  jobMap: Map<number, Job>;
  busyMatchId: number | null;
  busyQueueId: number | null;
  onViewJob: (match: Match) => void;
  onMarkApplied: (match: Match) => Promise<void>;
  onSkip: (match: Match) => Promise<void>;
  onReport: (queueItem: WorkQueueItem, payload: WorkQueueReportPayload) => Promise<void>;
};

const REPORT_OPTIONS: { value: WorkQueueReportPayload["report_status"]; label: string }[] = [
  { value: "invalid", label: "Invalid listing" },
  { value: "outdated", label: "Job already filled / outdated" },
  { value: "not_relevant", label: "Not relevant to candidate" }
];

const PAGE_SIZE_OPTIONS = [10, 25, 50];

function ReportPanel({
  queueItem,
  busy,
  onReport
}: {
  queueItem: WorkQueueItem;
  busy: boolean;
  onReport: (payload: WorkQueueReportPayload) => Promise<void>;
}) {
  const [open, setOpen] = useState(false);
  const [status, setStatus] = useState<WorkQueueReportPayload["report_status"]>("invalid");
  const [reason, setReason] = useState("");
  const [done, setDone] = useState(!!queueItem.report_status);

  if (done) {
    return (
      <span className="queue-status-pill queue-status-skipped" style={{ fontSize: "0.72rem" }}>
        Reported: {queueItem.report_status ?? status}
      </span>
    );
  }

  if (!open) {
    return (
      <button className="report-button" onClick={() => setOpen(true)}>
        ⚑ Report
      </button>
    );
  }

  return (
    <div className="report-panel">
      <select value={status} onChange={(e) => setStatus(e.target.value as WorkQueueReportPayload["report_status"])}>
        {REPORT_OPTIONS.map((opt) => (
          <option key={opt.value} value={opt.value}>{opt.label}</option>
        ))}
      </select>
      <input
        placeholder="Optional note…"
        value={reason}
        onChange={(e) => setReason(e.target.value)}
      />
      <div style={{ display: "flex", gap: "0.5rem" }}>
        <button
          className="danger-button"
          disabled={busy}
          onClick={() =>
            void onReport({ report_status: status, report_reason: reason || null }).then(() => {
              setDone(true);
              setOpen(false);
            })
          }
        >
          {busy ? "Saving…" : "Submit Report"}
        </button>
        <button className="secondary-button" onClick={() => setOpen(false)}>Cancel</button>
      </div>
    </div>
  );
}

export function EmployeeWorkQueuePage({
  matches,
  workQueueItems,
  candidateMap,
  jobMap,
  busyMatchId,
  busyQueueId,
  onViewJob,
  onMarkApplied,
  onSkip,
  onReport
}: EmployeeWorkQueuePageProps) {
  const [only48h, setOnly48h] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  // Build a lookup: match_id → queue item
  const queueByMatchId = new Map(
    workQueueItems.filter((q) => q.match_id != null).map((q) => [q.match_id!, q])
  );

  // 48h filter: keep matches whose queue item was created within the last 48 hours
  const cutoff48h = Date.now() - 48 * 60 * 60 * 1000;
  const recentMatchIds = only48h
    ? new Set(
        workQueueItems
          .filter((q) => q.match_id != null && new Date(q.created_at).getTime() >= cutoff48h)
          .map((q) => q.match_id!)
      )
    : null;

  const filteredMatches = recentMatchIds
    ? matches.filter((m) => recentMatchIds.has(m.id))
    : matches;

  // Pagination
  const totalMatches = filteredMatches.length;
  const totalPages = Math.max(1, Math.ceil(totalMatches / pageSize));
  const safePageNum = Math.min(page, totalPages);
  const startIdx = (safePageNum - 1) * pageSize;
  const pageMatches = filteredMatches.slice(startIdx, startIdx + pageSize);

  const startItem = totalMatches === 0 ? 0 : startIdx + 1;
  const endItem = Math.min(startIdx + pageSize, totalMatches);

  function handleOnly48hToggle(next: boolean) {
    setOnly48h(next);
    setPage(1);
  }

  function handlePageSizeChange(next: number) {
    setPageSize(next);
    setPage(1);
  }

  return (
    <section className="panel">
      <div className="section-heading">
        <h3>Employee Work Queue</h3>
        <p>Operational queue ordered by match quality and priority. Use ⚑ Report to flag invalid or outdated listings.</p>
      </div>

      {/* ── Filters row ────────────────────────────────────────────────────── */}
      <div className="ops-filters-row" style={{ marginBottom: "1rem" }}>
        <div className="filter-field">
          <span>Time window</span>
          <div className="ops-time-toggle">
            <button
              className={`ops-time-btn${!only48h ? " ops-time-btn-active" : ""}`}
              onClick={() => handleOnly48hToggle(false)}
            >
              All time
            </button>
            <button
              className={`ops-time-btn${only48h ? " ops-time-btn-active" : ""}`}
              onClick={() => handleOnly48hToggle(true)}
            >
              Last 48 h
            </button>
          </div>
        </div>
        <div className="filter-field" style={{ marginLeft: "auto", alignItems: "flex-end" }}>
          <span style={{ fontSize: "0.82rem", color: "var(--brand-muted)" }}>
            {totalMatches === 0
              ? "No matches"
              : `${startItem}–${endItem} of ${totalMatches} match${totalMatches !== 1 ? "es" : ""}`}
          </span>
        </div>
      </div>

      <div className="queue-grid">
        {pageMatches.map((match) => {
          const candidate = candidateMap.get(match.candidate_id);
          const job = jobMap.get(match.job_id);
          const queueItem = queueByMatchId.get(match.id);

          return (
            <div key={match.id} className="queue-card-wrapper">
              <JobCard
                match={match}
                candidate={candidate}
                job={job}
                compact
                queueStatus={queueItem?.status}
                disabled={busyMatchId === match.id}
                onViewJob={() => onViewJob(match)}
                onApply={() => void onMarkApplied(match)}
                onSkip={() => void onSkip(match)}
              />
              {queueItem ? (
                <div className="queue-card-footer">
                  <ReportPanel
                    queueItem={queueItem}
                    busy={busyQueueId === queueItem.id}
                    onReport={(payload) => onReport(queueItem, payload)}
                  />
                </div>
              ) : null}
            </div>
          );
        })}

        {pageMatches.length === 0 ? (
          <p className="empty-state">
            {only48h ? "No matches in the last 48 hours." : "No matches in the queue yet."}
          </p>
        ) : null}
      </div>

      {/* ── Pagination ──────────────────────────────────────────────────────── */}
      {totalMatches > pageSize && (
        <div className="ops-pagination">
          <span className="ops-page-info">
            {startItem}–{endItem} of {totalMatches}
          </span>

          <div className="ops-page-controls">
            <button
              className="ops-page-btn"
              disabled={safePageNum <= 1}
              onClick={() => setPage((p) => p - 1)}
            >‹</button>

            {buildPageNumbers(safePageNum, totalPages).map((p, i) =>
              p === "…" ? (
                <span key={`ellipsis-${i}`} className="ops-page-ellipsis">…</span>
              ) : (
                <button
                  key={p}
                  className={`ops-page-btn${safePageNum === p ? " ops-page-btn-active" : ""}`}
                  onClick={() => setPage(Number(p))}
                >
                  {p}
                </button>
              )
            )}

            <button
              className="ops-page-btn"
              disabled={safePageNum >= totalPages}
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

// ── Helpers ────────────────────────────────────────────────────────────────────

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
