type MatchScoreBadgeProps = {
  score: number;
  priorityLabel: string;
};

export function MatchScoreBadge({ score, priorityLabel }: MatchScoreBadgeProps) {
  return (
    <div className={`score-badge score-${priorityLabel.toLowerCase()}`}>
      <strong>{score.toFixed(1)}</strong>
      <span>{priorityLabel}</span>
    </div>
  );
}

