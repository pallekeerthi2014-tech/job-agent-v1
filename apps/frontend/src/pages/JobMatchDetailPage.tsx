import { useCallback, useEffect, useRef, useState } from "react";
import { JobCard } from "../components/JobCard";
import { apiClient } from "../api/client";
import type { Candidate, Job, Match, TailoredResumeRead, TailoredResumeReadWithFlags } from "../types";

type JobMatchDetailPageProps = {
  match: Match | null;
  candidate: Candidate | null;
  job: Job | null;
  busy: boolean;
  onMarkApplied: () => Promise<void>;
  onSkip: () => Promise<void>;
};

// ── Resume Tailoring Panel ────────────────────────────────────────────────────

function TailoringPanel({ job, candidate }: { job: Job; candidate: Candidate }) {
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [record, setRecord] = useState<TailoredResumeRead | null>(null);
  const [flaggedSkills, setFlaggedSkills] = useState<string[]>([]);
  const [confirmSkillsOpen, setConfirmSkillsOpen] = useState(false);
  const [history, setHistory] = useState<TailoredResumeRead[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const hasMasterDocx = Boolean(
    candidate.resume_filename && candidate.resume_filename.toLowerCase().endsWith(".docx")
  );

  // Load history on mount
  useEffect(() => {
    if (!candidate.id || !job.id) return;
    setHistoryLoading(true);
    apiClient
      .listTailoredResumes(job.id, candidate.id)
      .then(setHistory)
      .catch(() => setHistory([]))
      .finally(() => setHistoryLoading(false));
  }, [job.id, candidate.id]);

  // Poll while processing
  const startPolling = useCallback(
    (id: number) => {
      if (pollRef.current) clearInterval(pollRef.current);
      pollRef.current = setInterval(async () => {
        try {
          const updated = await apiClient.getTailoredResume(id);
          setRecord(updated);
          if (updated.status === "ready" || updated.status === "error") {
            if (pollRef.current) clearInterval(pollRef.current);
            // Refresh history
            apiClient
              .listTailoredResumes(job.id, candidate.id)
              .then(setHistory)
              .catch(() => {});
          }
        } catch {
          if (pollRef.current) clearInterval(pollRef.current);
        }
      }, 2500);
    },
    [job.id, candidate.id]
  );

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const handleSubmit = async (confirmFlagged?: string[]) => {
    setSubmitting(true);
    setError(null);
    setRecord(null);
    setFlaggedSkills([]);
    try {
      const resp: TailoredResumeReadWithFlags = await apiClient.tailorResume(job.id, {
        candidate_id: candidate.id,
        notes: notes.trim() || null,
        confirm_flagged_skills: confirmFlagged ?? null,
      });
      setRecord(resp);
      if (resp.flagged_skills && resp.flagged_skills.length > 0) {
        setFlaggedSkills(resp.flagged_skills);
        setConfirmSkillsOpen(true);
      } else if (resp.status === "processing" || resp.status === "pending") {
        startPolling(resp.id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setSubmitting(false);
    }
  };

  const handleConfirmSkills = (accepted: string[]) => {
    setConfirmSkillsOpen(false);
    void handleSubmit(accepted);
  };

  const handleSkipSkills = () => {
    setConfirmSkillsOpen(false);
    void handleSubmit([]);
  };

  return (
    <section className="panel tailor-panel">
      <div className="section-heading">
        <h3>✦ AI Resume Tailor</h3>
        <p>Generate a tailored DOCX for <strong>{candidate.name}</strong> targeting this role.</p>
      </div>

      {!hasMasterDocx && (
        <div className="tailor-warning">
          ⚠️ Upload a <strong>.docx</strong> resume for {candidate.name} to enable tailoring.
        </div>
      )}

      {hasMasterDocx && (
        <>
          <div className="tailor-form">
            <label className="tailor-label">Notes / Instructions (optional)</label>
            <textarea
              className="tailor-notes"
              rows={3}
              placeholder="e.g. Emphasise Python skills, remove references to Java, highlight cloud experience..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              disabled={submitting}
            />
            <button
              className="btn btn-primary tailor-btn"
              onClick={() => void handleSubmit()}
              disabled={submitting || !hasMasterDocx}
            >
              {submitting ? "Tailoring…" : "✦ Tailor Resume for This Job"}
            </button>
          </div>

          {/* Flagged skills confirmation dialog */}
          {confirmSkillsOpen && flaggedSkills.length > 0 && (
            <div className="tailor-flagged-box">
              <p className="tailor-flagged-title">⚠️ Unverified Skills Detected</p>
              <p className="tailor-flagged-desc">
                The AI wants to add the following skills that aren't in {candidate.name}'s profile. Confirm which are OK to include:
              </p>
              <ul className="tailor-flagged-list">
                {flaggedSkills.map((s) => (
                  <li key={s} className="tailor-flagged-item">{s}</li>
                ))}
              </ul>
              <div className="tailor-flagged-actions">
                <button className="btn btn-primary btn-sm" onClick={() => handleConfirmSkills(flaggedSkills)}>
                  Add All Anyway
                </button>
                <button className="btn btn-secondary btn-sm" onClick={handleSkipSkills}>
                  Skip These Skills
                </button>
              </div>
            </div>
          )}

          {/* Status display */}
          {record && (
            <div className={`tailor-status tailor-status-${record.status}`}>
              {record.status === "processing" || record.status === "pending" ? (
                <span className="tailor-spinner">⏳ Processing… please wait</span>
              ) : record.status === "ready" ? (
                <div className="tailor-ready">
                  <span>✅ {record.error_message || "Tailored resume ready!"}</span>
                  <a
                    className="btn btn-primary btn-sm"
                    href={apiClient.downloadTailoredResumeUrl(record.id)}
                    download
                    target="_blank"
                    rel="noreferrer"
                  >
                    ⬇ Download Tailored Resume
                  </a>
                </div>
              ) : (
                <div className="tailor-error-box">
                  <span className="tailor-error">❌ {record.error_message || "Tailoring failed"}</span>
                  {(record.error_message || "").toLowerCase().includes("re-upload") && (
                    <p className="tailor-reupload-hint">
                      Go to <strong>Admin → Candidates</strong>, open this candidate's profile, and upload their DOCX resume again.
                    </p>
                  )}
                </div>
              )}
            </div>
          )}

          {error && <p className="tailor-error">{error}</p>}
        </>
      )}

      {/* Tailoring history */}
      {!historyLoading && history.length > 0 && (
        <div className="tailor-history">
          <h4>Previous Tailored Resumes</h4>
          <ul className="tailor-history-list">
            {history.map((r) => (
              <li key={r.id} className="tailor-history-item">
                <span className="tailor-history-date">
                  {new Date(r.created_at).toLocaleDateString()} {new Date(r.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                </span>
                <span className={`tailor-history-status tailor-history-status-${r.status}`}>
                  {r.status}
                </span>
                {r.status === "ready" && (
                  <a
                    className="tailor-history-dl"
                    href={apiClient.downloadTailoredResumeUrl(r.id)}
                    download
                    target="_blank"
                    rel="noreferrer"
                  >
                    ⬇ Download
                  </a>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

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

      {/* Phase 8: AI Resume Tailoring */}
      <TailoringPanel job={job} candidate={candidate} />
    </div>
  );
}
