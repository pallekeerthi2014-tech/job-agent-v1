import { MatchScoreBadge } from "./MatchScoreBadge";
import type { Candidate, Job, Match } from "../types";

type MatchTableProps = {
  matches: Match[];
  candidateMap: Map<number, Candidate>;
  jobMap: Map<number, Job>;
  onSelectMatch: (match: Match) => void;
};

export function MatchTable({ matches, candidateMap, jobMap, onSelectMatch }: MatchTableProps) {
  return (
    <section className="panel">
      <div className="section-heading">
        <h3>Candidate List</h3>
        <p>Top matching opportunities with source, score, and analyst context.</p>
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Candidate</th>
              <th>Score</th>
              <th>Job</th>
              <th>Company</th>
              <th>Source</th>
              <th>Posted</th>
              <th>Priority</th>
            </tr>
          </thead>
          <tbody>
            {matches.map((match) => {
              const candidate = candidateMap.get(match.candidate_id);
              const job = jobMap.get(match.job_id);
              const priorityLabel = match.status ?? "Low";

              return (
                <tr key={match.id} onClick={() => onSelectMatch(match)} className="clickable-row">
                  <td>{candidate?.name ?? `Candidate ${match.candidate_id}`}</td>
                  <td>
                    <MatchScoreBadge score={match.score} priorityLabel={priorityLabel} />
                  </td>
                  <td>{job?.title ?? `Job ${match.job_id}`}</td>
                  <td>{job?.company ?? "Unknown company"}</td>
                  <td>{job?.source ?? "Unknown source"}</td>
                  <td>{job?.posted_date ?? "Unspecified"}</td>
                  <td>{priorityLabel}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

