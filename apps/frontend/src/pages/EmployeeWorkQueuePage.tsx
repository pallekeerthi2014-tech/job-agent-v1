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
  // Build a lookup: match_id → queue item
  const queueByMatchId = new Map(
    workQueueItems.filter((q) => q.match_id != null).map((q) => [q.match_id!, q])
  );

  return (
    <section className="panel">
      <div className="section-heading">
        <h3>Employee Work Queue</h3>
        <p>Operational queue ordered by match quality and priority. Use ⚑ Report to flag invalid or outdated listings.</p>
      </div>

      <div className="queue-grid">
        {matches.map((match) => {
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

        {matches.length === 0 ? (
          <p className="empty-state">No matches in the queue yet.</p>
        ) : null}
      </div>
    </section>
  );
}
