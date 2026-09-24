import type { AuthResponse, Dashboard, Task, TaskInput, User } from "../types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const TOKEN_KEY = "sstm_access_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null) {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

export class ApiError extends Error {
  status: number;
  fieldErrors: { field: string; message: string }[];

  constructor(message: string, status: number, fieldErrors: { field: string; message: string }[] = []) {
    super(message);
    this.status = status;
    this.fieldErrors = fieldErrors;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    ...(options.body ? { "Content-Type": "application/json" } : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers as Record<string, string> | undefined),
  };

  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });

  if (response.status === 204) {
    return undefined as T;
  }

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const message = data.detail && typeof data.detail === "string" ? data.detail : "Something went wrong.";
    throw new ApiError(message, response.status, data.errors || []);
  }

  return data as T;
}

export const api = {
  register: (name: string, email: string, password: string) =>
    request<AuthResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ name, email, password }),
    }),

  login: (email: string, password: string) =>
    request<AuthResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  logout: () => request<void>("/auth/logout", { method: "POST" }),

  me: () => request<User>("/auth/me"),

  listTasks: (params: { subject?: string; completed?: boolean; overdueOnly?: boolean; sortBy?: "priority" | "deadline" } = {}) => {
    const search = new URLSearchParams();
    if (params.subject) search.set("subject", params.subject);
    if (params.completed !== undefined) search.set("completed", String(params.completed));
    if (params.overdueOnly) search.set("overdue_only", "true");
    if (params.sortBy) search.set("sort_by", params.sortBy);
    const qs = search.toString();
    return request<Task[]>(`/tasks${qs ? `?${qs}` : ""}`);
  },

  getTask: (id: string) => request<Task>(`/tasks/${id}`),

  createTask: (input: TaskInput) =>
    request<Task>("/tasks", { method: "POST", body: JSON.stringify(input) }),

  updateTask: (id: string, input: Partial<TaskInput> & { completed?: boolean }) =>
    request<Task>(`/tasks/${id}`, { method: "PATCH", body: JSON.stringify(input) }),

  completeTask: (id: string) => request<Task>(`/tasks/${id}/complete`, { method: "POST" }),

  deleteTask: (id: string) => request<void>(`/tasks/${id}`, { method: "DELETE" }),

  upcoming: (days = 7) => request<Task[]>(`/tasks/upcoming?days=${days}`),

  dashboard: () => request<Dashboard>("/dashboard"),
};
