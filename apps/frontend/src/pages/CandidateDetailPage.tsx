import { MatchScoreBadge } from "../components/MatchScoreBadge";
import type { Application, Candidate, Job, Match } from "../types";

type CandidateDetailPageProps = {
  candidate: Candidate | null;
  matches: Match[];
  jobMap: Map<number, Job>;
  applications: Application[];
  onSelectMatch: (match: Match) => void;
};

export function CandidateDetailPage({
  candidate,
  matches,
  jobMap,
  applications,
  onSelectMatch
}: CandidateDetailPageProps) {
  if (!candidate) {
    return (
      <section className="panel empty-state">
        <h3>Candidate Detail</h3>
        <p>Select a candidate from the filters or pick a match from the list to inspect their details.</p>
      </section>
    );
  }

  return (
    <div className="detail-grid">
      <section className="panel">
        <div className="section-heading">
          <h3>{candidate.name}</h3>
          <p>
            {candidate.work_authorization ?? "Authorization unspecified"} • {candidate.years_experience ?? 0} years
            experience
          </p>
        </div>

        <div className="stack-list">
          <div className="metric-row">
            <span>Salary floor</span>
            <strong>
              {candidate.salary_min ? `${candidate.salary_min.toLocaleString()} ${candidate.salary_unit ?? ""}` : "N/A"}
            </strong>
          </div>
          <div className="metric-row">
            <span>Status</span>
            <strong>{candidate.active ? "Active" : "Inactive"}</strong>
          </div>
          <div className="metric-row">
            <span>Applications</span>
            <strong>{applications.length}</strong>
          </div>
        </div>
      </section>

      <section className="panel">
        <div className="section-heading">
          <h3>Candidate Match Detail</h3>
          <p>Current job matches for this candidate.</p>
        </div>

        <ul className="match-list">
          {matches.map((match) => {
            const job = jobMap.get(match.job_id);
            const priorityLabel = match.status ?? "Low";

            return (
              <li key={match.id} className="match-card" onClick={() => onSelectMatch(match)}>
                <div className="match-card-header">
                  <div>
                    <strong>{job?.title ?? "Unknown job"}</strong>
                    <span>
                      {job?.company ?? "Unknown company"} • {job?.source ?? "Unknown source"}
                    </span>
                  </div>
                  <MatchScoreBadge score={match.score} priorityLabel={priorityLabel} />
                </div>
                <p>{match.explanation ?? "No explanation available yet."}</p>
              </li>
            );
          })}
        </ul>
      </section>
    </div>
  );
}

