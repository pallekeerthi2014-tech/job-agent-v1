import { JobCard } from "../components/JobCard";
import type { Candidate, Employee, Job, Match, WorkQueueItem } from "../types";

type OperationsDashboardPageProps = {
  queueItems: WorkQueueItem[];
  candidateMap: Map<number, Candidate>;
  employeeMap: Map<number, Employee>;
  jobMap: Map<number, Job>;
  matchMap: Map<number, Match>;
  busyQueueId: number | null;
  searchTerm: string;
  sourceFilter: string;
  statusFilter: string;
  dayFilter: string;
  onSearchTermChange: (value: string) => void;
  onSourceFilterChange: (value: string) => void;
  onStatusFilterChange: (value: string) => void;
  onDayFilterChange: (value: string) => void;
  onOpenMatch: (queueItem: WorkQueueItem) => void;
  onMarkApplied: (queueItem: WorkQueueItem) => Promise<void>;
  onSkip: (queueItem: WorkQueueItem) => Promise<void>;
};

const STATUS_OPTIONS = ["all", "pending", "applied", "skipped"];

export function OperationsDashboardPage({
  queueItems,
  candidateMap,
  employeeMap,
  jobMap,
  matchMap,
  busyQueueId,
  searchTerm,
  sourceFilter,
  statusFilter,
  dayFilter,
  onSearchTermChange,
  onSourceFilterChange,
  onStatusFilterChange,
  onDayFilterChange,
  onOpenMatch,
  onMarkApplied,
  onSkip
}: OperationsDashboardPageProps) {
  const sources = Array.from(
    new Set(queueItems.map((queueItem) => jobMap.get(queueItem.job_id)?.source).filter((value): value is string => Boolean(value)))
  ).sort((left, right) => left.localeCompare(right));

  const days = Array.from(new Set(queueItems.map((queueItem) => toDayKey(queueItem.created_at)))).sort((left, right) =>
    right.localeCompare(left)
  );

  const filteredQueueItems = queueItems.filter((queueItem) => {
    const candidate = candidateMap.get(queueItem.candidate_id);
    const employee = employeeMap.get(queueItem.employee_id);
    const job = jobMap.get(queueItem.job_id);
    const haystack = [
      candidate?.name,
      employee?.name,
      job?.title,
      job?.company,
      job?.source,
      queueItem.explanation
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();

    const matchesSearch = !searchTerm || haystack.includes(searchTerm.trim().toLowerCase());
    const matchesSource = sourceFilter === "all" || job?.source === sourceFilter;
    const matchesStatus = statusFilter === "all" || queueItem.status.toLowerCase() === statusFilter;
    const matchesDay = dayFilter === "all" || toDayKey(queueItem.created_at) === dayFilter;

    return matchesSearch && matchesSource && matchesStatus && matchesDay;
  });

  const groupedQueueItems = groupByDay(filteredQueueItems);
  const pendingCount = filteredQueueItems.filter((queueItem) => queueItem.status === "pending").length;
  const appliedCount = filteredQueueItems.filter((queueItem) => queueItem.status === "applied").length;
  const highPriorityCount = filteredQueueItems.filter((queueItem) => queueItem.priority_bucket === "High").length;

  return (
    <section className="dashboard-stack">
      <section className="panel">
        <div className="section-heading">
          <h3>Employee Jobs Dashboard</h3>
          <p>One place for fresh analyst-role jobs, direct links, and daily completion workflow.</p>
        </div>

        <div className="dashboard-metrics">
          <MetricCard label="Visible Jobs" value={String(filteredQueueItems.length)} accent="warm" />
          <MetricCard label="Pending" value={String(pendingCount)} accent="neutral" />
          <MetricCard label="Applied" value={String(appliedCount)} accent="success" />
          <MetricCard label="High Priority" value={String(highPriorityCount)} accent="warning" />
        </div>

        <div className="dashboard-filters">
          <label className="filter-field">
            <span>Search</span>
            <input
              value={searchTerm}
              onChange={(event) => onSearchTermChange(event.target.value)}
              placeholder="Search candidate, company, title, or source"
            />
          </label>

          <label className="filter-field">
            <span>Source</span>
            <select value={sourceFilter} onChange={(event) => onSourceFilterChange(event.target.value)}>
              <option value="all">All sources</option>
              {sources.map((source) => (
                <option key={source} value={source}>
                  {source}
                </option>
              ))}
            </select>
          </label>

          <label className="filter-field">
            <span>Status</span>
            <select value={statusFilter} onChange={(event) => onStatusFilterChange(event.target.value)}>
              {STATUS_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {option === "all" ? "All statuses" : capitalize(option)}
                </option>
              ))}
            </select>
          </label>

          <label className="filter-field">
            <span>Queue Day</span>
            <select value={dayFilter} onChange={(event) => onDayFilterChange(event.target.value)}>
              <option value="all">All queue days</option>
              {days.map((day) => (
                <option key={day} value={day}>
                  {formatDayLabel(day)}
                </option>
              ))}
            </select>
          </label>
        </div>
      </section>

      {filteredQueueItems.length === 0 ? (
        <section className="panel empty-state">
          <h3>No jobs match these filters</h3>
          <p>Try widening the employee, candidate, source, or status filters to bring more jobs into view.</p>
        </section>
      ) : null}

      {groupedQueueItems.map(([day, items]) => (
        <section key={day} className="panel">
          <div className="section-heading section-heading-inline">
            <div>
              <h3>{formatDayLabel(day)}</h3>
              <p>{items.length} jobs queued for employee review on this day.</p>
            </div>
            <div className="day-summary-chip">{items.filter((item) => item.status === "pending").length} pending</div>
          </div>

          <div className="queue-grid">
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
                <article key={queueItem.id} className="queue-item-shell">
                  <div className="queue-item-meta">
                    <div>
                      <strong>{employee?.name ?? "Unassigned employee"}</strong>
                      <span>
                        Queue status: <b>{capitalize(queueItem.status)}</b>
                      </span>
                    </div>
                    <div className={`queue-status-pill queue-status-${queueItem.status.toLowerCase()}`}>
                      {capitalize(queueItem.status)}
                    </div>
                  </div>

                  <JobCard
                    match={displayMatch}
                    candidate={candidate}
                    job={job}
                    compact
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
                </article>
              );
            })}
          </div>
        </section>
      ))}
    </section>
  );
}

type MetricCardProps = {
  label: string;
  value: string;
  accent: "warm" | "neutral" | "success" | "warning";
};

function MetricCard({ label, value, accent }: MetricCardProps) {
  return (
    <div className={`metric-card metric-card-${accent}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function groupByDay(queueItems: WorkQueueItem[]) {
  const grouped = new Map<string, WorkQueueItem[]>();
  for (const queueItem of queueItems) {
    const key = toDayKey(queueItem.created_at);
    const current = grouped.get(key) ?? [];
    current.push(queueItem);
    grouped.set(key, current);
  }

  return Array.from(grouped.entries()).sort((left, right) => right[0].localeCompare(left[0]));
}

function toDayKey(value: string) {
  return value.slice(0, 10);
}

function formatDayLabel(value: string) {
  const parsed = new Date(`${value}T00:00:00`);
  return parsed.toLocaleDateString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    year: "numeric"
  });
}

function capitalize(value: string) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}
