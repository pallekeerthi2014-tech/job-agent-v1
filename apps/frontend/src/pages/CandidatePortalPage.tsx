/**
 * CandidatePortalPage — self-service portal for candidates.
 *
 * Shows:
 *  • Their top-matched jobs (score + title + company + apply link)
 *  • Their profile summary with inline edit
 *  • Resume upload / download
 */

import { useEffect, useRef, useState } from "react";
import { apiClient, getStoredAccessToken } from "../api/client";
import type { Candidate, Job, Match, User } from "../types";

type PortalView = "matches" | "profile" | "resume";

interface Props {
  currentUser: User;
  onLogout: () => void;
}

export function CandidatePortalPage({ currentUser, onLogout }: Props) {
  const [view, setView] = useState<PortalView>("matches");
  const [profile, setProfile] = useState<Candidate | null>(null);
  const [matches, setMatches] = useState<Match[]>([]);
  const [jobCache, setJobCache] = useState<Map<number, Job>>(new Map());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Profile edit
  const [editMode, setEditMode] = useState(false);
  const [editPhone, setEditPhone] = useState("");
  const [editLocation, setEditLocation] = useState("");
  const [editYears, setEditYears] = useState("");
  const [editWorkAuth, setEditWorkAuth] = useState("");
  const [editSalaryMin, setEditSalaryMin] = useState("");
  const [editSalaryUnit, setEditSalaryUnit] = useState("yearly");

  // Resume
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [resumeBusy, setResumeBusy] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  // ── Load ──────────────────────────────────────────────────────────────────
  useEffect(() => {
    void loadAll();
  }, []);

  async function loadAll() {
    setBusy(true);
    setError(null);
    try {
      const [profileData, matchData] = await Promise.all([
        apiClient.portalGetProfile(),
        apiClient.portalGetMatches({ limit: 50, offset: 0 }),
      ]);
      setProfile(profileData);
      setMatches(matchData.items);

      // Pre-fetch jobs for all matches (batch-style, throttled)
      const uniqueJobIds = [...new Set(matchData.items.map((m) => m.job_id))];
      const jobPairs = await Promise.all(
        uniqueJobIds.map((jid) =>
          apiClient.portalGetJob(jid).then((j) => [jid, j] as [number, Job]).catch(() => null)
        )
      );
      const map = new Map<number, Job>();
      for (const pair of jobPairs) {
        if (pair) map.set(pair[0], pair[1]);
      }
      setJobCache(map);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load portal data");
    } finally {
      setBusy(false);
    }
  }

  // ── Profile edit ─────────────────────────────────────────────────────────
  function startEdit() {
    if (!profile) return;
    setEditPhone(profile.phone ?? "");
    setEditLocation(profile.location ?? "");
    setEditYears(profile.years_experience != null ? String(profile.years_experience) : "");
    setEditWorkAuth(profile.work_authorization ?? "");
    setEditSalaryMin(profile.salary_min != null ? String(profile.salary_min) : "");
    setEditSalaryUnit(profile.salary_unit ?? "yearly");
    setEditMode(true);
  }

  async function saveProfile() {
    setBusy(true);
    setError(null);
    setSuccess(null);
    try {
      const updated = await apiClient.portalUpdateProfile({
        phone: editPhone || null,
        location: editLocation || null,
        years_experience: editYears ? parseInt(editYears, 10) : null,
        work_authorization: editWorkAuth || null,
        salary_min: editSalaryMin ? parseInt(editSalaryMin, 10) : null,
        salary_unit: editSalaryUnit || null,
      });
      setProfile(updated);
      setEditMode(false);
      setSuccess("Profile updated successfully.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update profile");
    } finally {
      setBusy(false);
    }
  }

  // ── Resume upload ─────────────────────────────────────────────────────────
  async function handleResumeUpload() {
    if (!resumeFile) return;
    setResumeBusy(true);
    setError(null);
    setSuccess(null);
    try {
      const updated = await apiClient.portalUploadResume(resumeFile);
      setProfile(updated);
      setResumeFile(null);
      if (fileRef.current) fileRef.current.value = "";
      setSuccess("Resume uploaded successfully. Your match scores will improve on the next daily run.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Resume upload failed");
    } finally {
      setResumeBusy(false);
    }
  }

  // ── Render ────────────────────────────────────────────────────────────────
  const priorityColor = (score: number) => {
    if (score >= 75) return "var(--green-600, #16a34a)";
    if (score >= 50) return "var(--amber-600, #d97706)";
    return "var(--slate-500, #64748b)";
  };

  return (
    <div className="portal-shell">
      {/* ── Header ── */}
      <header className="portal-header">
        <div className="portal-header-brand">
          <span className="portal-logo">TS</span>
          <span className="portal-title">ThinkSuccess — Candidate Portal</span>
        </div>
        <div className="portal-header-actions">
          <span className="portal-welcome">Hi, {currentUser.name}</span>
          <button className="portal-btn-ghost" onClick={onLogout}>Sign out</button>
        </div>
      </header>

      {/* ── Nav ── */}
      <nav className="portal-nav">
        <button
          className={`portal-nav-item${view === "matches" ? " active" : ""}`}
          onClick={() => setView("matches")}
        >
          🎯 My Matches
        </button>
        <button
          className={`portal-nav-item${view === "profile" ? " active" : ""}`}
          onClick={() => setView("profile")}
        >
          👤 My Profile
        </button>
        <button
          className={`portal-nav-item${view === "resume" ? " active" : ""}`}
          onClick={() => setView("resume")}
        >
          📄 Resume{profile?.resume_filename ? " ✓" : ""}
        </button>
      </nav>

      {/* ── Messages ── */}
      {error && <div className="portal-error">{error}</div>}
      {success && <div className="portal-success">{success}</div>}

      {/* ── Content ── */}
      <main className="portal-content">
        {busy && !matches.length && (
          <div className="portal-loading">Loading your portal…</div>
        )}

        {/* ── Matches view ── */}
        {view === "matches" && (
          <section className="portal-section">
            <div className="portal-section-header">
              <h2>Your Top Job Matches</h2>
              <span className="portal-count">{matches.length} jobs found</span>
            </div>

            {matches.length === 0 && !busy && (
              <div className="portal-empty">
                No matches yet. Your recruiter will run the daily pipeline soon — check back tomorrow!
              </div>
            )}

            <div className="portal-match-list">
              {matches.map((match) => {
                const job = jobCache.get(match.job_id);
                const score = Math.round(match.score);
                const applyUrl = job?.canonical_apply_url || job?.apply_url;
                return (
                  <article key={match.id} className="portal-match-card">
                    <div className="portal-match-score" style={{ color: priorityColor(score) }}>
                      {score}<span className="portal-match-score-denom">/100</span>
                    </div>
                    <div className="portal-match-body">
                      <div className="portal-match-title">
                        {job?.title ?? `Job #${match.job_id}`}
                      </div>
                      <div className="portal-match-meta">
                        {job?.company && <span>{job.company}</span>}
                        {job?.location && <span>· {job.location}</span>}
                        {job?.is_remote && <span className="portal-badge-remote">Remote</span>}
                        {job?.employment_type && (
                          <span className="portal-badge-type">{job.employment_type}</span>
                        )}
                      </div>
                      {match.explanation && (
                        <div className="portal-match-explanation">{match.explanation}</div>
                      )}
                      {job?.domain_tags && job.domain_tags.length > 0 && (
                        <div className="portal-tags">
                          {job.domain_tags.slice(0, 4).map((tag) => (
                            <span key={tag} className="portal-tag">{tag}</span>
                          ))}
                        </div>
                      )}
                    </div>
                    <div className="portal-match-actions">
                      {applyUrl ? (
                        <a
                          href={applyUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="portal-btn-apply"
                        >
                          Apply →
                        </a>
                      ) : (
                        <span className="portal-no-link">No apply link</span>
                      )}
                    </div>
                  </article>
                );
              })}
            </div>
          </section>
        )}

        {/* ── Profile view ── */}
        {view === "profile" && profile && (
          <section className="portal-section">
            <div className="portal-section-header">
              <h2>My Profile</h2>
              {!editMode && (
                <button className="portal-btn-secondary" onClick={startEdit}>Edit</button>
              )}
            </div>

            {!editMode ? (
              <div className="portal-profile-grid">
                <ProfileRow label="Name" value={profile.name} />
                <ProfileRow label="Email" value={profile.email ?? "—"} />
                <ProfileRow label="Phone" value={profile.phone ?? "—"} />
                <ProfileRow label="Location" value={profile.location ?? "—"} />
                <ProfileRow label="Work Authorization" value={profile.work_authorization ?? "—"} />
                <ProfileRow label="Years of Experience" value={profile.years_experience != null ? String(profile.years_experience) : "—"} />
                <ProfileRow
                  label="Salary Expectation"
                  value={
                    profile.salary_min
                      ? `$${profile.salary_min.toLocaleString()} / ${profile.salary_unit ?? "year"}`
                      : "—"
                  }
                />
              </div>
            ) : (
              <div className="portal-edit-form">
                <label className="portal-label">
                  Phone
                  <input
                    className="portal-input"
                    value={editPhone}
                    onChange={(e) => setEditPhone(e.target.value)}
                    placeholder="+1 555 000 0000"
                  />
                </label>
                <label className="portal-label">
                  Location
                  <input
                    className="portal-input"
                    value={editLocation}
                    onChange={(e) => setEditLocation(e.target.value)}
                    placeholder="City, State"
                  />
                </label>
                <label className="portal-label">
                  Work Authorization
                  <select
                    className="portal-input"
                    value={editWorkAuth}
                    onChange={(e) => setEditWorkAuth(e.target.value)}
                  >
                    <option value="">— Select —</option>
                    <option>US Citizen</option>
                    <option>Green Card</option>
                    <option>EAD</option>
                    <option>OPT EAD</option>
                    <option>H-1B</option>
                    <option>TN</option>
                    <option>Other</option>
                  </select>
                </label>
                <label className="portal-label">
                  Years of Experience
                  <input
                    className="portal-input"
                    type="number"
                    min="0"
                    max="50"
                    value={editYears}
                    onChange={(e) => setEditYears(e.target.value)}
                    placeholder="0"
                  />
                </label>
                <label className="portal-label">
                  Salary Expectation (min)
                  <input
                    className="portal-input"
                    type="number"
                    min="0"
                    value={editSalaryMin}
                    onChange={(e) => setEditSalaryMin(e.target.value)}
                    placeholder="75000"
                  />
                </label>
                <label className="portal-label">
                  Salary Unit
                  <select
                    className="portal-input"
                    value={editSalaryUnit}
                    onChange={(e) => setEditSalaryUnit(e.target.value)}
                  >
                    <option value="yearly">Yearly</option>
                    <option value="hourly">Hourly</option>
                    <option value="monthly">Monthly</option>
                  </select>
                </label>
                <div className="portal-edit-actions">
                  <button className="portal-btn-primary" onClick={saveProfile} disabled={busy}>
                    {busy ? "Saving…" : "Save Changes"}
                  </button>
                  <button className="portal-btn-ghost" onClick={() => setEditMode(false)}>
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </section>
        )}

        {/* ── Resume view ── */}
        {view === "resume" && (
          <section className="portal-section">
            <div className="portal-section-header">
              <h2>My Resume</h2>
            </div>

            {profile?.resume_filename ? (
              <div className="portal-resume-current">
                <span className="portal-resume-icon">📎</span>
                <span className="portal-resume-name">{profile.resume_filename}</span>
                <a
                  href={`${apiClient.portalResumeUrl()}?t=${getStoredAccessToken()}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="portal-btn-secondary"
                >
                  Download
                </a>
              </div>
            ) : (
              <div className="portal-resume-empty">No resume uploaded yet.</div>
            )}

            <div className="portal-resume-upload">
              <p className="portal-resume-hint">
                Upload your resume to improve your match scores. Supported formats: PDF, DOCX, TXT.
                Our system extracts your skills and experience automatically to find you better job matches.
              </p>
              <input
                ref={fileRef}
                type="file"
                accept=".pdf,.doc,.docx,.txt"
                className="portal-file-input"
                onChange={(e) => setResumeFile(e.target.files?.[0] ?? null)}
              />
              {resumeFile && (
                <div className="portal-file-selected">
                  Selected: <strong>{resumeFile.name}</strong>
                </div>
              )}
              <button
                className="portal-btn-primary"
                onClick={handleResumeUpload}
                disabled={!resumeFile || resumeBusy}
              >
                {resumeBusy ? "Uploading…" : profile?.resume_filename ? "Replace Resume" : "Upload Resume"}
              </button>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

function ProfileRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="portal-profile-row">
      <span className="portal-profile-label">{label}</span>
      <span className="portal-profile-value">{value}</span>
    </div>
  );
}
