import { JobCard } from "../components/JobCard";
import type { Candidate, Job, Match } from "../types";

type JobMatchDetailPageProps = {
  match: Match | null;
  candidate: Candidate | null;
  job: Job | null;
  busy: boolean;
  onMarkApplied: () => Promise<void>;
  onSkip: () => Promise<void>;
};

export function JobMatchDetailPage({
  match,
  candidate,
  job,
  busy,
  onMarkApplied,
  onSkip
}: JobMatchDetailPageProps) {
  if (!match || !candidate || !job) {
    return (
      <section className="panel empty-state">
        <h3>Job Match Detail</h3>
        <p>Select a match from the list or work queue to inspect scoring and next actions.</p>
      </section>
    );
  }

  return (
    <div className="detail-grid">
      <section className="panel">
        <p className="eyebrow">Job Match Detail</p>
        <JobCard
          match={match}
          candidate={candidate}
          job={job}
          disabled={busy}
          onViewJob={() => window.open(job.apply_url ?? "#", "_blank", "noopener,noreferrer")}
          onApply={() => void onMarkApplied()}
          onSkip={() => void onSkip()}
        />
      </section>

      <section className="panel">
        <div className="section-heading">
          <h3>Score Breakdown</h3>
          <p>Weighted sub-scores behind the recommendation.</p>
        </div>

        <div className="score-grid">
          <div className="score-row"><span>Title Match</span><strong>{match.title_score?.toFixed(1) ?? "0.0"}/25</strong></div>
          <div className="score-row"><span>Domain Match</span><strong>{match.domain_score?.toFixed(1) ?? "0.0"}/20</strong></div>
          <div className="score-row"><span>Skills Match</span><strong>{match.skills_score?.toFixed(1) ?? "0.0"}/20</strong></div>
          <div className="score-row"><span>Experience Fit</span><strong>{match.experience_score?.toFixed(1) ?? "0.0"}/10</strong></div>
          <div className="score-row"><span>Employment Fit</span><strong>{match.employment_preference_score?.toFixed(1) ?? "0.0"}/10</strong></div>
          <div className="score-row"><span>Visa Fit</span><strong>{match.visa_score?.toFixed(1) ?? "0.0"}/10</strong></div>
          <div className="score-row"><span>Remote / Location Fit</span><strong>{match.location_score?.toFixed(1) ?? "0.0"}/5</strong></div>
        </div>

        <div className="explanation-block">
          <h4>Explanation</h4>
          <p>{match.explanation ?? "No explanation available yet."}</p>
        </div>
      </section>

      {/* Phase 2: Job intelligence panel — domain tags, keywords, visa hints */}
      <section className="panel">
        <div className="section-heading">
          <h3>Job Intelligence</h3>
          <p>Tags and signals extracted from the live job posting.</p>
        </div>

        {(job.domain_tags?.length ?? 0) > 0 && (
          <div className="intel-group">
            <h4>Domain Tags</h4>
            <div className="job-tags">
              {job.domain_tags.map((tag) => (
                <span key={tag} className="job-tag job-tag-domain">{tag}</span>
              ))}
            </div>
          </div>
        )}

        {(job.keywords_extracted?.length ?? 0) > 0 && (
          <div className="intel-group">
            <h4>Keywords Extracted</h4>
            <div className="job-tags">
              {job.keywords_extracted.map((kw) => (
                <span key={kw} className="job-tag">{kw}</span>
              ))}
            </div>
          </div>
        )}

        {(job.visa_hints?.length ?? 0) > 0 && (
          <div className="intel-group">
            <h4>Visa / Authorization Signals</h4>
            <div className="job-tags">
              {job.visa_hints.map((hint) => (
                <span key={hint} className="job-tag job-tag-visa">{hint}</span>
              ))}
            </div>
          </div>
        )}

        {(job.domain_tags?.length ?? 0) === 0 &&
          (job.keywords_extracted?.length ?? 0) === 0 &&
          (job.visa_hints?.length ?? 0) === 0 && (
            <p className="intel-empty">No signals extracted yet — run the pipeline to populate tags.</p>
        )}

        {(job.apply_url || job.canonical_apply_url) && (
          <div className="intel-group">
            <a
              className="link-button apply-now-button"
              href={job.apply_url ?? job.canonical_apply_url ?? "#"}
              target="_blank"
              rel="noreferrer"
            >
              ↗ Apply Now on {job.company}
            </a>
          </div>
        )}
      </section>
    </div>
  );
}
