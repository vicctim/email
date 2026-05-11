import axios from "axios";
import Cookies from "js-cookie";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const api = axios.create({
  baseURL: API_URL,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  const token = Cookies.get("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response?.status === 401) {
      Cookies.remove("token");
      if (typeof window !== "undefined" && !window.location.pathname.includes("/login")) {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

export default api;

// ── Auth ──────────────────────────────────
export async function login(username: string, password: string) {
  const { data } = await api.post("/api/auth/login", { username, password });
  Cookies.set("token", data.access_token, { expires: 7 });
  return data;
}

export function logout() {
  Cookies.remove("token");
  window.location.href = "/login";
}

export function isAuthenticated(): boolean {
  return !!Cookies.get("token");
}

// ── Sites ─────────────────────────────────
export const sitesApi = {
  list: () => api.get("/api/sites").then((r) => r.data),
  get: (id: number) => api.get(`/api/sites/${id}`).then((r) => r.data),
  create: (data: Record<string, unknown>) => api.post("/api/sites", data).then((r) => r.data),
  update: (id: number, data: Record<string, unknown>) => api.put(`/api/sites/${id}`, data).then((r) => r.data),
  delete: (id: number) => api.delete(`/api/sites/${id}`),
  test: (id: number) => api.post(`/api/sites/${id}/test`).then((r) => r.data),
};

// ── Email Accounts ────────────────────────
export const accountsApi = {
  list: () => api.get("/api/accounts").then((r) => r.data),
  get: (id: number) => api.get(`/api/accounts/${id}`).then((r) => r.data),
  create: (data: Record<string, unknown>) => api.post("/api/accounts", data).then((r) => r.data),
  update: (id: number, data: Record<string, unknown>) => api.put(`/api/accounts/${id}`, data).then((r) => r.data),
  delete: (id: number) => api.delete(`/api/accounts/${id}`),
  test: (id: number) => api.post(`/api/accounts/${id}/test`).then((r) => r.data),
};

// ── Rules ─────────────────────────────────
export const rulesApi = {
  list: () => api.get("/api/rules").then((r) => r.data),
  get: (id: number) => api.get(`/api/rules/${id}`).then((r) => r.data),
  create: (data: Record<string, unknown>) => api.post("/api/rules", data).then((r) => r.data),
  update: (id: number, data: Record<string, unknown>) => api.put(`/api/rules/${id}`, data).then((r) => r.data),
  delete: (id: number) => api.delete(`/api/rules/${id}`),
  toggle: (id: number) => api.patch(`/api/rules/${id}/toggle`).then((r) => r.data),
};

// ── Queue ─────────────────────────────────
export const queueApi = {
  list: (params?: Record<string, string>) => api.get("/api/queue", { params }).then((r) => r.data),
  preview: (id: number) => api.get(`/api/queue/${id}/preview`).then((r) => r.data),
  cancel: (id: number) => api.post(`/api/queue/${id}/cancel`).then((r) => r.data),
  retry: (id: number) => api.post(`/api/queue/${id}/retry`).then((r) => r.data),
};

// ── Logs ──────────────────────────────────
export const logsApi = {
  list: (params?: Record<string, string>) => api.get("/api/logs", { params }).then((r) => r.data),
  get: (id: number) => api.get(`/api/logs/${id}`).then((r) => r.data),
};

// ── Dashboard ─────────────────────────────
export const dashboardApi = {
  stats: () => api.get("/api/dashboard/stats").then((r) => r.data),
  recent: () => api.get("/api/dashboard/recent").then((r) => r.data),
};

// ── Settings ──────────────────────────────
export const settingsApi = {
  get: () => api.get("/api/settings").then((r) => r.data),
  update: (data: Record<string, unknown>) => api.put("/api/settings", data).then((r) => r.data),
};
