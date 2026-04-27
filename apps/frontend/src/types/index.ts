export type PageMeta = {
  total: number;
  limit: number;
  offset: number;
};

export type PaginatedResponse<T> = {
  items: T[];
  meta: PageMeta;
};

export type Candidate = {
  id: number;
  name: string;
  email?: string | null;
  phone?: string | null;
  location?: string | null;
  assigned_employee?: number | null;
  work_authorization?: string | null;
  years_experience?: number | null;
  salary_min?: number | null;
  salary_unit?: string | null;
  active: boolean;
  resume_filename?: string | null;
};

export type Employee = {
  id: number;
  name: string;
  email: string;
};

export type UserRole = "super_admin" | "employee";

export type User = {
  id: number;
  name: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  employee_id?: number | null;
  last_login_at?: string | null;
};

export type Job = {
  id: number;
  source: string;
  title: string;
  company: string;
  location?: string | null;
  is_remote: boolean;
  employment_type?: string | null;
  salary_min?: number | null;
  salary_max?: number | null;
  posted_date?: string | null;
  apply_url?: string | null;
  canonical_apply_url?: string | null;
  description?: string | null;
  normalized_description_hash?: string | null;
  domain_tags: string[];
  visa_hints: string[];
  keywords_extracted: string[];
  dedupe_hash?: string | null;
  is_active: boolean;
  probable_duplicate_of_job_id?: number | null;
  duplicate_reasons: string[];
};

export type Match = {
  id: number;
  job_id: number;
  candidate_id: number;
  score: number;
  priority?: number | null;
  title_score?: number | null;
  domain_score?: number | null;
  skills_score?: number | null;
  experience_score?: number | null;
  employment_preference_score?: number | null;
  visa_score?: number | null;
  location_score?: number | null;
  explanation?: string | null;
  status?: string | null;
};

export type Application = {
  id: number;
  candidate_id: number;
  job_id: number;
  employee_id?: number | null;
  status?: string | null;
  notes?: string | null;
  applied_at: string;
};

export type WorkQueueItem = {
  id: number;
  employee_id: number;
  candidate_id: number;
  job_id: number;
  match_id?: number | null;
  priority_bucket: string;
  score: number;
  explanation?: string | null;
  status: string;
  report_status?: string | null;
  report_reason?: string | null;
  reported_at?: string | null;
  created_at: string;
  updated_at: string;
};

export type ApplicationCreatePayload = {
  candidate_id: number;
  job_id: number;
  employee_id?: number | null;
  status?: string | null;
  notes?: string | null;
};

export type PriorityFilter = "All" | "High" | "Medium" | "Low";

export type LoginPayload = {
  email: string;
  password: string;
};

export type LoginResponse = {
  access_token: string;
  token_type: string;
  user: User;
};

export type ForgotPasswordPayload = {
  email: string;
};

export type ForgotPasswordResponse = {
  message: string;
  delivery: "email" | "preview";
  reset_token?: string | null;
  reset_url?: string | null;
};

export type ResetPasswordPayload = {
  token: string;
  password: string;
};

export type UserCreatePayload = {
  name: string;
  email: string;
  password: string;
  role: UserRole;
  is_active: boolean;
  employee_id?: number | null;
};

export type UserUpdatePayload = {
  name?: string;
  role?: UserRole;
  is_active?: boolean;
  employee_id?: number | null;
  password?: string;
};

// ── Phase 3 types ─────────────────────────────────────────────────────────────

export type AlertRecipient = {
  id: number;
  phone_number: string;
  label?: string | null;
  is_active: boolean;
  created_at: string;
};

export type CandidatePreference = {
  candidate_id: number;
  preferred_titles: string[];
  employment_preferences: string[];
  location_preferences: string[];
  domain_expertise: string[];
  must_have_keywords: string[];
  exclude_keywords: string[];
};

export type CandidateSkill = {
  candidate_id: number;
  skill_name: string;
  years_used?: number | null;
};

export type CandidateCreatePayload = {
  name: string;
  email?: string | null;
  phone?: string | null;
  location?: string | null;
  assigned_employee?: number | null;
  work_authorization?: string | null;
  years_experience?: number | null;
  salary_min?: number | null;
  salary_unit?: string | null;
  active?: boolean;
};

export type CandidateUpdatePayload = Partial<CandidateCreatePayload>;

export type AlertRecipientCreatePayload = {
  phone_number: string;
  label?: string | null;
  is_active?: boolean;
};

export type AlertRecipientUpdatePayload = {
  label?: string | null;
  is_active?: boolean;
};

export type WorkQueueReportPayload = {
  report_status: "invalid" | "outdated" | "not_relevant";
  report_reason?: string | null;
};

export type AnalyticsOverview = {
  jobs_by_source: { source: string; count: number; latest_posted: string | null }[];
  freshness: { status: string; count: number }[];
  funnel: {
    total_raw: number;
    total_normalized: number;
    total_matched: number;
    total_queued: number;
    total_applied: number;
  };
  reports_by_source: { source: string; total: number; invalid: number; outdated: number; not_relevant: number }[];
  top_candidates: { candidate_id: number; candidate_name: string; match_count: number; avg_score: number }[];
};
