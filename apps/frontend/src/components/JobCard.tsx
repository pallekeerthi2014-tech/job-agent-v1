import { MatchActions } from "./MatchActions";
import { MatchScoreBadge } from "./MatchScoreBadge";
import type { Candidate, Job, Match } from "../types";

type JobCardProps = {
  match: Match;
  candidate?: Candidate | null;
  job?: Job | null;
  disabled?: boolean;
  compact?: boolean;
  onViewJob: () => void;
  onApply: () => void;
  onSkip: () => void;
};

/** Sources that indicate a live-fetched job (Phase 2 feeds) */
const LIVE_SOURCES = ["indeed", "dice", "remoteok", "usajobs", "live_feed"];

function isLiveSource(source?: string | null): boolean {
  if (!source) return false;
  const lower = source.toLowerCase();
  return LIVE_SOURCES.some((s) => lower.includes(s));
}

function sourceLabel(source?: string | null): string {
  if (!source) return "Unknown source";
  const lower = source.toLowerCase();
  if (lower.includes("indeed")) return "Indeed";
  if (lower.includes("dice")) return "Dice";
  if (lower.includes("remoteok")) return "RemoteOK";
  if (lower.includes("usajobs")) return "USAJobs";
  return source;
}

export function JobCard({
  match,
  candidate,
  job,
  disabled,
  compact = false,
  onViewJob,
  onApply,
  onSkip
}: JobCardProps) {
  const priorityLabel = match.status ?? "Low";
  const scorePercent = Math.max(0, Math.min(100, match.score));
  const reasons = buildWhyMatchedBullets(match, candidate, job);
  const live = isLiveSource(job?.source);
  const applyUrl = job?.apply_url ?? job?.canonical_apply_url;

  // Show a concise set of tags: domain first, then keywords (cap at 6 total)
  const allTags = [
    ...(job?.domain_tags ?? []),
    ...(job?.keywords_extracted ?? []).slice(0, 4),
  ].slice(0, 6);

  return (
    <article className={`job-card ${compact ? "job-card-compact" : ""}`}>
      <div className="job-card-header">
        <div className="job-card-title-block">
          <strong>{job?.title ?? "Unknown job"}</strong>
          <span>{job?.company ?? "Unknown company"}</span>
          <small>
            <span className={`source-label${live ? " source-label-live" : ""}`}>
              {live && <span className="live-dot" aria-hidden="true" />}
              {sourceLabel(job?.source)}
            </span>
            {" "}• {job?.posted_date ?? "Unspecified"}
            {job?.is_remote && <span className="remote-pill">Remote</span>}
          </small>
        </div>
        <MatchScoreBadge score={match.score} priorityLabel={priorityLabel} />
      </div>

      <div className="score-progress-shell" aria-label="Match score progress">
        <div className="score-progress-track">
          <div className={`score-progress-fill score-${priorityLabel.toLowerCase()}`} style={{ width: `${scorePercent}%` }} />
        </div>
        <span>{scorePercent.toFixed(0)}%</span>
      </div>

      {candidate ? <div className="job-card-candidate">{candidate.name}</div> : null}

      {allTags.length > 0 && (
        <div className="job-tags">
          {allTags.map((tag) => (
            <span key={tag} className="job-tag">{tag}</span>
          ))}
        </div>
      )}

      <div className="job-card-reasons">
        <h4>Why matched</h4>
        <ul>
          {reasons.map((reason) => (
            <li key={reason}>{reason}</li>
          ))}
        </ul>
      </div>

      <p className="job-card-explanation">{match.explanation ?? "No explanation available yet."}</p>

      <MatchActions
        jobUrl={applyUrl}
        onViewJob={onViewJob}
        onMarkApplied={onApply}
        onSkip={onSkip}
        disabled={disabled}
      />
    </article>
  );
}

function buildWhyMatchedBullets(match: Match, candidate?: Candidate | null, job?: Job | null): string[] {
  const reasons: string[] = [];

  if (candidate) {
    reasons.push(`${candidate.name} brings ${candidate.years_experience ?? 0}+ years of relevant experience.`);
  }
  if (job) {
    reasons.push(`Source: ${job.source}; posted ${job.posted_date ?? "date unavailable"}.`);
  }
  if ((match.title_score ?? 0) > 0) {
    reasons.push(`Title alignment scored ${formatScore(match.title_score, 25)}.`);
  }
  if ((match.domain_score ?? 0) > 0) {
    reasons.push(`Healthcare domain fit scored ${formatScore(match.domain_score, 20)}.`);
  }
  if ((match.skills_score ?? 0) > 0) {
    reasons.push(`Skills and keyword overlap scored ${formatScore(match.skills_score, 20)}.`);
  }
  if ((match.visa_score ?? 0) > 0) {
    reasons.push(`Work authorization fit scored ${formatScore(match.visa_score, 10)}.`);
  }

  return reasons.slice(0, 4);
}

function formatScore(value: number | null | undefined, max: number): string {
  return `${(value ?? 0).toFixed(1)}/${max}`;
}

