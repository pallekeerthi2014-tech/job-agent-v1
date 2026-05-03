type MatchActionsProps = {
  jobUrl?: string | null;
  onViewJob: () => void;
  onMarkApplied: () => void;
  onSkip: () => void;
  disabled?: boolean;
  /** Current queue status — changes button appearance when already acted on */
  queueStatus?: string | null;
};

export function MatchActions({ jobUrl, onViewJob, onMarkApplied, onSkip, disabled, queueStatus }: MatchActionsProps) {
  const isApplied = queueStatus === "applied";
  const isSkipped = queueStatus === "skipped";

  return (
    <div className="action-row">
      <button className="secondary-button" onClick={onViewJob}>
        View Job
      </button>
      {jobUrl ? (
        <a className="link-button apply-now-button" href={jobUrl} target="_blank" rel="noreferrer">
          ↗ Apply Now
        </a>
      ) : null}
      <button
        className={isApplied ? "btn-applied-done" : "primary-button"}
        onClick={onMarkApplied}
        disabled={disabled || isApplied}
      >
        {isApplied ? "✅ Applied" : "Mark Applied"}
      </button>
      <button
        className={isSkipped ? "btn-skipped-done" : "ghost-button"}
        onClick={onSkip}
        disabled={disabled || isSkipped}
      >
        {isSkipped ? "Skipped" : "Skip"}
      </button>
    </div>
  );
}
