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

  return (
    <article className={`job-card ${compact ? "job-card-compact" : ""}`}>
      <div className="job-card-header">
        <div className="job-card-title-block">
          <strong>{job?.title ?? "Unknown job"}</strong>
          <span>{job?.company ?? "Unknown company"}</span>
          <small>
            {job?.source ?? "Unknown source"} • {job?.posted_date ?? "Unspecified"}
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
        jobUrl={job?.apply_url}
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

