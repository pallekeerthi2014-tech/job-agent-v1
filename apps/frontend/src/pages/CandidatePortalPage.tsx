import { useEffect, useMemo, useRef, useState } from "react";
import { apiClient, getStoredAccessToken } from "../api/client";
import type { Application, Candidate, CandidatePreference, Job, Match, User } from "../types";

interface Props {
  currentUser: User;
  onLogout: () => void;
}

type SortKey = "score" | "date" | "title";
type FilterKey = "all" | "high" | "saved" | "pending" | "applied";
type PortalTab = "overview" | "matches" | "tracker" | "prep";
const PAGE_SIZE_OPTIONS = [5, 10, 20];

const ROLE_OPTIONS = [
  "Business Analyst",
  "Data Analyst",
  "Healthcare Business Analyst",
  "Product Analyst",
  "Scrum Master",
  "QA Analyst",
];
const WORK_MODE_OPTIONS = ["Remote", "Hybrid", "On-site", "Contract", "Full-time"];
const DOMAIN_OPTIONS = ["Healthcare", "Finance", "Insurance", "SaaS", "Retail", "Government"];

function scoreColor(score: number) {
  if (score >= 80) return { bg: "#dcfce7", text: "#15803d", border: "#86efac" };
  if (score >= 60) return { bg: "#fef9c3", text: "#854d0e", border: "#fde047" };
  return { bg: "#f1f5f9", text: "#475569", border: "#cbd5e1" };
}

function splitList(value: string) {
  return value.split(",").map((item) => item.trim()).filter(Boolean);
}

function toggleValue(values: string[], value: string) {
  return values.includes(value) ? values.filter((item) => item !== value) : [...values, value];
}

function formatDate(value?: string | null) {
  if (!value) return "Recently";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Recently";
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function fmtSalary(min: number | null | undefined, unit: string | null | undefined) {
  if (!min) return null;
  return `$${min.toLocaleString()} / ${unit ?? "year"}`;
}

function truncateText(value: string | null | undefined, max = 150) {
  if (!value) return "";
  return value.length > max ? `${value.slice(0, max).trim()}...` : value;
}

function getApplicationStatus(applicationsByJob: Map<number, Application>, jobId: number) {
  return applicationsByJob.get(jobId)?.status ?? "pending";
}

function isAppliedStatus(status?: string | null) {
  return status === "applied" || status === "interviewing" || status === "offer";
}

function jobSearchText(job: Job | undefined) {
  return [
    job?.title,
    job?.company,
    job?.location,
    job?.employment_type,
    ...(job?.domain_tags ?? []),
    ...(job?.keywords_extracted ?? []),
  ].filter(Boolean).join(" ").toLowerCase();
}

function matchReasons(match: Match, job: Job | undefined, preferences: CandidatePreference | null) {
  const reasons: string[] = [];
  if (match.title_score != null && match.title_score >= 20) reasons.push("Role title aligns");
  if (match.location_score != null && match.location_score > 0) reasons.push("Location preference fits");
  if (match.employment_preference_score != null && match.employment_preference_score > 0) reasons.push("Work mode preference fits");
  if ((match.keyword_match_count ?? 0) > 0) {
    reasons.push(`${match.keyword_match_count}/${match.keyword_match_total ?? "many"} JD keywords found`);
  }
  if (job?.is_remote) reasons.push("Remote-friendly");
  const preferredDomains = preferences?.domain_expertise ?? [];
  if (preferredDomains.some((domain) => job?.domain_tags?.some((tag) => tag.toLowerCase().includes(domain.toLowerCase())))) {
    reasons.push("Industry preference match");
  }
  return reasons.slice(0, 4);
}

function missingKeywords(match: Match, job: Job | undefined, preferences: CandidatePreference | null) {
  const preferred = new Set((preferences?.must_have_keywords ?? []).map((item) => item.toLowerCase()));
  return (job?.keywords_extracted ?? [])
    .filter((keyword) => !preferred.has(keyword.toLowerCase()))
    .slice(0, Math.max((match.keyword_match_total ?? 6) - (match.keyword_match_count ?? 0), 3));
}

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
      setSideSuccess("Resume updated.");
      setTimeout(() => setSideSuccess(null), 3000);
    } catch (e) {
      setSideError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setResumeBusy(false);
    }
  }

  const initials = (currentUser.name ?? "?").split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase();
  const salary = fmtSalary(profile?.salary_min, profile?.salary_unit);

  return (
    <aside className="portal-sidebar">
      <div className="portal-sidebar-hero">
        <div className="portal-avatar">{initials}</div>
        <div className="portal-sidebar-name">{currentUser.name}</div>
        <div className="portal-sidebar-email">{currentUser.email}</div>
      </div>

      {profile && !editing && (
        <div className="portal-sidebar-stats">
          {profile.location && <div className="portal-sidebar-stat"><span>Location</span><strong>{profile.location}</strong></div>}
          {profile.work_authorization && <div className="portal-sidebar-stat"><span>Work auth</span><strong>{profile.work_authorization}</strong></div>}
          {profile.years_experience != null && <div className="portal-sidebar-stat"><span>Experience</span><strong>{profile.years_experience} years</strong></div>}
          {salary && <div className="portal-sidebar-stat"><span>Target</span><strong>{salary}</strong></div>}
          {profile.phone && <div className="portal-sidebar-stat"><span>Phone</span><strong>{profile.phone}</strong></div>}
        </div>
      )}

      {editing && (
        <div className="portal-sidebar-edit">
          <label className="portal-sidebar-field"><span>Phone</span><input value={editPhone} onChange={(e) => setEditPhone(e.target.value)} /></label>
          <label className="portal-sidebar-field"><span>Location</span><input value={editLocation} onChange={(e) => setEditLocation(e.target.value)} /></label>
          <label className="portal-sidebar-field">
            <span>Work authorization</span>
            <select value={editWorkAuth} onChange={(e) => setEditWorkAuth(e.target.value)}>
              <option value="">Select</option>
              <option>US Citizen</option><option>Green Card</option><option>EAD</option><option>OPT EAD</option><option>H-1B</option><option>TN</option><option>Other</option>
            </select>
          </label>
          <label className="portal-sidebar-field"><span>Years experience</span><input type="number" min="0" max="50" value={editYears} onChange={(e) => setEditYears(e.target.value)} /></label>
          <label className="portal-sidebar-field"><span>Salary minimum</span><input type="number" min="0" value={editSalaryMin} onChange={(e) => setEditSalaryMin(e.target.value)} /></label>
          <label className="portal-sidebar-field">
            <span>Salary unit</span>
            <select value={editSalaryUnit} onChange={(e) => setEditSalaryUnit(e.target.value)}>
              <option value="yearly">Yearly</option><option value="hourly">Hourly</option><option value="monthly">Monthly</option>
            </select>
          </label>
          <div className="portal-sidebar-edit-actions">
            <button className="portal-sidebar-btn-primary" onClick={saveProfile} disabled={saveBusy}>{saveBusy ? "Saving..." : "Save"}</button>
            <button className="portal-sidebar-btn-ghost" onClick={() => setEditing(false)}>Cancel</button>
          </div>
        </div>
      )}

      {!editing && <button className="portal-sidebar-btn-outline" onClick={startEdit}>Edit profile</button>}

      <div className="portal-sidebar-resume">
        <div className="portal-sidebar-resume-title">Resume</div>
        {profile?.resume_filename ? (
          <div className="portal-sidebar-resume-file">
            <span className="portal-sidebar-resume-name" title={profile.resume_filename}>{profile.resume_filename}</span>
            <a href={`${apiClient.portalResumeUrl()}?t=${getStoredAccessToken()}`} target="_blank" rel="noopener noreferrer" className="portal-sidebar-btn-ghost">Download</a>
          </div>
        ) : <div className="portal-sidebar-resume-empty">No resume yet</div>}
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
        <button className="portal-sidebar-btn-outline" onClick={() => fileRef.current?.click()} disabled={resumeBusy}>
          {resumeBusy ? "Uploading..." : profile?.resume_filename ? "Replace resume" : "Upload resume"}
        </button>
      </div>

      {sideError && <div className="portal-sidebar-error">{sideError}</div>}
      {sideSuccess && <div className="portal-sidebar-success">{sideSuccess}</div>}
      <button className="portal-sidebar-signout" onClick={onLogout}>Sign out</button>
    </aside>
  );
}

function PreferencePanel({
  preferences,
  applications,
  totalMatches,
  onSaved,
}: {
  preferences: CandidatePreference | null;
  applications: Application[];
  totalMatches: number;
  onSaved: (preferences: CandidatePreference) => void;
}) {
  const [preferredTitles, setPreferredTitles] = useState<string[]>([]);
  const [employmentPreferences, setEmploymentPreferences] = useState<string[]>([]);
  const [domainExpertise, setDomainExpertise] = useState<string[]>([]);
  const [locationText, setLocationText] = useState("");
  const [keywordsText, setKeywordsText] = useState("");
  const [excludeText, setExcludeText] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    setPreferredTitles(preferences?.preferred_titles ?? []);
    setEmploymentPreferences(preferences?.employment_preferences ?? []);
    setDomainExpertise(preferences?.domain_expertise ?? []);
    setLocationText((preferences?.location_preferences ?? []).join(", "));
    setKeywordsText((preferences?.must_have_keywords ?? []).join(", "));
    setExcludeText((preferences?.exclude_keywords ?? []).join(", "));
  }, [preferences]);

  async function savePreferences() {
    setBusy(true);
    setMessage(null);
    try {
      const updated = await apiClient.portalUpdatePreferences({
        preferred_titles: preferredTitles,
        employment_preferences: employmentPreferences,
        location_preferences: splitList(locationText),
        domain_expertise: domainExpertise,
        must_have_keywords: splitList(keywordsText),
        exclude_keywords: splitList(excludeText),
      });
      onSaved(updated);
      setMessage("Preferences saved. Your future matches will use this profile.");
      setTimeout(() => setMessage(null), 3500);
    } finally {
      setBusy(false);
    }
  }

  const appliedCount = applications.filter((app) => isAppliedStatus(app.status)).length;
  const savedCount = applications.filter((app) => app.status === "saved").length;
  const pendingCount = Math.max(totalMatches - new Set(applications.map((app) => app.job_id)).size, 0);

  return (
    <section className="portal-profile-panel">
      <div className="portal-profile-stats">
        <div><strong>{totalMatches}</strong><span>Matching jobs</span></div>
        <div><strong>{appliedCount}</strong><span>Applied</span></div>
        <div><strong>{savedCount}</strong><span>Saved</span></div>
        <div><strong>{pendingCount}</strong><span>Pending</span></div>
      </div>

      <div className="portal-preference-card">
        <div className="portal-card-heading">
          <div>
            <h3>Job profile</h3>
            <p>Tell us where to focus: target roles, domains, work modes, locations, and keywords.</p>
          </div>
          <button className="portal-sidebar-btn-primary" type="button" onClick={savePreferences} disabled={busy}>{busy ? "Saving..." : "Save profile"}</button>
        </div>

        <div className="portal-pref-section">
          <span className="portal-pref-label">Target roles</span>
          <div className="portal-chip-group">
            {ROLE_OPTIONS.map((role) => (
              <button key={role} className={`portal-choice-chip${preferredTitles.includes(role) ? " portal-choice-chip-active" : ""}`} type="button" onClick={() => setPreferredTitles((current) => toggleValue(current, role))}>{role}</button>
            ))}
          </div>
        </div>

        <div className="portal-pref-section">
          <span className="portal-pref-label">Work mode</span>
          <div className="portal-chip-group">
            {WORK_MODE_OPTIONS.map((mode) => (
              <button key={mode} className={`portal-choice-chip${employmentPreferences.includes(mode) ? " portal-choice-chip-active" : ""}`} type="button" onClick={() => setEmploymentPreferences((current) => toggleValue(current, mode))}>{mode}</button>
            ))}
          </div>
        </div>

        <div className="portal-pref-section">
          <span className="portal-pref-label">Preferred industries</span>
          <div className="portal-chip-group">
            {DOMAIN_OPTIONS.map((domain) => (
              <button key={domain} className={`portal-choice-chip${domainExpertise.includes(domain) ? " portal-choice-chip-active" : ""}`} type="button" onClick={() => setDomainExpertise((current) => toggleValue(current, domain))}>{domain}</button>
            ))}
          </div>
        </div>

        <div className="portal-preference-grid">
          <label><span>Preferred locations</span><input value={locationText} onChange={(event) => setLocationText(event.target.value)} placeholder="Remote, Atlanta, Dallas" /></label>
          <label><span>Must-have keywords</span><input value={keywordsText} onChange={(event) => setKeywordsText(event.target.value)} placeholder="SQL, Excel, Power BI" /></label>
          <label><span>Avoid keywords</span><input value={excludeText} onChange={(event) => setExcludeText(event.target.value)} placeholder="Senior, onsite only, contract" /></label>
        </div>
        {message && <div className="portal-inline-success">{message}</div>}
      </div>
    </section>
  );
}

function CommandCenter({
  matches,
  applications,
  profile,
  topMatch,
  topJob,
}: {
  matches: Match[];
  applications: Application[];
  profile: Candidate | null;
  topMatch: Match | undefined;
  topJob: Job | undefined;
}) {
  const applied = applications.filter((app) => isAppliedStatus(app.status)).length;
  const saved = applications.filter((app) => app.status === "saved").length;
  const high = matches.filter((match) => match.score >= 80).length;
  const pending = Math.max(matches.length - new Set(applications.map((app) => app.job_id)).size, 0);
  const resumeReady = Boolean(profile?.resume_filename);

  return (
    <section className="portal-command-grid">
      <div className="portal-command-card portal-command-primary">
        <span className="portal-eyebrow">Today&apos;s focus</span>
        <h2>{topJob ? `${topJob.title} at ${topJob.company}` : "Complete your job profile"}</h2>
        <p>{topMatch ? `${Math.round(topMatch.score)}% match. ${topMatch.explanation ?? "Review this first and request tailoring if it fits."}` : "Add target roles, upload your resume, and new matches will become easier to rank."}</p>
      </div>
      <div className="portal-command-card"><strong>{high}</strong><span>High-fit jobs</span></div>
      <div className="portal-command-card"><strong>{applied}</strong><span>Applications sent</span></div>
      <div className="portal-command-card"><strong>{saved}</strong><span>Saved for review</span></div>
      <div className="portal-command-card"><strong>{pending}</strong><span>Pending decisions</span></div>
      <div className={`portal-command-card ${resumeReady ? "portal-ready" : "portal-attention"}`}><strong>{resumeReady ? "Ready" : "Needed"}</strong><span>Resume status</span></div>
    </section>
  );
}

function JobCard({
  match,
  job,
  status,
  preferences,
  actionBusy,
  onApply,
  onSave,
  onSkip,
  onTailor,
}: {
  match: Match;
  job: Job | undefined;
  status: string | null | undefined;
  preferences: CandidatePreference | null;
  actionBusy: boolean;
  onApply: () => void;
  onSave: () => void;
  onSkip: () => void;
  onTailor: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const score = Math.round(match.score);
  const sc = scoreColor(score);
  const reasons = matchReasons(match, job, preferences);
  const missing = missingKeywords(match, job, preferences);
  const applied = isAppliedStatus(status);
  const saved = status === "saved";
  const skipped = status === "not_interested";
  const primaryRole = preferences?.preferred_titles?.[0] ?? job?.title ?? "this role";
  const recruiterMessage = job
    ? `Hi, I am interested in the ${job.title} role at ${job.company}. My background aligns with the role requirements, and I would welcome the chance to discuss fit.`
    : "Save a job to generate a recruiter outreach message.";

  return (
    <article className={`portal-job-card portal-job-card-enhanced${skipped ? " portal-job-muted" : ""}`}>
      <div className="portal-job-card-top">
        <div className="portal-job-score" style={{ background: sc.bg, color: sc.text, border: `1px solid ${sc.border}` }}>
          {score}<span className="portal-job-score-denom">/100</span>
        </div>
        <div className="portal-job-body">
          <div className="portal-job-title">{job?.title ?? `Job #${match.job_id}`}</div>
          <div className="portal-job-meta">
            {job?.company && <span className="portal-job-company">{job.company}</span>}
            {job?.location && <span> - {job.location}</span>}
            {job?.posted_date && <span> - Posted {formatDate(job.posted_date)}</span>}
          </div>
          <div className="portal-job-badges">
            {job?.is_remote && <span className="portal-badge portal-badge-remote">Remote</span>}
            {job?.employment_type && <span className="portal-badge portal-badge-type">{job.employment_type}</span>}
            {job?.salary_min && <span className="portal-badge portal-badge-salary">${(job.salary_min / 1000).toFixed(0)}k{job.salary_max ? `-$${(job.salary_max / 1000).toFixed(0)}k` : "+"}</span>}
            {saved && <span className="portal-badge portal-badge-saved">Saved</span>}
            {applied && <span className="portal-badge portal-badge-applied">Applied</span>}
          </div>
        </div>
      </div>

      <div className="portal-fit-grid portal-fit-grid-compact">
        <div>
          <span className="portal-fit-label">Why it matches</span>
          <div className="portal-mini-list">
            {(reasons.length ? reasons : ["Good overall profile alignment"]).slice(0, 3).map((reason) => <span key={reason}>{reason}</span>)}
          </div>
        </div>
        <div>
          <span className="portal-fit-label">Resume focus</span>
          <div className="portal-mini-list">
            {(missing.length ? missing : ["Resume already covers key terms"]).slice(0, 3).map((keyword) => <span key={keyword}>{keyword}</span>)}
          </div>
        </div>
      </div>

      {match.explanation && <div className="portal-job-explanation">{truncateText(match.explanation, expanded ? 900 : 170)}</div>}

      {expanded && (
        <div className="portal-job-detail-drawer">
          <div>
            <span className="portal-fit-label">Application plan</span>
            <p>Use a tailored resume for {primaryRole}, mention the strongest matching keywords, and apply while the posting is fresh.</p>
          </div>
          <div>
            <span className="portal-fit-label">Recruiter message</span>
            <p>{recruiterMessage}</p>
          </div>
          <div>
            <span className="portal-fit-label">Interview prep</span>
            <p>Prepare one project story, one metrics-driven result, and one answer connecting your tools to business outcomes.</p>
          </div>
        </div>
      )}

      <div className="portal-job-actions portal-job-actions-enhanced">
        <button type="button" className="portal-btn-apply" onClick={onApply} disabled={actionBusy || applied}>{applied ? "Applied" : "Apply"}</button>
        <button type="button" className="portal-btn-secondary" onClick={onTailor} disabled={actionBusy}>Request tailored resume</button>
        <button type="button" className="portal-btn-secondary" onClick={onSave} disabled={actionBusy || saved}>{saved ? "Saved" : "Save"}</button>
        <button type="button" className="portal-btn-secondary" onClick={() => setExpanded((value) => !value)}>{expanded ? "Less detail" : "View plan"}</button>
        <button type="button" className="portal-btn-quiet" onClick={onSkip} disabled={actionBusy || skipped}>{skipped ? "Hidden" : "Not interested"}</button>
      </div>
    </article>
  );
}

function ApplicationTracker({
  applications,
  jobCache,
  matches,
}: {
  applications: Application[];
  jobCache: Map<number, Job>;
  matches: Match[];
}) {
  const rows = applications.slice().sort((a, b) => new Date(b.applied_at).getTime() - new Date(a.applied_at).getTime());
  const applied = rows.filter((app) => isAppliedStatus(app.status));
  const saved = rows.filter((app) => app.status === "saved");
  const hidden = rows.filter((app) => app.status === "not_interested");
  const untouched = matches.length - new Set(rows.map((app) => app.job_id)).size;

  return (
    <section className="portal-panel">
      <div className="portal-card-heading">
        <div><h3>Application tracker</h3><p>Every action is visible here so candidates know exactly what has happened.</p></div>
      </div>
      <div className="portal-tracker-summary">
        <div><strong>{applied.length}</strong><span>Applied / active</span></div>
        <div><strong>{saved.length}</strong><span>Saved</span></div>
        <div><strong>{untouched}</strong><span>Pending review</span></div>
        <div><strong>{hidden.length}</strong><span>Not interested</span></div>
      </div>
      <div className="portal-tracker-list">
        {rows.length === 0 ? <div className="portal-v2-empty">No application activity yet.</div> : rows.map((app) => {
          const job = jobCache.get(app.job_id);
          return (
            <div className="portal-tracker-row" key={app.id}>
              <div><strong>{job?.title ?? `Job #${app.job_id}`}</strong><span>{job?.company ?? "Company unavailable"} - {formatDate(app.applied_at)}</span></div>
              <span className={`portal-status-pill portal-status-${app.status ?? "pending"}`}>{(app.status ?? "pending").replace("_", " ")}</span>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function ResumeAndPrepPanel({
  profile,
  topMatch,
  topJob,
  preferences,
  matches,
  applications,
}: {
  profile: Candidate | null;
  topMatch: Match | undefined;
  topJob: Job | undefined;
  preferences: CandidatePreference | null;
  matches: Match[];
  applications: Application[];
}) {
  const readinessItems = [
    { label: "Resume uploaded", done: Boolean(profile?.resume_filename) },
    { label: "Target roles selected", done: Boolean(preferences?.preferred_titles?.length) },
    { label: "Locations selected", done: Boolean(preferences?.location_preferences?.length) },
    { label: "Work authorization added", done: Boolean(profile?.work_authorization) },
    { label: "Keyword focus added", done: Boolean(preferences?.must_have_keywords?.length) },
  ];
  const readiness = Math.round((readinessItems.filter((item) => item.done).length / readinessItems.length) * 100);
  const missing = topMatch ? missingKeywords(topMatch, topJob, preferences).slice(0, 6) : [];
  const applied = applications.filter((app) => isAppliedStatus(app.status)).length;

  return (
    <div className="portal-two-column">
      <section className="portal-panel">
        <div className="portal-card-heading"><div><h3>Resume fit checker</h3><p>Use this to see whether the candidate profile is application-ready.</p></div><strong className="portal-readiness-score">{readiness}%</strong></div>
        <div className="portal-readiness-bars">
          {readinessItems.map((item) => <div key={item.label} className={item.done ? "done" : ""}><span>{item.label}</span><strong>{item.done ? "Done" : "Missing"}</strong></div>)}
        </div>
        <div className="portal-gap-box">
          <span className="portal-fit-label">Suggested resume keywords for top match</span>
          <div className="portal-mini-list">{(missing.length ? missing : ["No obvious gaps for the top match"]).map((item) => <span key={item}>{item}</span>)}</div>
        </div>
      </section>

      <section className="portal-panel">
        <div className="portal-card-heading"><div><h3>Interview readiness</h3><p>Generated from the current top opportunity and candidate target role.</p></div></div>
        <div className="portal-prep-list">
          <div><strong>Company brief</strong><span>{topJob ? `Research ${topJob.company}, its product, customers, and recent hiring themes before applying.` : "Choose a top match to create company prep."}</span></div>
          <div><strong>Likely questions</strong><span>Walk through a recent project, explain your analysis process, and connect your tools to business outcomes.</span></div>
          <div><strong>Role talking points</strong><span>{preferences?.preferred_titles?.[0] ? `Prepare stories for ${preferences.preferred_titles[0]} responsibilities.` : "Add a target role to sharpen prep prompts."}</span></div>
          <div><strong>Momentum</strong><span>{applied} applications are active from {matches.length} current matches.</span></div>
        </div>
      </section>
    </div>
  );
}

function ValueDashboard({ matches, applications }: { matches: Match[]; applications: Application[] }) {
  const applied = applications.filter((app) => isAppliedStatus(app.status)).length;
  const tailored = applications.filter((app) => app.notes?.toLowerCase().includes("tailored")).length;
  const hoursSaved = Math.round((matches.length * 8 + applied * 12 + tailored * 20) / 60);
  return (
    <section className="portal-panel portal-value-panel">
      <div className="portal-card-heading"><div><h3>Subscription value</h3><p>A clear view of what the service is doing for the candidate.</p></div></div>
      <div className="portal-value-grid">
        <div><strong>{matches.length}</strong><span>Jobs scanned into your queue</span></div>
        <div><strong>{applied}</strong><span>Applications moved forward</span></div>
        <div><strong>{tailored}</strong><span>Tailoring requests</span></div>
        <div><strong>{hoursSaved}h</strong><span>Estimated time saved</span></div>
      </div>
    </section>
  );
}

export function CandidatePortalPage({ currentUser, onLogout }: Props) {
  const [profile, setProfile] = useState<Candidate | null>(null);
  const [preferences, setPreferences] = useState<CandidatePreference | null>(null);
  const [matches, setMatches] = useState<Match[]>([]);
  const [applications, setApplications] = useState<Application[]>([]);
  const [jobCache, setJobCache] = useState<Map<number, Job>>(new Map());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filterKey, setFilterKey] = useState<FilterKey>("all");
  const [sortKey, setSortKey] = useState<SortKey>("score");
  const [search, setSearch] = useState("");
  const [activeTab, setActiveTab] = useState<PortalTab>("overview");
  const [actionBusyJobId, setActionBusyJobId] = useState<number | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [matchPage, setMatchPage] = useState(1);
  const [matchPageSize, setMatchPageSize] = useState(10);

  useEffect(() => { void loadAll(); }, []);
  useEffect(() => { setMatchPage(1); }, [filterKey, search, sortKey, activeTab, matchPageSize]);

  async function loadAll() {
    setBusy(true);
    setError(null);
    try {
      const [profileData, matchData, preferenceData, applicationData] = await Promise.all([
        apiClient.portalGetProfile(),
        apiClient.portalGetMatches({ limit: 100, offset: 0 }),
        apiClient.portalGetPreferences(),
        apiClient.portalGetApplications({ limit: 200, offset: 0 }),
      ]);
      setProfile(profileData);
      setPreferences(preferenceData);
      setMatches(matchData.items);
      setApplications(applicationData.items);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load portal data");
    } finally {
      setBusy(false);
    }
  }

  async function loadJobsForIds(jobIds: number[]) {
    const missingIds = [...new Set(jobIds)].filter((jobId) => !jobCache.has(jobId));
    if (missingIds.length === 0) return;
    const pairs = await Promise.all(
      missingIds.map((jobId) => apiClient.portalGetJob(jobId).then((job) => [jobId, job] as [number, Job]).catch(() => null))
    );
    setJobCache((current) => {
      const next = new Map(current);
      for (const pair of pairs) if (pair) next.set(pair[0], pair[1]);
      return next;
    });
  }

  const applicationsByJob = useMemo(() => {
    const map = new Map<number, Application>();
    applications.forEach((application) => map.set(application.job_id, application));
    return map;
  }, [applications]);

  const visibleMatches = useMemo(() => {
    return matches
      .filter((m) => {
        const status = getApplicationStatus(applicationsByJob, m.job_id);
        if (filterKey === "high") return m.score >= 80;
        if (filterKey === "saved") return status === "saved";
        if (filterKey === "pending") return status === "pending";
        if (filterKey === "applied") return isAppliedStatus(status);
        return status !== "not_interested";
      })
      .filter((m) => {
        if (!search.trim()) return true;
        const q = search.toLowerCase();
        return jobSearchText(jobCache.get(m.job_id)).includes(q);
      })
      .sort((a, b) => {
        if (sortKey === "score") return b.score - a.score;
        if (sortKey === "title") return (jobCache.get(a.job_id)?.title ?? "").localeCompare(jobCache.get(b.job_id)?.title ?? "");
        return b.id - a.id;
      });
  }, [matches, applicationsByJob, filterKey, search, sortKey, jobCache]);

  const topMatch = visibleMatches[0] ?? matches.slice().sort((a, b) => b.score - a.score)[0];
  const topJob = topMatch ? jobCache.get(topMatch.job_id) : undefined;
  const totalMatchPages = Math.max(1, Math.ceil(visibleMatches.length / matchPageSize));
  const safeMatchPage = Math.min(matchPage, totalMatchPages);
  const pagedMatches = visibleMatches.slice((safeMatchPage - 1) * matchPageSize, safeMatchPage * matchPageSize);
  const visibleJobIdKey = pagedMatches.map((match) => match.job_id).join(",");
  useEffect(() => {
    const ids = pagedMatches.map((match) => match.job_id);
    if (topMatch) ids.push(topMatch.job_id);
    void loadJobsForIds(ids);
  }, [visibleJobIdKey, topMatch?.job_id]);
  const counts = {
    high: matches.filter((m) => m.score >= 80).length,
    saved: applications.filter((app) => app.status === "saved").length,
    applied: applications.filter((app) => isAppliedStatus(app.status)).length,
    pending: Math.max(matches.length - new Set(applications.map((app) => app.job_id)).size, 0),
  };

  async function recordJobStatus(jobId: number, status: string, notes?: string | null) {
    setActionBusyJobId(jobId);
    setNotice(null);
    try {
      const application = status === "applied"
        ? await apiClient.portalApplyToJob(jobId)
        : await apiClient.portalSetJobStatus(jobId, { status, notes });
      setApplications((current) => [application, ...current.filter((item) => item.job_id !== application.job_id)]);
      if (status === "saved") setNotice("Saved to your review queue.");
      if (status === "not_interested") setNotice("Hidden from your active match list.");
      if (notes?.includes("tailored")) setNotice("Tailored resume request saved for this job.");
      setTimeout(() => setNotice(null), 3000);
      return application;
    } finally {
      setActionBusyJobId(null);
    }
  }

  async function handleApply(match: Match, job: Job | undefined) {
    await recordJobStatus(match.job_id, "applied", "Applied from candidate portal.");
    const applyUrl = job?.canonical_apply_url ?? job?.apply_url;
    if (applyUrl) window.open(applyUrl, "_blank", "noopener,noreferrer");
  }

  return (
    <div className="portal-v2-shell">
      <header className="portal-v2-topbar">
        <div className="portal-v2-brand">
          <img src="/brand/think-success-logo.jpg" alt="ThinkSuccess" className="portal-v2-logo" />
          <span className="portal-v2-brand-name">ThinkSuccess Portal</span>
        </div>
        <div className="portal-v2-topbar-right"><span className="portal-v2-greeting">Hi, {currentUser.name.split(" ")[0]}</span></div>
      </header>

      <div className="portal-v2-body">
        <ProfileSidebar profile={profile} currentUser={currentUser} onLogout={onLogout} onProfileSaved={setProfile} />

        <main className="portal-v2-main">
          {error && <div className="portal-error">{error}</div>}
          {notice && <div className="portal-inline-success">{notice}</div>}

          <div className="portal-tabs">
            {([
              ["overview", "Overview"],
              ["matches", "Job matches"],
              ["tracker", "Tracker"],
              ["prep", "Resume & prep"],
            ] as [PortalTab, string][]).map(([tab, label]) => (
              <button key={tab} className={activeTab === tab ? "active" : ""} onClick={() => setActiveTab(tab)}>{label}</button>
            ))}
          </div>

          {activeTab === "overview" && (
            <>
              <CommandCenter matches={matches} applications={applications} profile={profile} topMatch={topMatch} topJob={topJob} />
              <PreferencePanel preferences={preferences} applications={applications} totalMatches={matches.length} onSaved={setPreferences} />
              <ValueDashboard matches={matches} applications={applications} />
            </>
          )}

          {activeTab === "matches" && (
            <>
              <div className="portal-v2-section-header">
                <div>
                  <h2 className="portal-v2-section-title">Your job matches</h2>
                  <p className="portal-v2-section-sub">{busy ? "Loading..." : `${matches.length} matches ranked for your profile`}</p>
                </div>
              </div>

              <div className="portal-v2-filters">
                {([
                  ["all", `All (${matches.length})`],
                  ["high", `High (${counts.high})`],
                  ["saved", `Saved (${counts.saved})`],
                  ["pending", `Pending (${counts.pending})`],
                  ["applied", `Applied (${counts.applied})`],
                ] as [FilterKey, string][]).map(([key, label]) => (
                  <button key={key} className={`portal-v2-filter-chip${filterKey === key ? " active" : ""}`} onClick={() => setFilterKey(key)}>{label}</button>
                ))}
                <div className="portal-v2-search-wrap">
                  <input className="portal-v2-search" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search title, company, skill..." />
                  {search && <button className="portal-v2-search-clear" onClick={() => setSearch("")}>Clear</button>}
                </div>
                <select className="portal-v2-sort-select" value={sortKey} onChange={(e) => setSortKey(e.target.value as SortKey)}>
                  <option value="score">Best match</option>
                  <option value="date">Newest first</option>
                  <option value="title">Title A-Z</option>
                </select>
                <select className="portal-v2-sort-select" value={matchPageSize} onChange={(e) => setMatchPageSize(Number(e.target.value))}>
                  {PAGE_SIZE_OPTIONS.map((size) => <option key={size} value={size}>{size} per page</option>)}
                </select>
              </div>

              {busy && matches.length === 0 ? (
                <div className="portal-v2-loading"><div className="portal-v2-spinner" /><span>Finding your matches...</span></div>
              ) : visibleMatches.length === 0 ? (
                <div className="portal-v2-empty">No jobs match this view yet.</div>
              ) : (
                <>
                  <div className="portal-results-meta">
                    Showing {(safeMatchPage - 1) * matchPageSize + 1}-{Math.min(safeMatchPage * matchPageSize, visibleMatches.length)} of {visibleMatches.length} jobs
                  </div>
                  <div className="portal-v2-cards">
                    {pagedMatches.map((match) => {
                      const job = jobCache.get(match.job_id);
                      return (
                        <JobCard
                          key={match.id}
                          match={match}
                          job={job}
                          status={getApplicationStatus(applicationsByJob, match.job_id)}
                          preferences={preferences}
                          actionBusy={actionBusyJobId === match.job_id}
                          onApply={() => void handleApply(match, job)}
                          onSave={() => void recordJobStatus(match.job_id, "saved", "Candidate saved this job for review.")}
                          onSkip={() => void recordJobStatus(match.job_id, "not_interested", "Candidate marked this job as not interested.")}
                          onTailor={() => void recordJobStatus(match.job_id, "saved", "Candidate requested a tailored resume for this job.")}
                        />
                      );
                    })}
                  </div>
                  <div className="portal-pagination">
                    <button type="button" onClick={() => setMatchPage((page) => Math.max(1, page - 1))} disabled={safeMatchPage <= 1}>Previous</button>
                    <span>Page {safeMatchPage} of {totalMatchPages}</span>
                    <button type="button" onClick={() => setMatchPage((page) => Math.min(totalMatchPages, page + 1))} disabled={safeMatchPage >= totalMatchPages}>Next</button>
                  </div>
                </>
              )}
            </>
          )}

          {activeTab === "tracker" && <ApplicationTracker applications={applications} jobCache={jobCache} matches={matches} />}
          {activeTab === "prep" && <ResumeAndPrepPanel profile={profile} topMatch={topMatch} topJob={topJob} preferences={preferences} matches={matches} applications={applications} />}
        </main>
      </div>
    </div>
  );
}
