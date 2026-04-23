import { JobCard } from "../components/JobCard";
import type { Candidate, Job, Match } from "../types";

type EmployeeWorkQueuePageProps = {
  matches: Match[];
  candidateMap: Map<number, Candidate>;
  jobMap: Map<number, Job>;
  busyMatchId: number | null;
  onViewJob: (match: Match) => void;
  onMarkApplied: (match: Match) => Promise<void>;
  onSkip: (match: Match) => Promise<void>;
};

export function EmployeeWorkQueuePage({
  matches,
  candidateMap,
  jobMap,
  busyMatchId,
  onViewJob,
  onMarkApplied,
  onSkip
}: EmployeeWorkQueuePageProps) {
  return (
    <section className="panel">
      <div className="section-heading">
        <h3>Employee Work Queue</h3>
        <p>Operational queue ordered by match quality and priority.</p>
      </div>

      <div className="queue-grid">
        {matches.map((match) => {
          const candidate = candidateMap.get(match.candidate_id);
          const job = jobMap.get(match.job_id);

          return (
            <JobCard
              key={match.id}
              match={match}
              candidate={candidate}
              job={job}
              compact
              disabled={busyMatchId === match.id}
              onViewJob={() => onViewJob(match)}
              onApply={() => void onMarkApplied(match)}
              onSkip={() => void onSkip(match)}
            />
          );
        })}
      </div>
    </section>
  );
}
