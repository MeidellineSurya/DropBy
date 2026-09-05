import { getToken } from "./auth";
import type {
  Business,
  BusinessDrop,
  BusinessOverview,
  DropFunnel,
} from "../types";

const API_BASE_URL = "http://localhost:8000/api/v1";

class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> | undefined),
  };
  if (token) headers.Authorization = `Bearer ${token}`;

  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    // FastAPI's validation errors (422s) send `detail` as an array of
    // {msg, loc, ...} objects, not a string — rendering that array
    // directly showed the literal text "[object Object]".
    const detail = body?.detail;
    const message = Array.isArray(detail)
      ? detail.map((item) => item.msg ?? JSON.stringify(item)).join(", ")
      : (detail ?? `Request to ${path} failed`);
    throw new ApiError(response.status, message);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export interface TokenResponse<TAccount> {
  access_token: string;
  token_type: string;
  business: TAccount;
}

export const api = {
  register: (payload: {
    name: string;
    category: string;
    owner_email: string;
    password: string;
    latitude: number;
    longitude: number;
    venue_capacity: number;
    description?: string;
    address?: string;
    phone?: string;
  }) =>
    request<TokenResponse<Business>>("/business/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  login: (owner_email: string, password: string) =>
    request<TokenResponse<Business>>("/business/auth/login", {
      method: "POST",
      body: JSON.stringify({ owner_email, password }),
    }),

  me: () => request<Business>("/business/auth/me"),

  createDrop: (payload: Record<string, unknown>) =>
    request<BusinessDrop>("/business/drops", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  listDrops: (status?: string) =>
    request<BusinessDrop[]>(
      `/business/drops${status ? `?drop_status=${status}` : ""}`,
    ),

  publishDrop: (dropId: string) =>
    request<BusinessDrop>(`/business/drops/${dropId}/publish`, { method: "POST" }),
  pauseDrop: (dropId: string) =>
    request<BusinessDrop>(`/business/drops/${dropId}/pause`, { method: "POST" }),
  resumeDrop: (dropId: string) =>
    request<BusinessDrop>(`/business/drops/${dropId}/resume`, { method: "POST" }),
  cancelDrop: (dropId: string) =>
    request<BusinessDrop>(`/business/drops/${dropId}/cancel`, { method: "POST" }),

  overview: () => request<BusinessOverview>("/business/analytics/overview"),
  dropFunnel: (dropId: string) =>
    request<DropFunnel>(`/business/analytics/drops/${dropId}`),
};

export { ApiError };
