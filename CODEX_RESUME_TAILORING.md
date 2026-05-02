# Codex Instructions: Resume Tailoring Module

> **Purpose:** Build a self-contained resume tailoring feature that can be merged back into the main `job-agent-v1` site with minimal conflicts.

---

## Context & Goal

ThinkSuccess is a recruiting platform (FastAPI backend + React/TypeScript/Vite frontend, PostgreSQL).

Employees use the platform to review job matches for their assigned candidates. This module adds a **resume tailoring workflow** directly on the job match detail view:

1. Employee sees the full Job Description (JD) on each job card.
2. If the candidate's existing resume needs adjustments for this JD, the employee triggers an AI-powered tailoring action.
3. The system generates a tailored DOCX file as a **separate artifact** (the master resume is never modified).
4. Employee can review, edit notes, and download the tailored DOCX.

---

## Step 1 — Branch Setup

Work on a dedicated branch so the merge back to `main` is clean:

```bash
git checkout main && git pull
git checkout -b codex/resume-tailoring-workflow
```

---

## Step 2 — Backend Changes

### 2a. New Alembic migration (`0008_resume_tailoring.py`)

```
revision = "0008"
down_revision = "0007"
```

Add table `tailored_resumes`:

| column | type | notes |
|---|---|---|
| id | Integer PK | |
| candidate_id | Integer FK → candidates.id | |
| job_id | Integer FK → jobs.id | |
| match_id | Integer FK nullable → matches.id | |
| created_by_employee_id | Integer FK nullable → employees.id | |
| created_at | DateTime | server_default=utcnow |
| notes | Text nullable | employee notes / instructions |
| filename | String(255) | stored DOCX filename |
| status | String(50) | "pending" | "processing" | "ready" | "error" |
| error_message | Text nullable | |

### 2b. New model (`app/models/tailored_resume.py`)

Standard SQLAlchemy Mapped class. Import + add to `app/models/__init__.py` `__all__`.

### 2c. New service (`app/services/resume_tailor.py`)

```python
async def tailor_resume(
    candidate_id: int,
    job_id: int,
    master_resume_path: str,   # path on disk to candidate's master resume
    jd_text: str,
    notes: str | None,
    db: Session,
) -> TailoredResume:
    ...
```

Logic:
- Call OpenAI (model: `gpt-4o`) with the master resume text + JD text + employee notes.
- Prompt the model to output a JSON list of suggested changes: each item has `section` (Summary|Experience|Skills), `action` (replace|add|remove), and `content`.
- Apply changes to an in-memory copy of the resume using `python-docx`.
- Save the resulting DOCX to `UPLOAD_DIR/tailored/{candidate_id}_{job_id}_{timestamp}.docx`.
- Update the `TailoredResume` DB record to `status="ready"` with the filename.

**Important constraints:**
- The master resume file at `UPLOAD_DIR/candidates/{candidate_id}/resume.*` must **never be modified**.
- Tailored DOCXs require the master resume to already be a `.docx` file. If it is PDF/TXT, return `status="error"` with `error_message="Master resume must be DOCX format for tailoring"`.
- Unsupported skills requested by the employee (i.e. not present in `candidate_skills` table) must be flagged: return them in a separate `flagged_skills` list in the API response for the employee to confirm before proceeding.

Add to `requirements.txt`:
- `openai>=1.0.0`
- `python-docx>=1.0.0`

### 2d. New API routes (add to `app/api/routes.py`)

All routes require `employee` or `super_admin` role. Employees are restricted to their assigned candidates (check `candidate.assigned_employee == current_user.employee_id`).

```
POST   /api/v1/jobs/{job_id}/tailor-resume
       Body: { candidate_id, notes?, confirm_flagged_skills? }
       Returns: TailoredResumeRead + flagged_skills[]

GET    /api/v1/tailored-resumes/{id}
       Returns: TailoredResumeRead (poll for status)

GET    /api/v1/tailored-resumes/{id}/download
       Returns: FileResponse (DOCX)

GET    /api/v1/jobs/{job_id}/tailored-resumes?candidate_id=X
       Returns: list[TailoredResumeRead]  (history for this job+candidate)
```

### 2e. New schemas (`app/schemas/tailored_resume.py`)

```python
class TailoredResumeRead(BaseModel):
    id: int
    candidate_id: int
    job_id: int
    status: str
    filename: str | None
    notes: str | None
    created_at: datetime
    error_message: str | None

class TailorResumeRequest(BaseModel):
    candidate_id: int
    notes: str | None = None
    confirm_flagged_skills: list[str] | None = None  # employee confirms these are OK
```

---

## Step 3 — Frontend Changes

### 3a. New page: `JobMatchDetailPage.tsx`

Route: accessed from the work queue / match list by clicking "View JD" on any job card.

**Left pane (60%):** Full Job Description viewer.
- Fetch job from `GET /api/v1/portal/jobs/{job_id}` (for portal) or `GET /api/v1/matches` job data (for admin).
- Render: title, company, location, employment type, salary, description (scrollable), domain tags, keywords.

**Right pane (40%):** Resume tailoring panel.
- Show candidate name + current resume filename.
- If no DOCX master resume → show warning: "Upload a DOCX resume to enable tailoring."
- "Tailor Resume for This Job" button.
- Optional notes textarea: "What to emphasize / what to adjust."
- On submit → call `POST /api/v1/jobs/{job_id}/tailor-resume`.
  - If response includes `flagged_skills` → show confirmation dialog listing them. Employee clicks "Add Anyway" or "Skip These".
  - Show polling spinner while `status === "processing"`.
  - On `status === "ready"` → show "Download Tailored Resume" button.
  - On `status === "error"` → show error message in red.
- Previous tailored resumes for this job: list with date + download link.

### 3b. New API methods in `client.ts`

```typescript
tailorResume: (jobId: number, payload: TailorResumeRequest) =>
  request<TailorResumeReadWithFlags>('/api/v1/jobs/${jobId}/tailor-resume', {
    method: 'POST', body: JSON.stringify(payload)
  }),
getTailoredResume: (id: number) =>
  request<TailoredResumeRead>(`/api/v1/tailored-resumes/${id}`),
downloadTailoredResumeUrl: (id: number) =>
  `${API_BASE_URL}/api/v1/tailored-resumes/${id}/download`,
listTailoredResumes: (jobId: number, candidateId: number) =>
  request<TailoredResumeRead[]>(`/api/v1/jobs/${jobId}/tailored-resumes?candidate_id=${candidateId}`),
```

### 3c. New types in `types/index.ts`

```typescript
export type TailoredResumeRead = {
  id: number;
  candidate_id: number;
  job_id: number;
  status: "pending" | "processing" | "ready" | "error";
  filename: string | null;
  notes: string | null;
  created_at: string;
  error_message: string | null;
};

export type TailorResumeRequest = {
  candidate_id: number;
  notes?: string | null;
  confirm_flagged_skills?: string[] | null;
};
```

---

## Step 4 — Environment Variables

Add to Railway Backend service:

| Variable | Value |
|---|---|
| `OPENAI_API_KEY` | sk-... from OpenAI dashboard |

Add to `app/core/config.py`:
```python
openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
```

---

## Step 5 — Merging Back to `main`

When the module is complete, merge via:

```bash
git checkout codex/resume-tailoring-workflow
git rebase main          # or: git merge main
# resolve conflicts if any, then:
git checkout main
git merge codex/resume-tailoring-workflow
git push
```

### Expected conflict files — resolve as follows:

| File | How to resolve |
|---|---|
| `apps/backend/app/api/routes.py` | Keep ALL existing routes, append new tailoring routes at the end. Do not remove any existing imports. |
| `apps/backend/requirements.txt` | Accept both sets of packages (union). Do not downgrade existing pinned versions. |
| `apps/frontend/src/pages/JobMatchDetailPage.tsx` | This is a new file — should not conflict. If it does, keep the Codex version. |
| `apps/frontend/src/api/client.ts` | Keep all existing methods, add new tailoring methods. |
| `apps/frontend/src/types/index.ts` | Keep all existing types, add new ones. |
| `apps/frontend/src/styles.css` | Append new styles at the bottom, do not override existing classes. |

### Non-negotiable merge rules:

- ✅ Master resume (`UPLOAD_DIR/candidates/.../resume.*`) must remain unchanged after merge.
- ✅ Tailored DOCX files are separate artifacts in `UPLOAD_DIR/tailored/` — never overwrite originals.
- ✅ Employee access control: employees can only tailor resumes for their **assigned** candidates. Keep the `assigned_employee` check that already exists in the codebase.
- ✅ Unsupported JD skills must be flagged for confirmation (not silently added). This is enforced in `resume_tailor.py` — do not remove the `flagged_skills` logic during merge.
- ✅ Tailored Word output only works with DOCX master resumes — the error for PDF/TXT inputs must remain.

---

## Step 6 — Testing Checklist

Before opening PR / merging to `main`:

- [ ] `alembic upgrade head` runs without error on local + Railway.
- [ ] `POST /api/v1/jobs/{job_id}/tailor-resume` returns 200 with DOCX master resume present.
- [ ] Returns flagged skills list when non-existent skills are requested.
- [ ] Download endpoint returns a valid `.docx` file.
- [ ] Employee cannot tailor resume for a candidate not assigned to them (403).
- [ ] Master resume file unchanged after tailoring.
- [ ] React page renders JD text correctly (no blank pane).
- [ ] Polling works: spinner → download button transition.
- [ ] `npm run build` has zero TypeScript errors.
