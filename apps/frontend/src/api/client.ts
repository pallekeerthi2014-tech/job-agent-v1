import type {
  AlertRecipient,
  AlertRecipientCreatePayload,
  AlertRecipientUpdatePayload,
  AnalyticsOverview,
  Application,
  ApplicationCreatePayload,
  Candidate,
  CandidateCreatePayload,
  CandidatePreference,
  CandidateProfileUpdatePayload,
  CandidateSelfRegisterPayload,
  CandidateSkill,
  CandidateUpdatePayload,
  Employee,
  ForgotPasswordPayload,
  ForgotPasswordResponse,
  Job,
  LoginPayload,
  LoginResponse,
  Match,
  PaginatedResponse,
  ResetPasswordPayload,
  User,
  UserCreatePayload,
  UserUpdatePayload,
  WorkQueueItem,
  WorkQueueReportPayload
  AdapterTypeList,
  SourceCreate,
  SourceRead,
  SourceRunResult,
  SourceTestRequest,
  SourceTestResult,
  SourceUpdate,
} from "../types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;
const ACCESS_TOKEN_KEY = "job-agent-access-token";

export function getStoredAccessToken() {
  return window.localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function setStoredAccessToken(token: string) {
  window.localStorage.setItem(ACCESS_TOKEN_KEY, token);
}

export function clearStoredAccessToken() {
  window.localStorage.removeItem(ACCESS_TOKEN_KEY);
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const token = getStoredAccessToken();
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options?.headers ?? {})
    },
    ...options
  });

  // 204 No Content Ã¢ÂÂ return empty object (DELETE endpoints)
  if (response.status === 204) {
    return {} as T;
  }

  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

function buildQuery(params: Record<string, string | number | undefined | null>) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      query.set(key, String(value));
    }
  });
  const value = query.toString();
  return value ? `?${value}` : "";
}

export const apiClient = {
  login: (payload: LoginPayload) =>
    request<LoginResponse>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  forgotPassword: (payload: ForgotPasswordPayload) =>
    request<ForgotPasswordResponse>("/api/v1/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  resetPassword: (payload: ResetPasswordPayload) =>
    request<{ message: string }>("/api/v1/auth/reset-password", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  getMe: () => request<User>("/api/v1/auth/me"),
  getUsers: () => request<User[]>("/api/v1/admin/users"),
  createUser: (payload: UserCreatePayload) =>
    request<User>("/api/v1/admin/users", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  updateUser: (userId: number, payload: UserUpdatePayload) =>
    request<User>(`/api/v1/admin/users/${userId}`, {
      method: "PUT",
      body: JSON.stringify(payload)
    }),
  getCandidates: (params?: { limit?: number; offset?: number; employee_id?: number }) =>
    request<PaginatedResponse<Candidate>>(`/api/v1/candidates${buildQuery(params ?? {})}`),
  getEmployees: () => request<Employee[]>("/api/v1/employees"),
  getJobs: (params?: { limit?: number; offset?: number; source?: string; posted_date?: string }) =>
    request<PaginatedResponse<Job>>(`/api/v1/jobs${buildQuery(params ?? {})}`),
  getMatches: (params?: {
    limit?: number;
    offset?: number;
    candidate_id?: number;
    employee_id?: number;
    score?: number;
    priority?: number;
    sort_by?: string;
    sort_order?: string;
  }) => request<PaginatedResponse<Match>>(`/api/v1/matches${buildQuery(params ?? {})}`),
  getApplications: (params?: { limit?: number; offset?: number; candidate_id?: number; employee_id?: number }) =>
    request<PaginatedResponse<Application>>(`/api/v1/applications${buildQuery(params ?? {})}`),
  getWorkQueues: (params?: {
    limit?: number;
    offset?: number;
    candidate_id?: number;
    employee_id?: number;
    priority?: string;
    status?: string;
    sort_by?: string;
    sort_order?: string;
  }) => request<PaginatedResponse<WorkQueueItem>>(`/api/v1/work-queues${buildQuery(params ?? {})}`),
  createApplication: (payload: ApplicationCreatePayload) =>
    request<Application>("/api/v1/applications", {
      method: "POST",
      body: JSON.stringify(payload)
    }),

  // Ã¢ÂÂÃ¢ÂÂ Phase 3: Candidate CRUD Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
  createCandidate: (payload: CandidateCreatePayload) =>
    request<Candidate>("/api/v1/candidates", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  updateCandidate: (id: number, payload: CandidateUpdatePayload) =>
    request<Candidate>(`/api/v1/candidates/${id}`, {
      method: "PUT",
      body: JSON.stringify(payload)
    }),
  deleteCandidate: (id: number) =>
    request<{ message: string }>(`/api/v1/candidates/${id}`, { method: "DELETE" }),

  // Ã¢ÂÂÃ¢ÂÂ Phase 3: Candidate preferences & skills Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
  // Backend uses flat routes: GET /candidate-preferences (all), PUT /candidate-preferences/{id}
  getCandidatePreferences: (candidateId: number) =>
    request<CandidatePreference[]>("/api/v1/candidate-preferences").then(
      (all) => all.find((p) => p.candidate_id === candidateId) ?? null
    ),
  upsertCandidatePreferences: (candidateId: number, payload: Omit<CandidatePreference, "candidate_id">) =>
    request<CandidatePreference>(`/api/v1/candidate-preferences/${candidateId}`, {
      method: "PUT",
      body: JSON.stringify(payload)
    }),
  // Backend: GET /candidate-skills?candidate_id={id}
  getCandidateSkills: (candidateId: number) =>
    request<CandidateSkill[]>(`/api/v1/candidate-skills?candidate_id=${candidateId}`),

  // Ã¢ÂÂÃ¢ÂÂ Phase 3: Resume upload Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
  uploadResume: (candidateId: number, file: File) => {
    const token = getStoredAccessToken();
    const formData = new FormData();
    formData.append("file", file);
    return fetch(`${API_BASE_URL}/api/v1/candidates/${candidateId}/resume`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData
    }).then((res) => {
      if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
      return res.json() as Promise<{ message: string; filename: string }>;
    });
  },
  getResumeUrl: (candidateId: number) =>
    `${API_BASE_URL}/api/v1/candidates/${candidateId}/resume`,

  // Ã¢ÂÂÃ¢ÂÂ Phase 3: Work queue reporting Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
  reportWorkQueueItem: (queueId: number, payload: WorkQueueReportPayload) =>
    request<WorkQueueItem>(`/api/v1/work-queues/${queueId}/report`, {
      method: "POST",
      body: JSON.stringify(payload)
    }),

  // Ã¢ÂÂÃ¢ÂÂ Phase 3: WhatsApp recipient management Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
  getWhatsappRecipients: () =>
    request<AlertRecipient[]>("/api/v1/admin/whatsapp-recipients"),
  createWhatsappRecipient: (payload: AlertRecipientCreatePayload) =>
    request<AlertRecipient>("/api/v1/admin/whatsapp-recipients", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  updateWhatsappRecipient: (id: number, payload: AlertRecipientUpdatePayload) =>
    request<AlertRecipient>(`/api/v1/admin/whatsapp-recipients/${id}`, {
      method: "PUT",
      body: JSON.stringify(payload)
    }),
  deleteWhatsappRecipient: (id: number) =>
    request<{ message: string }>(`/api/v1/admin/whatsapp-recipients/${id}`, { method: "DELETE" }),

  // Ã¢ÂÂÃ¢ÂÂ Phase 3: Employee management Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
  updateEmployee: (id: number, payload: { name?: string; email?: string }) =>
    request<Employee>(`/api/v1/admin/employees/${id}`, {
      method: "PUT",
      body: JSON.stringify(payload)
    }),
  deleteEmployee: (id: number) =>
    request<{ message: string }>(`/api/v1/admin/employees/${id}`, { method: "DELETE" }),

  // Ã¢ÂÂÃ¢ÂÂ Phase 3: Analytics Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
  getAnalyticsOverview: () =>
    request<AnalyticsOverview>("/api/v1/analytics/overview"),

  // Ã¢ÂÂÃ¢ÂÂ Candidate Portal Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
  candidateRegister: (payload: CandidateSelfRegisterPayload) =>
    request<LoginResponse>("/api/v1/portal/register", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  portalGetProfile: () =>
    request<Candidate>("/api/v1/portal/me"),
  portalUpdateProfile: (payload: CandidateProfileUpdatePayload) =>
    request<Candidate>("/api/v1/portal/me", {
      method: "PATCH",
      body: JSON.stringify(payload)
    }),
  portalGetMatches: (params?: { limit?: number; offset?: number }) =>
    request<PaginatedResponse<Match>>(`/api/v1/portal/matches${buildQuery(params ?? {})}`),
  portalGetJob: (jobId: number) =>
    request<Job>(`/api/v1/portal/jobs/${jobId}`),
  portalUploadResume: (file: File) => {
    const token = getStoredAccessToken();
    const formData = new FormData();
    formData.append("file", file);
    return fetch(`${API_BASE_URL}/api/v1/portal/me/resume`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData
    }).then((res) => {
      if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
      return res.json() as Promise<Candidate>;
    });
  },
  portalResumeUrl: () =>
    `${API_BASE_URL}/api/v1/portal/me/resume`,

  // âââ Source / Feed Management âââââââââââââââââââââââââââââââââââââââââââââ
  listSourceTypes: () =>
    request<AdapterTypeList>("/api/v1/admin/source-types"),

  listSources: () =>
    request<SourceRead[]>("/api/v1/admin/sources"),

  getSource: (id: number) =>
    request<SourceRead>(`/api/v1/admin/sources/${id}`),

  createSource: (payload: SourceCreate) =>
    request<SourceRead>("/api/v1/admin/sources", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),

  updateSource: (id: number, payload: SourceUpdate) =>
    request<SourceRead>(`/api/v1/admin/sources/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),

  deleteSource: (id: number) =>
    request<Record<string, never>>(`/api/v1/admin/sources/${id}`, {
      method: "DELETE",
    }),

  testSourceConfig: (payload: SourceTestRequest) =>
    request<SourceTestResult>("/api/v1/admin/sources/test", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),

  testExistingSource: (id: number) =>
    request<SourceTestResult>(`/api/v1/admin/sources/${id}/test`, {
      method: "POST",
    }),

  runSourceNow: (id: number) =>
    request<SourceRunResult>(`/api/v1/admin/sources/${id}/run-now`, {
      method: "POST",
    })
};
