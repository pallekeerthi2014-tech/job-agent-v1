/**
 * CandidatePortalPage — modern job-board style portal for candidates.
 *
 * Layout:
 *  • Dark sidebar — profile summary, resume section, quick-edit
 *  • Main area  — job match cards with score badge, filter bar, sort
 */

import { useEffect, useRef, useState } from "react";
import { apiClient, getStoredAccessToken } from "../api/client";
import type { Candidate, Job, Match, User } from "../types";

interface Props {
  currentUser: User;
  onLogout: () => void;
}

type SortKey = "score" | "date" | "title";
type FilterKey = "all" | "high" | "medium" | "low";

// ── Helpers ───────────────────────────────────────────────────────────────────

function scoreColor(score: number) {
  if (score >= 75) return { bg: "#dcfce7", text: "#15803d", border: "#86efac" };
  if (score >= 50) return { bg: "#fef9c3", text: "#854d0e", border: "#fde047" };
  return { bg: "#f1f5f9", text: "#475569", border: "#cbd5e1" };
}

function fmtSalary(min: number | null | undefined, unit: string | null | undefined) {
  if (!min) return null;
  const u = unit ?? "year";
  return `$${min.toLocaleString()} / ${u}`;
}

// ── Profile sidebar ───────────────────────────────────────────────────────────

function ProfileSidebar({
  profile,
  currentUser,
  onLogout,
  onProfileSaved,
}: {
  profile: Candidate | null;
  currentUser: User;
  onLogout: () => void;
  onProfileSaved: (updated: Candidate) => void;
}) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [editing, setEditing] = useState(false);
  const [editPhone, setEditPhone] = useState("");
  const [editLocation, setEditLocation] = useState("");
  const [editYears, setEditYears] = useState("");
  const [editWorkAuth, setEditWorkAuth] = useState("");
  const [editSalaryMin, setEditSalaryMin] = useState("");
  const [editSalaryUnit, setEditSalaryUnit] = useState("yearly");
  const [saveBusy, setSaveBusy] = useState(false);
  const [resumeBusy, setResumeBusy] = useState(false);
  const [sideError, setSideError] = useState<string | null>(null);
  const [sideSuccess, setSideSuccess] = useState<string | null>(null);

  function startEdit() {
    if (!profile) return;
    setEditPhone(profile.phone ?? "");
    setEditLocation(profile.location ?? "");
    setEditYears(profile.years_experience != null ? String(profile.years_experience) : "");
    setEditWorkAuth(profile.work_authorization ?? "");
    setEditSalaryMin(profile.salary_min != null ? String(profile.salary_min) : "");
    setEditSalaryUnit(profile.salary_unit ?? "yearly");
    setSideError(null);
    setSideSuccess(null);
    setEditing(true);
  }

  async function saveProfile() {
    setSaveBusy(true);
    setSideError(null);
    try {
      const updated = await apiClient.portalUpdateProfile({
        phone: editPhone || null,
        location: editLocation || null,
        years_experience: editYears ? parseInt(editYears, 10) : null,
        work_authorization: editWorkAuth || null,
        salary_min: editSalaryMin ? parseInt(editSalaryMin, 10) : null,
        salary_unit: editSalaryUnit || null,
      });
      onProfileSaved(updated);
      setEditing(false);
      setSideSuccess("Profile saved.");
      setTimeout(() => setSideSuccess(null), 3000);
    } catch (e) {
      setSideError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaveBusy(false);
    }
  }

  async function handleResumeUpload(file: File) {
    setResumeBusy(true);
    setSideError(null);
    try {
      const updated = await apiClient.portalUploadResume(file);
      onProfileSaved(updated);
      setSideSuccess("Resume updated!");
      setTimeout(() => setSideSuccess(null), 3000);
    } catch (e) {
      setSideError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setResumeBusy(false);
    }
  }

  const initials = (currentUser.name ?? "?")
    .split(" ")
    .map((w) => w[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  return (
    <aside className="portal-sidebar">
      {/* Avatar + name */}
      <div className="portal-sidebar-hero">
        <div className="portal-avatar">{initials}</div>
        <div className="portal-sidebar-name">{currentUser.name}</div>
        <div className="portal-sidebar-email">{currentUser.email}</div>
      </div>

      {/* Quick stats */}
      {profile && !editing && (
        <div className="portal-sidebar-stats">
          {profile.location && (
            <div className="portal-sidebar-stat">
              <span className="portal-sidebar-stat-icon">📍</span>
              <span>{profile.location}</span>
            </div>
          )}
          {profile.work_authorization && (
            <div className="portal-sidebar-stat">
              <span className="portal-sidebar-stat-icon">🪪</span>
              <span>{profile.work_authorization}</span>
            </div>
          )}
          {profile.years_experience != null && (
            <div className="portal-sidebar-stat">
              <span className="portal-sidebar-stat-icon">💼</span>
              <span>{profile.years_experience} yrs experience</span>
            </div>
          )}
          {fmtSalary(profile.salary_min, profile.salary_unit) && (
            <div className="portal-sidebar-stat">
              <span className="portal-sidebar-stat-icon">💰</span>
              <span>{fmtSalary(profile.salary_min, profile.salary_unit)}</span>
            </div>
          )}
          {profile.phone && (
            <div className="portal-sidebar-stat">
              <span className="portal-sidebar-stat-icon">📞</span>
              <span>{profile.phone}</span>
            </div>
          )}
        </div>
      )}

      {/* Edit form */}
      {editing && (
        <div className="portal-sidebar-edit">
          <label className="portal-sidebar-field">
            <span>Phone</span>
            <input value={editPhone} onChange={(e) => setEditPhone(e.target.value)} placeholder="+1 555 000 0000" />
          </label>
          <label className="portal-sidebar-field">
            <span>Location</span>
            <input value={editLocation} onChange={(e) => setEditLocation(e.target.value)} placeholder="City, State" />
          </label>
          <label className="portal-sidebar-field">
            <span>Work Auth</span>
            <select value={editWorkAuth} onChange={(e) => setEditWorkAuth(e.target.value)}>
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
          <label className="portal-sidebar-field">
            <span>Years Exp.</span>
            <input type="number" min="0" max="50" value={editYears} onChange={(e) => setEditYears(e.target.value)} placeholder="0" />
          </label>
          <label className="portal-sidebar-field">
            <span>Salary Min</span>
            <input type="number" min="0" value={editSalaryMin} onChange={(e) => setEditSalaryMin(e.target.value)} placeholder="75000" />
          </label>
          <label className="portal-sidebar-field">
            <span>Unit</span>
            <select value={editSalaryUnit} onChange={(e) => setEditSalaryUnit(e.target.value)}>
              <option value="yearly">Yearly</option>
              <option value="hourly">Hourly</option>
              <option value="monthly">Monthly</option>
            </select>
          </label>
          <div className="portal-sidebar-edit-actions">
            <button className="portal-sidebar-btn-primary" onClick={saveProfile} disabled={saveBusy}>
              {saveBusy ? "Saving…" : "Save"}
            </button>
            <button className="portal-sidebar-btn-ghost" onClick={() => setEditing(false)}>Cancel</button>
          </div>
        </div>
      )}

      {!editing && (
        <button className="portal-sidebar-btn-outline" onClick={startEdit}>✏ Edit Profile</button>
      )}

      {/* Resume section */}
      <div className="portal-sidebar-resume">
        <div className="portal-sidebar-resume-title">Resume</div>
        {profile?.resume_filename ? (
          <div className="portal-sidebar-resume-file">
            <span className="portal-sidebar-resume-icon">📎</span>
            <span className="portal-sidebar-resume-name" title={profile.resume_filename}>
              {profile.resume_filename.length > 22
                ? profile.resume_filename.slice(0, 20) + "…"
                : profile.resume_filename}
            </span>
            <a
              href={`${apiClient.portalResumeUrl()}?t=${getStoredAccessToken()}`}
              target="_blank"
              rel="noopener noreferrer"
              className="portal-sidebar-btn-ghost"
              style={{ fontSize: "0.75rem", padding: "3px 8px" }}
            >
              ↓
            </a>
          </div>
        ) : (
          <div className="portal-sidebar-resume-empty">No resume yet</div>
        )}
        <input
          ref={fileRef}
          type="file"
          accept=".pdf,.doc,.docx,.txt"
          style={{ display: "none" }}
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) void handleResumeUpload(f);
            if (fileRef.current) fileRef.current.value = "";
          }}
        />
        <button
          className="portal-sidebar-btn-outline"
          style={{ marginTop: 8, width: "100%", fontSize: "0.8rem" }}
          onClick={() => fileRef.current?.click()}
          disabled={resumeBusy}
        >
          {resumeBusy ? "Uploading…" : profile?.resume_filename ? "Replace Resume" : "Upload Resume"}
        </button>
      </div>

      {/* Feedback messages */}
      {sideError && <div className="portal-sidebar-error">{sideError}</div>}
      {sideSuccess && <div className="portal-sidebar-success">{sideSuccess}</div>}

      {/* Sign out */}
      <button className="portal-sidebar-signout" onClick={onLogout}>Sign out</button>
    </aside>
  );
}

// ── Job match card ────────────────────────────────────────────────────────────

function JobCard({ match, job }: { match: Match; job: Job | undefined }) {
  const score = Math.round(match.score);
  const sc = scoreColor(score);
  const applyUrl = job?.canonical_apply_url ?? job?.apply_url;

  return (
    <article className="portal-job-card">
      {/* Score badge */}
      <div
        className="portal-job-score"
        style={{ background: sc.bg, color: sc.text, border: `1px solid ${sc.border}` }}
      >
        {score}
        <span className="portal-job-score-denom">/100</span>
      </div>

      {/* Content */}
      <div className="portal-job-body">
        <div className="portal-job-title">
          {job?.title ?? `Job #${match.job_id}`}
        </div>
        <div className="portal-job-meta">
          {job?.company && <span className="portal-job-company">{job.company}</span>}
          {job?.location && <span className="portal-job-location">· {job.location}</span>}
        </div>

        {/* Badges row */}
        <div className="portal-job-badges">
          {job?.is_remote && <span className="portal-badge portal-badge-remote">Remote</span>}
          {job?.employment_type && <span className="portal-badge portal-badge-type">{job.employment_type}</span>}
          {job?.salary_min && (
            <span className="portal-badge portal-badge-salary">
              ${(job.salary_min / 1000).toFixed(0)}k{job.salary_max ? `–$${(job.salary_max / 1000).toFixed(0)}k` : "+"}
            </span>
          )}
        </div>

        {/* Tags */}
        {job?.domain_tags && job.domain_tags.length > 0 && (
          <div className="portal-job-tags">
            {job.domain_tags.slice(0, 5).map((tag) => (
              <span key={tag} className="portal-job-tag">{tag}</span>
            ))}
          </div>
        )}

        {/* Match explanation */}
        {match.explanation && (
          <div className="portal-job-explanation">{match.explanation}</div>
        )}
      </div>

      {/* Apply CTA */}
      <div className="portal-job-actions">
        {applyUrl ? (
          <a href={applyUrl} target="_blank" rel="noopener noreferrer" className="portal-btn-apply">
            Apply →
          </a>
        ) : (
          <span className="portal-no-link">No link</span>
        )}
      </div>
    </article>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export function CandidatePortalPage({ currentUser, onLogout }: Props) {
  const [profile, setProfile] = useState<Candidate | null>(null);
  const [matches, setMatches] = useState<Match[]>([]);
  const [jobCache, setJobCache] = useState<Map<number, Job>>(new Map());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filter + sort
  const [filterKey, setFilterKey] = useState<FilterKey>("all");
  const [sortKey, setSortKey] = useState<SortKey>("score");
  const [search, setSearch] = useState("");

  useEffect(() => { void loadAll(); }, []);

  async function loadAll() {
    setBusy(true);
    setError(null);
    try {
      const [profileData, matchData] = await Promise.all([
        apiClient.portalGetProfile(),
        apiClient.portalGetMatches({ limit: 100, offset: 0 }),
      ]);
      setProfile(profileData);
      setMatches(matchData.items);

      const uniqueJobIds = [...new Set(matchData.items.map((m) => m.job_id))];
      const pairs = await Promise.all(
        uniqueJobIds.map((jid) =>
          apiClient.portalGetJob(jid).then((j) => [jid, j] as [number, Job]).catch(() => null)
        )
      );
      const map = new Map<number, Job>();
      for (const pair of pairs) { if (pair) map.set(pair[0], pair[1]); }
      setJobCache(map);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load portal data");
    } finally {
      setBusy(false);
    }
  }

  // Apply filter + search + sort
  const filtered = matches
    .filter((m) => {
      if (filterKey === "high") return m.score >= 75;
      if (filterKey === "medium") return m.score >= 50 && m.score < 75;
      if (filterKey === "low") return m.score < 50;
      return true;
    })
    .filter((m) => {
      if (!search.trim()) return true;
      const q = search.toLowerCase();
      const job = jobCache.get(m.job_id);
      return (
        job?.title?.toLowerCase().includes(q) ||
        job?.company?.toLowerCase().includes(q) ||
        job?.location?.toLowerCase().includes(q) ||
        job?.domain_tags?.some((t) => t.toLowerCase().includes(q))
      );
    })
    .sort((a, b) => {
      if (sortKey === "score") return b.score - a.score;
      if (sortKey === "title") {
        const ta = jobCache.get(a.job_id)?.title ?? "";
        const tb = jobCache.get(b.job_id)?.title ?? "";
        return ta.localeCompare(tb);
      }
      // date: use match id as proxy (higher id = more recent)
      return b.id - a.id;
    });

  const highCount = matches.filter((m) => m.score >= 75).length;
  const medCount  = matches.filter((m) => m.score >= 50 && m.score < 75).length;
  const lowCount  = matches.filter((m) => m.score < 50).length;

  return (
    <div className="portal-v2-shell">
      {/* ── Top bar ── */}
      <header className="portal-v2-topbar">
        <div className="portal-v2-brand">
          <img src="/brand/think-success-logo.jpg" alt="ThinkSuccess" className="portal-v2-logo" />
          <span className="portal-v2-brand-name">ThinkSuccess Portal</span>
        </div>
        <div className="portal-v2-topbar-right">
          <span className="portal-v2-greeting">Hi, {currentUser.name.split(" ")[0]} 👋</span>
        </div>
      </header>

      <div className="portal-v2-body">
        {/* ── Sidebar ── */}
        <ProfileSidebar
          profile={profile}
          currentUser={currentUser}
          onLogout={onLogout}
          onProfileSaved={setProfile}
        />

        {/* ── Main content ── */}
        <main className="portal-v2-main">
          {error && <div className="portal-error" style={{ marginBottom: 16 }}>{error}</div>}

          {/* Section header */}
          <div className="portal-v2-section-header">
            <div>
              <h2 className="portal-v2-section-title">Your Job Matches</h2>
              <p className="portal-v2-section-sub">
                {busy ? "Loading…" : `${matches.length} matches found for you`}
              </p>
            </div>
          </div>

          {/* Filter chips */}
          <div className="portal-v2-filters">
            {([
              ["all",    `All (${matches.length})`],
              ["high",   `High Match (${highCount})`],
              ["medium", `Good Match (${medCount})`],
              ["low",    `Fair Match (${lowCount})`],
            ] as [FilterKey, string][]).map(([key, label]) => (
              <button
                key={key}
                className={`portal-v2-filter-chip${filterKey === key ? " active" : ""}`}
                onClick={() => setFilterKey(key)}
              >
                {label}
              </button>
            ))}

            {/* Search */}
            <div className="portal-v2-search-wrap">
              <span className="portal-v2-search-icon">🔍</span>
              <input
                className="portal-v2-search"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search title, company, tag…"
              />
              {search && (
                <button className="portal-v2-search-clear" onClick={() => setSearch("")}>✕</button>
              )}
            </div>

            {/* Sort */}
            <div className="portal-v2-sort-wrap">
              <span style={{ fontSize: "0.8rem", color: "var(--brand-muted)", whiteSpace: "nowrap" }}>Sort:</span>
              <select
                className="portal-v2-sort-select"
                value={sortKey}
                onChange={(e) => setSortKey(e.target.value as SortKey)}
              >
                <option value="score">Best Match</option>
                <option value="date">Newest First</option>
                <option value="title">Title A–Z</option>
              </select>
            </div>
          </div>

          {/* Cards grid */}
          {busy && matches.length === 0 ? (
            <div className="portal-v2-loading">
              <div className="portal-v2-spinner" />
              <span>Finding your matches…</span>
            </div>
          ) : filtered.length === 0 ? (
            <div className="portal-v2-empty">
              {matches.length === 0
                ? "No matches yet. Your recruiter will run the daily pipeline soon — check back tomorrow!"
                : "No jobs match your current filters. Try adjusting the search or filter."}
            </div>
          ) : (
            <div className="portal-v2-cards">
              {filtered.map((match) => (
                <JobCard key={match.id} match={match} job={jobCache.get(match.job_id)} />
              ))}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
