import { useEffect, useState } from "react";

import { apiClient } from "../api/client";
import type { Candidate, CandidateCreatePayload, CandidatePreference, CandidateSkill, Employee } from "../types";

type AdminCandidatesPageProps = {
  candidates: Candidate[];
  employees: Employee[];
  busy: boolean;
  error: string | null;
  onCreateCandidate: (payload: CandidateCreatePayload) => Promise<void>;
  onUpdateCandidate: (id: number, payload: Partial<CandidateCreatePayload>) => Promise<void>;
  onDeleteCandidate: (id: number) => Promise<void>;
  onRefresh: () => Promise<void>;
};

const BLANK_FORM: CandidateCreatePayload = {
  name: "",
  email: "",
  phone: "",
  location: "",
  assigned_employee: null,
  work_authorization: "",
  years_experience: undefined,
  salary_min: undefined,
  salary_unit: "annual",
  active: true
};

const BLANK_PREFS: Omit<CandidatePreference, "candidate_id"> = {
  preferred_titles: [],
  employment_preferences: [],
  location_preferences: [],
  domain_expertise: [],
  must_have_keywords: [],
  exclude_keywords: []
};

function tagInput(
  label: string,
  values: string[],
  onChange: (next: string[]) => void
) {
  return (
    <label className="filter-field" key={label}>
      <span>{label}</span>
      <input
        placeholder="Comma-separated values, press Enter"
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === ",") {
            e.preventDefault();
            const val = (e.currentTarget as HTMLInputElement).value.trim().replace(/,$/, "");
            if (val && !values.includes(val)) onChange([...values, val]);
            (e.currentTarget as HTMLInputElement).value = "";
          }
        }}
      />
      <div className="tag-chips">
        {values.map((v) => (
          <span key={v} className="tag-chip">
            {v}
            <button type="button" onClick={() => onChange(values.filter((x) => x !== v))}>×</button>
          </span>
        ))}
      </div>
    </label>
  );
}

export function AdminCandidatesPage({
  candidates,
  employees,
  busy,
  error,
  onCreateCandidate,
  onUpdateCandidate,
  onDeleteCandidate,
  onRefresh
}: AdminCandidatesPageProps) {
  const [form, setForm] = useState<CandidateCreatePayload>(BLANK_FORM);
  const [editId, setEditId] = useState<number | null>(null);
  const [editForm, setEditForm] = useState<Partial<CandidateCreatePayload>>({});
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [prefs, setPrefs] = useState<Omit<CandidatePreference, "candidate_id">>(BLANK_PREFS);
  const [skills, setSkills] = useState<CandidateSkill[]>([]);
  const [prefsBusy, setPrefsBusy] = useState(false);
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [resumeBusy, setResumeBusy] = useState(false);
  const [resumeMsg, setResumeMsg] = useState<string | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null);

  // Load preferences + skills when expanding a candidate
  useEffect(() => {
    if (expandedId == null) return;
    setPrefsBusy(true);
    setResumeMsg(null);
    Promise.all([
      apiClient.getCandidatePreferences(expandedId).catch(() => null),
      apiClient.getCandidateSkills(expandedId).catch(() => [])
    ]).then(([p, s]) => {
      if (p) setPrefs({ ...BLANK_PREFS, ...p });
      else setPrefs(BLANK_PREFS);
      setSkills(s as CandidateSkill[]);
      setPrefsBusy(false);
    });
  }, [expandedId]);

  async function handleSavePrefs() {
    if (expandedId == null) return;
    setPrefsBusy(true);
    try {
      await apiClient.upsertCandidatePreferences(expandedId, prefs);
      setResumeMsg("Preferences saved.");
    } catch {
      setLocalError("Failed to save preferences.");
    } finally {
      setPrefsBusy(false);
    }
  }

  async function handleUploadResume() {
    if (!resumeFile || expandedId == null) return;
    setResumeBusy(true);
    setResumeMsg(null);
    try {
      const res = await apiClient.uploadResume(expandedId, resumeFile);
      setResumeMsg(`✓ Resume uploaded: ${res.filename}`);
      setResumeFile(null);
      await onRefresh();
    } catch {
      setResumeMsg("Upload failed. Please try again.");
    } finally {
      setResumeBusy(false);
    }
  }

  function startEdit(c: Candidate) {
    setEditId(c.id);
    setEditForm({
      name: c.name,
      email: c.email ?? "",
      phone: c.phone ?? "",
      location: c.location ?? "",
      assigned_employee: c.assigned_employee ?? null,
      work_authorization: c.work_authorization ?? "",
      years_experience: c.years_experience ?? undefined,
      salary_min: c.salary_min ?? undefined,
      salary_unit: c.salary_unit ?? "annual",
      active: c.active
    });
  }

  return (
    <section className="dashboard-stack">
      {/* ── Add candidate ─────────────────────────────────────────────────────── */}
      <section className="panel">
        <div className="section-heading">
          <h3>Add Candidate</h3>
          <p>Create a new candidate profile. You can upload a resume and set preferences after saving.</p>
        </div>

        <form
          className="admin-user-form"
          onSubmit={(e) => {
            e.preventDefault();
            setLocalError(null);
            void onCreateCandidate(form).then(() => setForm(BLANK_FORM));
          }}
        >
          <div className="form-row">
            <label className="filter-field">
              <span>Full Name *</span>
              <input
                required
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                placeholder="Jane Doe"
              />
            </label>
            <label className="filter-field">
              <span>Email</span>
              <input
                type="email"
                value={form.email ?? ""}
                onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
                placeholder="jane@example.com"
              />
            </label>
            <label className="filter-field">
              <span>Phone</span>
              <input
                value={form.phone ?? ""}
                onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))}
                placeholder="+1 555 000 0000"
              />
            </label>
          </div>

          <div className="form-row">
            <label className="filter-field">
              <span>Location</span>
              <input
                value={form.location ?? ""}
                onChange={(e) => setForm((f) => ({ ...f, location: e.target.value }))}
                placeholder="Dallas, TX"
              />
            </label>
            <label className="filter-field">
              <span>Work Authorization</span>
              <select
                value={form.work_authorization ?? ""}
                onChange={(e) => setForm((f) => ({ ...f, work_authorization: e.target.value }))}
              >
                <option value="">— select —</option>
                <option value="US Citizen">US Citizen</option>
                <option value="Green Card">Green Card</option>
                <option value="H1B">H1B</option>
                <option value="OPT">OPT</option>
                <option value="CPT">CPT</option>
                <option value="EAD">EAD</option>
                <option value="TN Visa">TN Visa</option>
              </select>
            </label>
            <label className="filter-field">
              <span>Assigned Employee</span>
              <select
                value={form.assigned_employee ?? ""}
                onChange={(e) => setForm((f) => ({ ...f, assigned_employee: e.target.value ? Number(e.target.value) : null }))}
              >
                <option value="">— unassigned —</option>
                {employees.map((emp) => (
                  <option key={emp.id} value={emp.id}>{emp.name}</option>
                ))}
              </select>
            </label>
          </div>

          <div className="form-row">
            <label className="filter-field">
              <span>Years Experience</span>
              <input
                type="number"
                min={0}
                value={form.years_experience ?? ""}
                onChange={(e) => setForm((f) => ({ ...f, years_experience: e.target.value ? Number(e.target.value) : undefined }))}
                placeholder="5"
              />
            </label>
            <label className="filter-field">
              <span>Minimum Salary</span>
              <input
                type="number"
                min={0}
                value={form.salary_min ?? ""}
                onChange={(e) => setForm((f) => ({ ...f, salary_min: e.target.value ? Number(e.target.value) : undefined }))}
                placeholder="80000"
              />
            </label>
            <label className="filter-field">
              <span>Salary Unit</span>
              <select
                value={form.salary_unit ?? "annual"}
                onChange={(e) => setForm((f) => ({ ...f, salary_unit: e.target.value }))}
              >
                <option value="annual">Annual</option>
                <option value="hourly">Hourly</option>
              </select>
            </label>
          </div>

          {(error ?? localError) ? <div className="error-banner">{error ?? localError}</div> : null}

          <button className="primary-button" type="submit" disabled={busy}>
            {busy ? "Saving..." : "Add Candidate"}
          </button>
        </form>
      </section>

      {/* ── Candidate list ────────────────────────────────────────────────────── */}
      <section className="panel">
        <div className="section-heading">
          <h3>Candidates ({candidates.length})</h3>
          <p>Click a row to edit profile, preferences, and upload resume.</p>
        </div>

        <div className="admin-candidate-list">
          {candidates.map((c) => {
            const assignedEmp = employees.find((e) => e.id === c.assigned_employee);
            const isExpanded = expandedId === c.id;
            const isEditing = editId === c.id;

            return (
              <article key={c.id} className={`admin-candidate-card${isExpanded ? " expanded" : ""}`}>
                {/* ── Row header ─────────────────────────────────────────────── */}
                <div className="candidate-card-header">
                  <div>
                    <strong>{c.name}</strong>
                    <p>{c.email ?? "No email"} · {c.phone ?? "No phone"} · {c.location ?? "No location"}</p>
                    <p>
                      {assignedEmp ? `Assigned to ${assignedEmp.name}` : "Unassigned"} ·{" "}
                      {c.work_authorization ?? "Auth not set"} ·{" "}
                      {c.years_experience != null ? `${c.years_experience}y exp` : ""}{" "}
                      {c.resume_filename ? <span className="resume-badge">📄 {c.resume_filename}</span> : null}
                    </p>
                  </div>
                  <div className="candidate-card-actions">
                    <span className={`queue-status-pill queue-status-${c.active ? "pending" : "skipped"}`}>
                      {c.active ? "Active" : "Inactive"}
                    </span>
                    <button
                      className="secondary-button"
                      onClick={() => {
                        setExpandedId(isExpanded ? null : c.id);
                        startEdit(c);
                      }}
                    >
                      {isExpanded ? "Collapse" : "Edit"}
                    </button>
                    {deleteConfirmId === c.id ? (
                      <>
                        <button
                          className="danger-button"
                          disabled={busy}
                          onClick={() => { void onDeleteCandidate(c.id).then(() => setDeleteConfirmId(null)); }}
                        >
                          Confirm Delete
                        </button>
                        <button className="secondary-button" onClick={() => setDeleteConfirmId(null)}>Cancel</button>
                      </>
                    ) : (
                      <button className="danger-button" onClick={() => setDeleteConfirmId(c.id)}>Delete</button>
                    )}
                  </div>
                </div>

                {/* ── Expanded edit panel ────────────────────────────────────── */}
                {isExpanded && isEditing ? (
                  <div className="candidate-detail-panel">
                    {/* Basic info edit */}
                    <h4>Edit Profile</h4>
                    <div className="form-row">
                      {(["name", "email", "phone", "location"] as const).map((field) => (
                        <label key={field} className="filter-field">
                          <span style={{ textTransform: "capitalize" }}>{field}</span>
                          <input
                            value={(editForm[field] as string) ?? ""}
                            onChange={(e) => setEditForm((f) => ({ ...f, [field]: e.target.value }))}
                          />
                        </label>
                      ))}
                    </div>
                    <div className="form-row">
                      <label className="filter-field">
                        <span>Work Auth</span>
                        <select
                          value={editForm.work_authorization ?? ""}
                          onChange={(e) => setEditForm((f) => ({ ...f, work_authorization: e.target.value }))}
                        >
                          <option value="">— select —</option>
                          {["US Citizen", "Green Card", "H1B", "OPT", "CPT", "EAD", "TN Visa"].map((v) => (
                            <option key={v} value={v}>{v}</option>
                          ))}
                        </select>
                      </label>
                      <label className="filter-field">
                        <span>Assigned Employee</span>
                        <select
                          value={editForm.assigned_employee ?? ""}
                          onChange={(e) => setEditForm((f) => ({ ...f, assigned_employee: e.target.value ? Number(e.target.value) : null }))}
                        >
                          <option value="">— unassigned —</option>
                          {employees.map((emp) => (
                            <option key={emp.id} value={emp.id}>{emp.name}</option>
                          ))}
                        </select>
                      </label>
                      <label className="filter-field">
                        <span>Years Exp</span>
                        <input
                          type="number"
                          value={editForm.years_experience ?? ""}
                          onChange={(e) => setEditForm((f) => ({ ...f, years_experience: e.target.value ? Number(e.target.value) : undefined }))}
                        />
                      </label>
                      <label className="filter-field">
                        <span>Active</span>
                        <select
                          value={editForm.active ? "true" : "false"}
                          onChange={(e) => setEditForm((f) => ({ ...f, active: e.target.value === "true" }))}
                        >
                          <option value="true">Active</option>
                          <option value="false">Inactive</option>
                        </select>
                      </label>
                    </div>
                    <button
                      className="primary-button"
                      disabled={busy}
                      onClick={() => void onUpdateCandidate(c.id, editForm).then(() => setEditId(null))}
                    >
                      {busy ? "Saving..." : "Save Profile"}
                    </button>

                    {/* Preferences */}
                    <h4 style={{ marginTop: "1.5rem" }}>Job Preferences</h4>
                    {prefsBusy ? <p>Loading…</p> : (
                      <>
                        {tagInput("Preferred Titles", prefs.preferred_titles, (v) => setPrefs((p) => ({ ...p, preferred_titles: v })))}
                        {tagInput("Domain Expertise", prefs.domain_expertise, (v) => setPrefs((p) => ({ ...p, domain_expertise: v })))}
                        {tagInput("Employment Preferences", prefs.employment_preferences, (v) => setPrefs((p) => ({ ...p, employment_preferences: v })))}
                        {tagInput("Location Preferences", prefs.location_preferences, (v) => setPrefs((p) => ({ ...p, location_preferences: v })))}
                        {tagInput("Must-Have Keywords", prefs.must_have_keywords, (v) => setPrefs((p) => ({ ...p, must_have_keywords: v })))}
                        {tagInput("Exclude Keywords", prefs.exclude_keywords, (v) => setPrefs((p) => ({ ...p, exclude_keywords: v })))}
                        <button className="primary-button" disabled={prefsBusy} onClick={() => void handleSavePrefs()}>
                          Save Preferences
                        </button>
                      </>
                    )}

                    {/* Skills */}
                    {skills.length > 0 ? (
                      <>
                        <h4 style={{ marginTop: "1.5rem" }}>Skills on File</h4>
                        <div className="tag-chips">
                          {skills.map((sk) => (
                            <span key={sk.skill_name} className="tag-chip">
                              {sk.skill_name}{sk.years_used ? ` (${sk.years_used}y)` : ""}
                            </span>
                          ))}
                        </div>
                      </>
                    ) : null}

                    {/* Resume upload */}
                    <h4 style={{ marginTop: "1.5rem" }}>Resume</h4>
                    {c.resume_filename ? (
                      <p>
                        Current: <strong>{c.resume_filename}</strong>{" "}
                        <a
                          href={apiClient.getResumeUrl(c.id)}
                          target="_blank"
                          rel="noreferrer"
                          className="secondary-button"
                          style={{ display: "inline-block", padding: "4px 10px", fontSize: "0.75rem" }}
                        >
                          Download
                        </a>
                      </p>
                    ) : (
                      <p>No resume uploaded yet.</p>
                    )}
                    <div className="resume-upload-row">
                      <input
                        type="file"
                        accept=".pdf,.docx,.txt"
                        onChange={(e) => setResumeFile(e.target.files?.[0] ?? null)}
                      />
                      <button
                        className="primary-button"
                        disabled={!resumeFile || resumeBusy}
                        onClick={() => void handleUploadResume()}
                      >
                        {resumeBusy ? "Uploading..." : "Upload Resume"}
                      </button>
                    </div>
                    {resumeMsg ? <p className={resumeMsg.startsWith("✓") ? "success-msg" : "error-banner"}>{resumeMsg}</p> : null}
                  </div>
                ) : null}
              </article>
            );
          })}

          {candidates.length === 0 ? (
            <p className="empty-state">No candidates yet. Add one above.</p>
          ) : null}
        </div>
      </section>
    </section>
  );
}
