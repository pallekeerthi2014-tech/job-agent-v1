import { JobCard } from "../components/JobCard";
import type {
  Candidate,
  DashboardTimeWindow,
  Employee,
  Job,
  Match,
  PageMeta,
  WorkQueueDayStats,
  WorkQueueItem
} from "../types";

// ── Props ─────────────────────────────────────────────────────────────────────

type OperationsDashboardPageProps = {
  // data
  queueItems: WorkQueueItem[];
  meta: PageMeta | null;
  dayStats: WorkQueueDayStats[];
  candidateMap: Map<number, Candidate>;
  employeeMap: Map<number, Employee>;
  jobMap: Map<number, Job>;
  matchMap: Map<number, Match>;
  candidates: Candidate[]; // for candidate filter dropdown
  busyQueueId: number | null;
  currentUserRole: string; // "super_admin" | "employee"
  // filters
  searchTerm: string;
  sourceFilter: string;
  statusFilter: string;
  timeWindow: DashboardTimeWindow;
  dayFilter: string; // "all" | "2026-05-07"
  candidateFilter: number | null;
  // pagination
  page: number;
  pageSize: number;
  // callbacks
  onSearchTermChange: (v: string) => void;
  onSourceFilterChange: (v: string) => void;
  onStatusFilterChange: (v: string) => void;
  onTimeWindowChange: (v: DashboardTimeWindow) => void;
  onDayFilterChange: (v: string) => void;
  onCandidateFilterChange: (v: number | null) => void;
  onPageChange: (p: number) => void;
  onPageSizeChange: (s: number) => void;
  onOpenMatch: (queueItem: WorkQueueItem) => void;
  onMarkApplied: (queueItem: WorkQueueItem) => Promise<void>;
  onSkip: (queueItem: WorkQueueItem) => Promise<void>;
};

const STATUS_OPTIONS = ["all", "pending", "applied", "skipped"];
const TIME_WINDOWS: { value: DashboardTimeWindow; label: string }[] = [
  { value: "48h", label: "48 h" },
  { value: "today", label: "Today" },
  { value: "7d", label: "7 days" },
  { value: "all", label: "All time" }
];
const PAGE_SIZE_OPTIONS = [10, 25, 50];

// ── Main component ─────────────────────────────────────────────────────────────

export function OperationsDashboardPage({
  queueItems,
  meta,
  dayStats,
  candidateMap,
  employeeMap,
  jobMap,
  matchMap,
  candidates,
  busyQueueId,
  currentUserRole,
  searchTerm,
  sourceFilter,
  statusFilter,
  timeWindow,
  dayFilter,
  candidateFilter,
  page,
  pageSize,
  onSearchTermChange,
  onSourceFilterChange,
  onStatusFilterChange,
  onTimeWindowChange,
  onDayFilterChange,
  onCandidateFilterChange,
  onPageChange,
  onPageSizeChange,
  onOpenMatch,
  onMarkApplied,
  onSkip
}: OperationsDashboardPageProps) {
  // Client-side secondary filters (search + source applied within the loaded page)
  const filteredItems = queueItems.filter((item) => {
    const candidate = candidateMap.get(item.candidate_id);
    const employee = employeeMap.get(item.employee_id);
    const job = jobMap.get(item.job_id);
    const haystack = [candidate?.name, employee?.name, job?.title, job?.company, job?.source, item.explanation]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    const matchesSearch = !searchTerm || haystack.includes(searchTerm.trim().toLowerCase());
    const matchesSource = sourceFilter === "all" || job?.source === sourceFilter;
    return matchesSearch && matchesSource;
  });

  const sources = Array.from(
    new Set(queueItems.map((i) => jobMap.get(i.job_id)?.source).filter((v): v is string => Boolean(v)))
  ).sort((a, b) => a.localeCompare(b));

  // Server total from meta (accurate, uncapped)
  const totalJobs = meta?.total ?? 0;
  const pendingCount = meta ? queueItems.filter((i) => i.status === "pending").length : 0;
  const appliedCount = meta ? queueItems.filter((i) => i.status === "applied").length : 0;
  const highPriorityCount = queueItems.filter((i) => i.priority_bucket === "High").length;

  // Pagination
  const totalPages = meta ? Math.ceil(meta.total / pageSize) : 1;
  const startItem = meta ? meta.offset + 1 : 1;
  const endItem = meta ? Math.min(meta.offset + queueItems.length, meta.total) : queueItems.length;

  // Active time window label for list header
  const windowLabel =
    dayFilter !== "all"
      ? `day: ${formatDayLabel(dayFilter)}`
      : TIME_WINDOWS.find((t) => t.value === timeWindow)?.label ?? timeWindow;

  return (
    <section className="dashboard-stack">

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <section className="panel">
        <div className="section-heading">
          <h3>Operations Dashboard</h3>
          <p>Employee jobs · fresh queue · daily recruiting workflow.</p>
        </div>

        {/* Metric cards */}
        <div className="dashboard-metrics">
          <MetricCard label="Total Jobs" subLabel={windowLabel} value={String(totalJobs)} accent="warm" />
          <MetricCard label="Pending" subLabel="needs action" value={String(pendingCount)} accent="neutral" />
          <MetricCard label="Applied" subLabel="this window" value={String(appliedCount)} accent="success" />
          <MetricCard label="High Priority" subLabel="act fast" value={String(highPriorityCount)} accent="warning" />
        </div>
      </section>

      {/* ── 7-day bar chart ─────────────────────────────────────────────────── */}
      <section className="panel">
        <div className="ops-chart-header">
          <div>
            <div className="ops-chart-title">Jobs Ingested · Past 7 Days</div>
            <div className="ops-chart-sub">Click a bar to filter the list to that day</div>
          </div>
          <div className="ops-chart-legend">
            <span><span className="ops-legend-dot ops-legend-blue" />New jobs</span>
            <span><span className="ops-legend-dot ops-legend-green" />Applied</span>
          </div>
        </div>
        <DayStatsChart stats={dayStats} selectedDay={dayFilter} onDayClick={(d) => {
          onDayFilterChange(dayFilter === d ? "all" : d);
          onPageChange(1);
        }} />
      </section>

      {/* ── Filters ─────────────────────────────────────────────────────────── */}
      <section className="panel">
        <div className="ops-filters-row">
          {/* Search */}
          <label className="filter-field ops-search-field">
            <span>Search</span>
            <input
              value={searchTerm}
              onChange={(e) => onSearchTermChange(e.target.value)}
              placeholder="Candidate, company, title, source…"
            />
          </label>

          {/* Time window toggle (only active when no specific day selected) */}
          <div className="filter-field">
            <span>Time window</span>
            <div className="ops-time-toggle">
              {TIME_WINDOWS.map((tw) => (
                <button
                  key={tw.value}
                  className={`ops-time-btn${timeWindow === tw.value && dayFilter === "all" ? " ops-time-btn-active" : ""}`}
                  onClick={() => { onTimeWindowChange(tw.value); onDayFilterChange("all"); onPageChange(1); }}
                >
                  {tw.label}
                </button>
              ))}
            </div>
          </div>

          {/* Source */}
          <label className="filter-field">
            <span>Source</span>
            <select value={sourceFilter} onChange={(e) => onSourceFilterChange(e.target.value)}>
              <option value="all">All sources</option>
              {sources.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </label>

          {/* Status */}
          <label className="filter-field">
            <span>Status</span>
            <select value={statusFilter} onChange={(e) => { onStatusFilterChange(e.target.value); onPageChange(1); }}>
              {STATUS_OPTIONS.map((opt) => (
                <option key={opt} value={opt}>{opt === "all" ? "All statuses" : capitalize(opt)}</option>
              ))}
            </select>
          </label>

          {/* Candidate filter — always visible for super_admin, also visible for employees */}
          <label className="filter-field">
            <span>Candidate</span>
            <select
              value={candidateFilter ?? ""}
              onChange={(e) => { onCandidateFilterChange(e.target.value ? Number(e.target.value) : null); onPageChange(1); }}
            >
              <option value="">All candidates</option>
              {candidates.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </label>
        </div>

        {/* Active day filter chip */}
        {dayFilter !== "all" && (
          <div className="ops-day-chip-row">
            <span className="ops-day-chip">
              Filtered to: <strong>{formatDayLabel(dayFilter)}</strong>
              <button className="ops-day-chip-clear" onClick={() => { onDayFilterChange("all"); onPageChange(1); }}>✕</button>
            </span>
          </div>
        )}
      </section>

      {/* ── Job list ─────────────────────────────────────────────────────────── */}
      <section className="panel ops-list-panel">
        {/* List header */}
        <div className="ops-list-header">
          <strong>
            {totalJobs === 0
              ? "No jobs match these filters"
              : `Showing ${startItem}–${endItem} of ${totalJobs} jobs · ${windowLabel}`}
          </strong>
          <span className="ops-list-meta">sorted by {statusFilter === "pending" ? "priority" : "date"}</span>
        </div>

        {/* Day-grouped rows */}
        {filteredItems.length === 0 ? (
          <div className="empty-state" style={{ minHeight: 120, display: "grid", placeItems: "center" }}>
            <p>No jobs match these filters. Try widening your search or time window.</p>
          </div>
        ) : (
          <div className="ops-job-list">
            {groupByDay(filteredItems).map(([day, items]) => (
              <div key={day}>
                {/* Day separator */}
                <div className="ops-day-sep">
                  <span>{formatDayLabel(day)}</span>
                  <span className="ops-day-sep-chip">{items.length} job{items.length !== 1 ? "s" : ""} · {items.filter(i => i.status === "pending").length} pending</span>
                </div>

                {/* Job rows */}
                {items.map((queueItem) => {
                  const candidate = candidateMap.get(queueItem.candidate_id);
                  const employee = employeeMap.get(queueItem.employee_id);
                  const job = jobMap.get(queueItem.job_id);
                  const match = queueItem.match_id ? matchMap.get(queueItem.match_id) : undefined;
                  const displayMatch: Match = match ?? {
                    id: queueItem.match_id ?? queueItem.id,
                    candidate_id: queueItem.candidate_id,
                    job_id: queueItem.job_id,
                    score: queueItem.score,
                    explanation: queueItem.explanation,
                    status: queueItem.priority_bucket
                  };

                  return (
                    <article key={queueItem.id} className="ops-job-row">
                      {/* Left meta: employee + candidate note */}
                      <div className="ops-job-row-meta">
                        <span className="ops-job-employee">{employee?.name ?? "Unassigned"}</span>
                        {candidate && (
                          <span className="ops-job-candidate">
                            <span className="ops-candidate-dot" />
                            {candidate.name}
                          </span>
                        )}
                        <div className={`queue-status-pill queue-status-${queueItem.status.toLowerCase()}`}>
                          {capitalize(queueItem.status)}
                        </div>
                      </div>

                      {/* Job card */}
                      <div className="ops-job-card-wrap">
                        <JobCard
                          match={displayMatch}
                          candidate={candidate}
                          job={job}
                          compact
                          queueStatus={queueItem.status}
                          disabled={busyQueueId === queueItem.id}
                          onViewJob={() => {
                            if (queueItem.match_id && matchMap.get(queueItem.match_id)) {
                              onOpenMatch(queueItem);
                              return;
                            }
                            if (job?.apply_url) {
                              window.open(job.apply_url, "_blank", "noopener,noreferrer");
                            }
                          }}
                          onApply={() => void onMarkApplied(queueItem)}
                          onSkip={() => void onSkip(queueItem)}
                        />
                      </div>
                    </article>
                  );
                })}
              </div>
            ))}
          </div>
        )}

        {/* Pagination */}
        {meta && meta.total > pageSize && (
          <div className="ops-pagination">
            <span className="ops-page-info">
              {startItem}–{endItem} of {totalJobs}
            </span>

            <div className="ops-page-controls">
              <button
                className="ops-page-btn"
                disabled={page <= 1}
                onClick={() => onPageChange(page - 1)}
              >‹</button>

              {buildPageNumbers(page, totalPages).map((p, i) =>
                p === "…" ? (
                  <span key={`ellipsis-${i}`} className="ops-page-ellipsis">…</span>
                ) : (
                  <button
                    key={p}
                    className={`ops-page-btn${page === p ? " ops-page-btn-active" : ""}`}
                    onClick={() => onPageChange(Number(p))}
                  >
                    {p}
                  </button>
                )
              )}

              <button
                className="ops-page-btn"
                disabled={page >= totalPages}
                onClick={() => onPageChange(page + 1)}
              >›</button>
            </div>

            <div className="ops-per-page">
              <span>Rows:</span>
              <select
                value={pageSize}
                onChange={(e) => { onPageSizeChange(Number(e.target.value)); onPageChange(1); }}
              >
                {PAGE_SIZE_OPTIONS.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
          </div>
        )}
      </section>
    </section>
  );
}

// ── Sub-components ─────────────────────────────────────────────────────────────

type MetricCardProps = {
  label: string;
  subLabel: string;
  value: string;
  accent: "warm" | "neutral" | "success" | "warning";
};

function MetricCard({ label, subLabel, value, accent }: MetricCardProps) {
  return (
    <div className={`metric-card metric-card-${accent}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      <small style={{ color: "var(--brand-muted)", fontSize: "0.78rem" }}>{subLabel}</small>
    </div>
  );
}

type DayStatsChartProps = {
  stats: WorkQueueDayStats[];
  selectedDay: string;
  onDayClick: (day: string) => void;
};

function DayStatsChart({ stats, selectedDay, onDayClick }: DayStatsChartProps) {
  if (stats.length === 0) {
    // Build 7 empty placeholder bars
    const today = new Date();
    const placeholders: WorkQueueDayStats[] = Array.from({ length: 7 }, (_, i) => {
      const d = new Date(today);
      d.setDate(today.getDate() - (6 - i));
      return { date: d.toISOString().slice(0, 10), total: 0, applied: 0, pending: 0 };
    });
    return <DayStatsChart stats={placeholders} selectedDay={selectedDay} onDayClick={onDayClick} />;
  }

  // Ensure exactly 7 days (fill missing)
  const today = new Date();
  const days: WorkQueueDayStats[] = Array.from({ length: 7 }, (_, i) => {
    const d = new Date(today);
    d.setDate(today.getDate() - (6 - i));
    const key = d.toISOString().slice(0, 10);
    return stats.find((s) => s.date === key) ?? { date: key, total: 0, applied: 0, pending: 0 };
  });

  const maxTotal = Math.max(...days.map((d) => d.total), 1);
  const todayKey = today.toISOString().slice(0, 10);

  return (
    <div className="ops-chart-bars">
      {days.map((d) => {
        const isToday = d.date === todayKey;
        const isSelected = selectedDay === d.date;
        const barHeight = Math.max((d.total / maxTotal) * 72, d.total > 0 ? 6 : 2);
        const appliedHeight = d.total > 0 ? (d.applied / d.total) * barHeight : 0;
        const dayLabel = new Date(`${d.date}T12:00:00`).toLocaleDateString(undefined, { weekday: "short" });

        return (
          <div
            key={d.date}
            className={`ops-bar-col${isSelected ? " ops-bar-col-selected" : ""}`}
            onClick={() => onDayClick(d.date)}
            title={`${d.date}: ${d.total} jobs, ${d.applied} applied, ${d.pending} pending`}
          >
            <span className={`ops-bar-count${isToday ? " ops-bar-count-today" : ""}`}>
              {d.total > 0 ? d.total : ""}
            </span>
            <div className="ops-bar-stack">
              <div
                className={`ops-bar-total${isToday ? " ops-bar-today" : ""}`}
                style={{ height: barHeight }}
              />
              {appliedHeight > 0 && (
                <div className="ops-bar-applied" style={{ height: appliedHeight }} />
              )}
            </div>
            <span className={`ops-bar-label${isToday ? " ops-bar-label-today" : ""}`}>
              {isToday ? "Today" : dayLabel}
            </span>
          </div>
        );
      })}
    </div>
  );
}

// ── Helpers ────────────────────────────────────────────────────────────────────

function groupByDay(items: WorkQueueItem[]) {
  const grouped = new Map<string, WorkQueueItem[]>();
  for (const item of items) {
    const key = item.created_at.slice(0, 10);
    const current = grouped.get(key) ?? [];
    current.push(item);
    grouped.set(key, current);
  }
  return Array.from(grouped.entries()).sort(([a], [b]) => b.localeCompare(a));
}

function formatDayLabel(dateStr: string) {
  const d = new Date(`${dateStr}T12:00:00`);
  const today = new Date();
  const yesterday = new Date(today);
  yesterday.setDate(today.getDate() - 1);
  if (dateStr === today.toISOString().slice(0, 10)) return "Today";
  if (dateStr === yesterday.toISOString().slice(0, 10)) return "Yesterday";
  return d.toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" });
}

function capitalize(s: string) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

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
