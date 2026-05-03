import type { AnalyticsOverview, EmployeeStat } from "../types";

type AnalyticsPageProps = {
  data: AnalyticsOverview | null;
  busy: boolean;
  error: string | null;
  onRefresh: () => void;
};

function pct(num: number, denom: number) {
  if (!denom) return "0%";
  return `${Math.round((num / denom) * 100)}%`;
}

function StatCard({ label, value, sub }: { label: string; value: number | string; sub?: string }) {
  return (
    <div className="stat-card">
      <span className="stat-label">{label}</span>
      <strong className="stat-value">{value}</strong>
      {sub ? <span className="stat-sub">{sub}</span> : null}
    </div>
  );
}

export function AnalyticsPage({ data, busy, error, onRefresh }: AnalyticsPageProps) {
  if (busy && !data) {
    return (
      <section className="panel">
        <p>Loading analytics…</p>
      </section>
    );
  }

  if (error) {
    return (
      <section className="panel">
        <div className="error-banner">{error}</div>
        <button className="secondary-button" onClick={onRefresh}>Retry</button>
      </section>
    );
  }

  if (!data) {
    return (
      <section className="panel">
        <p className="empty-state">No analytics data available yet. Run the pipeline first.</p>
      </section>
    );
  }

  const { funnel, jobs_by_source, freshness, reports_by_source, top_candidates, employee_stats = [] } = data;
  const totalFresh = freshness.find((f) => f.status === "fresh")?.count ?? 0;
  const totalStale = freshness.find((f) => f.status === "stale")?.count ?? 0;
  const totalOther = freshness.find((f) => !["fresh", "stale"].includes(f.status))?.count ?? 0;

  return (
    <section className="dashboard-stack">
      {/* ── Pipeline Funnel ────────────────────────────────────────────────────── */}
      <section className="panel">
        <div className="section-heading">
          <h3>Pipeline Funnel</h3>
          <p>End-to-end conversion from raw scrape to applied status.</p>
          <button className="secondary-button" style={{ marginTop: "0.5rem" }} disabled={busy} onClick={onRefresh}>
            {busy ? "Refreshing…" : "↺ Refresh"}
          </button>
        </div>

        <div className="stat-grid">
          <StatCard label="Raw Jobs" value={funnel.total_raw} />
          <StatCard
            label="Normalized"
            value={funnel.total_normalized}
            sub={pct(funnel.total_normalized, funnel.total_raw) + " of raw"}
          />
          <StatCard
            label="Matched"
            value={funnel.total_matched}
            sub={pct(funnel.total_matched, funnel.total_normalized) + " of normalized"}
          />
          <StatCard
            label="In Queue"
            value={funnel.total_queued}
            sub={pct(funnel.total_queued, funnel.total_matched) + " of matches"}
          />
          <StatCard
            label="Applied"
            value={funnel.total_applied}
            sub={pct(funnel.total_applied, funnel.total_queued) + " of queued"}
          />
        </div>

        {/* Visual funnel bar */}
        <div className="funnel-bars">
          {[
            { label: "Raw", count: funnel.total_raw, color: "#93c5fd" },
            { label: "Normalized", count: funnel.total_normalized, color: "#60a5fa" },
            { label: "Matched", count: funnel.total_matched, color: "#3b82f6" },
            { label: "Queued", count: funnel.total_queued, color: "#1d4ed8" },
            { label: "Applied", count: funnel.total_applied, color: "#1e3a8a" }
          ].map(({ label, count, color }) => {
            const widthPct = funnel.total_raw ? Math.max(4, Math.round((count / funnel.total_raw) * 100)) : 4;
            return (
              <div key={label} className="funnel-row">
                <span className="funnel-label">{label}</span>
                <div className="funnel-bar-track">
                  <div
                    className="funnel-bar-fill"
                    style={{ width: `${widthPct}%`, background: color }}
                  />
                </div>
                <span className="funnel-count">{count.toLocaleString()}</span>
              </div>
            );
          })}
        </div>
      </section>

      {/* ── Jobs by Source ─────────────────────────────────────────────────────── */}
      <section className="panel">
        <div className="section-heading">
          <h3>Jobs by Source</h3>
          <p>Volume and recency per feed. Sources with reported-invalid listings are flagged below.</p>
        </div>

        <div className="analytics-table-wrap">
          <table className="analytics-table">
            <thead>
              <tr>
                <th>Source</th>
                <th>Total Jobs</th>
                <th>Latest Posted</th>
                <th>Reports</th>
                <th>Invalid</th>
                <th>Outdated</th>
                <th>Not Relevant</th>
              </tr>
            </thead>
            <tbody>
              {jobs_by_source.map((row) => {
                const report = reports_by_source.find((r) => r.source === row.source);
                const hasReports = (report?.total ?? 0) > 0;
                return (
                  <tr key={row.source} className={hasReports ? "row-flagged" : ""}>
                    <td><strong>{row.source}</strong></td>
                    <td>{row.count.toLocaleString()}</td>
                    <td>{row.latest_posted ? new Date(row.latest_posted).toLocaleDateString() : "—"}</td>
                    <td>{report?.total ?? 0}</td>
                    <td>{report?.invalid ?? 0}</td>
                    <td>{report?.outdated ?? 0}</td>
                    <td>{report?.not_relevant ?? 0}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      {/* ── Freshness ──────────────────────────────────────────────────────────── */}
      <section className="panel">
        <div className="section-heading">
          <h3>Job Freshness</h3>
          <p>Distribution of normalized jobs by recency of posting date.</p>
        </div>
        <div className="stat-grid">
          <StatCard label="Fresh (≤7 days)" value={totalFresh} sub={pct(totalFresh, funnel.total_normalized) + " of normalized"} />
          <StatCard label="Stale (>7 days)" value={totalStale} sub={pct(totalStale, funnel.total_normalized) + " of normalized"} />
          {totalOther > 0 ? <StatCard label="No Date" value={totalOther} /> : null}
        </div>
      </section>

      {/* ── Top Candidates ─────────────────────────────────────────────────────── */}
      <section className="panel">
        <div className="section-heading">
          <h3>Top Candidates by Match Volume</h3>
          <p>Candidates with the most job matches and their average score.</p>
        </div>

        {top_candidates.length === 0 ? (
          <p className="empty-state">No candidate match data yet.</p>
        ) : (
          <div className="analytics-table-wrap">
            <table className="analytics-table">
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Candidate</th>
                  <th>Matches</th>
                  <th>Avg Score</th>
                  <th>Score Bar</th>
                </tr>
              </thead>
              <tbody>
                {top_candidates.map((row, i) => (
                  <tr key={row.candidate_id}>
                    <td>#{i + 1}</td>
                    <td><strong>{row.candidate_name}</strong></td>
                    <td>{row.match_count}</td>
                    <td>{row.avg_score.toFixed(1)}</td>
                    <td>
                      <div style={{ background: "#e0e7ef", borderRadius: 3, height: 8, width: 100 }}>
                        <div
                          style={{
                            background: "#1B6EC2",
                            width: `${Math.min(100, row.avg_score)}%`,
                            height: "100%",
                            borderRadius: 3
                          }}
                        />
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* ── Employee Activity ───────────────────────────────────────────────────── */}
      <section className="panel">
        <div className="section-heading">
          <h3>Employee Activity</h3>
          <p>Per-employee, per-candidate breakdown — jobs queued, applied, and still pending.</p>
        </div>

        {employee_stats.length === 0 ? (
          <p className="empty-state">No employee queue data yet.</p>
        ) : (
          <EmployeeStatsTable rows={employee_stats} />
        )}
      </section>
    </section>
  );
}

// ── Employee stats table ──────────────────────────────────────────────────────

function EmployeeStatsTable({ rows }: { rows: EmployeeStat[] }) {
  // Group by employee for better readability
  const byEmployee = new Map<string, EmployeeStat[]>();
  for (const row of rows) {
    const key = `${row.employee_id}:${row.employee_name}`;
    const existing = byEmployee.get(key) ?? [];
    existing.push(row);
    byEmployee.set(key, existing);
  }

  return (
    <div className="analytics-table-wrap">
      <table className="employee-stats-table">
        <thead>
          <tr>
            <th>Employee</th>
            <th>Candidate</th>
            <th>Total Queued</th>
            <th>Applied</th>
            <th>Pending</th>
            <th>Applied %</th>
          </tr>
        </thead>
        <tbody>
          {Array.from(byEmployee.entries()).map(([empKey, empRows]) => {
            const empTotal = empRows.reduce((s, r) => s + r.total, 0);
            const empApplied = empRows.reduce((s, r) => s + r.applied, 0);
            const empPending = empRows.reduce((s, r) => s + r.pending, 0);
            const empPct = empTotal ? Math.round((empApplied / empTotal) * 100) : 0;

            return empRows.map((row, i) => (
              <tr key={`${empKey}:${row.candidate_id}`}>
                {i === 0 ? (
                  <td rowSpan={empRows.length} style={{ fontWeight: 700, verticalAlign: "top", borderRight: "2px solid var(--brand-border)" }}>
                    {row.employee_name}
                    <div style={{ fontSize: "0.75rem", fontWeight: 400, color: "var(--brand-muted)", marginTop: 2 }}>
                      {empApplied}/{empTotal} applied ({empPct}%)
                    </div>
                  </td>
                ) : null}
                <td>{row.candidate_name}</td>
                <td>{row.total}</td>
                <td className="applied-cell">{row.applied}</td>
                <td className="pending-cell">{row.pending}</td>
                <td>
                  <span style={{ fontSize: "0.8rem", marginRight: 6 }}>
                    {row.total ? Math.round((row.applied / row.total) * 100) : 0}%
                  </span>
                  <span className="applied-bar-track">
                    <span
                      className="applied-bar-fill"
                      style={{ width: `${row.total ? Math.min(100, Math.round((row.applied / row.total) * 100)) : 0}%` }}
                    />
                  </span>
                </td>
              </tr>
            ));
          })}
        </tbody>
      </table>
    </div>
  );
}
