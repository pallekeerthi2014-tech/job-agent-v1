type MatchActionsProps = {
  jobUrl?: string | null;
  onViewJob: () => void;
  onMarkApplied: () => void;
  onSkip: () => void;
  disabled?: boolean;
};

export function MatchActions({ jobUrl, onViewJob, onMarkApplied, onSkip, disabled }: MatchActionsProps) {
  return (
    <div className="action-row">
      <button className="secondary-button" onClick={onViewJob}>
        View Job
      </button>
      {jobUrl ? (
        <a className="link-button" href={jobUrl} target="_blank" rel="noreferrer">
          Open Job Link
        </a>
      ) : null}
      <button className="primary-button" onClick={onMarkApplied} disabled={disabled}>
        Mark Applied
      </button>
      <button className="ghost-button" onClick={onSkip} disabled={disabled}>
        Skip
      </button>
    </div>
  );
}
