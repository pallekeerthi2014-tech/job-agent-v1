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
  assigned_employee?: number | null;
  work_authorization?: string | null;
  years_experience?: number | null;
  salary_min?: number | null;
  salary_unit?: string | null;
  active: boolean;
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
