import type {
  Application,
  ApplicationCreatePayload,
  Candidate,
  Employee,
  Job,
  Match,
  PaginatedResponse,
  WorkQueueItem
} from "../types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json"
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
