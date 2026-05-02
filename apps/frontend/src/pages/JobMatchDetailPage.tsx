import { useState } from "react";
import { apiClient } from "../api/client";
import { JobCard } from "../components/JobCard";
import type { Candidate, Job, Match, ResumeTailoringDraft } from "../types";

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
  const [recruiterContext, setRecruiterContext] = useState("");
  const [tailoringDraft, setTailoringDraft] = useState<ResumeTailoringDraft | null>(null);
  const [selectedSuggestions, setSelectedSuggestions] = useState<Set<string>>(new Set());
  const [confirmedSkills, setConfirmedSkills] = useState<Set<string>>(new Set());
  const [tailoringBusy, setTailoringBusy] = useState(false);
  const [tailoringError, setTailoringError] = useState<string | null>(null);
  const [tailoringSuccess, setTailoringSuccess] = useState<string | null>(null);

  if (!match || !candidate || !job) {
    return (
      <section className="panel empty-state">
        <h3>Job Match Detail</h3>
        <p>Select a match from the list or work queue to inspect scoring and next actions.</p>
      </section>
    );
  }

  const hasDocxResume = candidate.resume_filename?.toLowerCase().endsWith(".docx") ?? false;
  const supportedSuggestions = tailoringDraft?.suggested_edits.filter((item) => item.status === "supported") ?? [];
  const selectedCount = selectedSuggestions.size + confirmedSkills.size;
  const applyUrl = job.apply_url ?? job.canonical_apply_url;

  const groups = new Map<string, typeof supportedSuggestions>();
  for (const suggestion of supportedSuggestions) {
    const list = groups.get(suggestion.section) ?? [];
    list.push(suggestion);
    groups.set(suggestion.section, list);
  }
  const groupedSuggestions = [...groups.entries()];

  async function prepareTailoringDraft() {
    if (!candidate || !job || !match) return;
    setTailoringBusy(true);
    setTailoringError(null);
    setTailoringSuccess(null);
    try {
      const draft = await apiClient.createResumeTailoringDraft({
        candidate_id: candidate.id,
        job_id: job.id,
        match_id: match.id,
        recruiter_context: recruiterContext || null
      });
      setTailoringDraft(draft);
      setSelectedSuggestions(new Set(draft.suggested_edits.filter((item) => item.status === "supported").map((item) => item.id)));
      setConfirmedSkills(new Set());
      setTailoringSuccess("AI suggestions are ready for review.");
    } catch (error) {
      setTailoringError(error instanceof Error ? error.message : "Unable to prepare resume tailoring suggestions.");
    } finally {
      setTailoringBusy(false);
    }
  }

  async function downloadTailoredResume() {
    if (!tailoringDraft) return;
    setTailoringBusy(true);
    setTailoringError(null);
    setTailoringSuccess(null);
    try {
      const { blob, filename } = await apiClient.downloadTailoredResume(tailoringDraft.id, {
        approved_suggestion_ids: [...selectedSuggestions],
        confirmed_skills: [...confirmedSkills]
      });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      setTailoringSuccess("Tailored resume downloaded. Keep the apply link open and move fast.");
    } catch (error) {
      setTailoringError(error instanceof Error ? error.message : "Unable to download tailored resume.");
    } finally {
      setTailoringBusy(false);
    }
  }

  function toggleSuggestion(id: string) {
    const next = new Set(selectedSuggestions);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setSelectedSuggestions(next);
  }

  function toggleSkill(skill: string) {
    const next = new Set(confirmedSkills);
    if (next.has(skill)) next.delete(skill);
    else next.add(skill);
    setConfirmedSkills(next);
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
          onViewJob={() => window.open(applyUrl ?? "#", "_blank", "noopener,noreferrer")}
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

      <section className="panel resume-tailor-panel">
        <div className="section-heading">
          <h3>Tailor Resume</h3>
          <p>Prepare a DOCX resume version for this job while keeping the master resume unchanged.</p>
        </div>

        <div className="resume-tailor-status-grid">
          <div className="score-row"><span>Master Resume</span><strong>{candidate.resume_filename ?? "Not uploaded"}</strong></div>
          <div className="score-row"><span>Apply Link</span><strong>{applyUrl ? "Ready" : "Missing"}</strong></div>
        </div>

        {!hasDocxResume ? (
          <div className="resume-tailor-warning">
            Upload a DOCX master resume for {candidate.name} before generating a tailored Word document.
          </div>
        ) : (
          <>
            <label className="resume-tailor-label">
              Recruiter or email context
              <textarea
                className="resume-tailor-textarea"
                value={recruiterContext}
                onChange={(event) => setRecruiterContext(event.target.value)}
                placeholder="Paste recruiter notes like: please add Facets, claims, SQL, UAT, or healthcare EDI experience if true."
                rows={5}
              />
            </label>

            <div className="resume-tailor-actions">
              <button className="primary-button" onClick={() => void prepareTailoringDraft()} disabled={tailoringBusy}>
                {tailoringBusy ? "Preparing..." : tailoringDraft ? "Regenerate Suggestions" : "Generate Suggestions"}
              </button>
              {applyUrl ? (
                <a className="link-button" href={applyUrl} target="_blank" rel="noreferrer">
                  Open Apply Link
                </a>
              ) : null}
            </div>
          </>
        )}

        {tailoringError ? <div className="resume-tailor-error">{tailoringError}</div> : null}
        {tailoringSuccess ? <div className="resume-tailor-success">{tailoringSuccess}</div> : null}

        {tailoringDraft ? (
          <div className="resume-tailor-review">
            {groupedSuggestions.length > 0 ? (
              groupedSuggestions.map(([section, suggestions]) => (
                <div className="resume-tailor-group" key={section}>
                  <h4>{section}</h4>
                  {suggestions.map((suggestion) => (
                    <label className="resume-tailor-suggestion" key={suggestion.id}>
                      <input
                        type="checkbox"
                        checked={selectedSuggestions.has(suggestion.id)}
                        onChange={() => toggleSuggestion(suggestion.id)}
                      />
                      <span>
                        <strong>{suggestion.text}</strong>
                        {suggestion.evidence ? <em>{suggestion.evidence}</em> : null}
                      </span>
                    </label>
                  ))}
                </div>
              ))
            ) : (
              <div className="resume-tailor-warning">
                No supported edits were found. Add recruiter context or update the candidate profile/resume with verified skills.
              </div>
            )}

            {tailoringDraft.skill_gaps.length > 0 ? (
              <div className="resume-tailor-group">
                <h4>Needs Confirmation</h4>
                {tailoringDraft.skill_gaps.map((gap) => (
                  <label className="resume-tailor-gap" key={gap.skill}>
                    <input
                      type="checkbox"
                      checked={confirmedSkills.has(gap.skill)}
                      onChange={() => toggleSkill(gap.skill)}
                    />
                    <span>
                      <strong>{gap.skill}</strong>
                      <em>{gap.reason}</em>
                    </span>
                  </label>
                ))}
              </div>
            ) : null}

            <div className="resume-tailor-actions">
              <button
                className="primary-button"
                onClick={() => void downloadTailoredResume()}
                disabled={tailoringBusy || selectedCount === 0}
              >
                {tailoringBusy ? "Building DOCX..." : "Download Tailored Resume"}
              </button>
              <span className="resume-tailor-count">{selectedCount} selected</span>
            </div>
          </div>
        ) : null}
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
