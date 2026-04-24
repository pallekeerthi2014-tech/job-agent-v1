import type {
  Application,
  ApplicationCreatePayload,
  Candidate,
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
  WorkQueueItem
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
    })
};
