import AsyncStorage from "@react-native-async-storage/async-storage";
import { Platform } from "react-native";

import type {
  ConnectionSummary,
  Conversation,
  DropSnapshot,
  GroupSnapshot,
  Message,
  RecentSquadmate,
  TokenResponse,
  UserProfile,
  UserSearchResult,
} from "../types";

const fallbackHost = Platform.OS === "android" ? "10.0.2.2" : "localhost";
export const API_ORIGIN = (
  process.env.EXPO_PUBLIC_API_URL ?? `http://${fallbackHost}:8000`
).replace(/\/$/, "");
const API_BASE_URL = `${API_ORIGIN}/api/v1`;
const TOKEN_KEY = "dropby.access-token";

let accessToken: string | null = null;

export async function setAccessToken(token: string | null): Promise<void> {
  accessToken = token;
  if (token) {
    await AsyncStorage.setItem(TOKEN_KEY, token);
  } else {
    await AsyncStorage.removeItem(TOKEN_KEY);
  }
}

export async function restoreAccessToken(): Promise<string | null> {
  accessToken = await AsyncStorage.getItem(TOKEN_KEY);
  return accessToken;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const headers = new Headers(options?.headers);
  if (options?.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = body?.detail;
    const message = Array.isArray(detail)
      ? detail.map((item) => item.msg).join(", ")
      : detail ?? `Request failed (${response.status})`;
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

export const api = {
  register: (email: string, password: string, displayName: string) =>
    request<TokenResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, display_name: displayName }),
    }),
  login: (email: string, password: string) =>
    request<TokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  me: () => request<UserProfile>("/auth/me"),
  onboarding: (
    displayName: string,
    preferences: string[],
    locationPermission: "denied" | "while_using" | "always",
  ) =>
    request<UserProfile>("/auth/onboarding", {
      method: "PUT",
      body: JSON.stringify({
        display_name: displayName,
        preferences,
        location_permission: locationPermission,
      }),
    }),
  locationPing: (latitude: number, longitude: number) =>
    request<{ drops: DropSnapshot[] }>("/drops/location/ping", {
      method: "POST",
      body: JSON.stringify({ latitude, longitude }),
    }),
  getDrop: (dropId: string) => request<DropSnapshot>(`/drops/${dropId}`),
  createGroup: (dropId: string) =>
    request<GroupSnapshot>("/groups", {
      method: "POST",
      body: JSON.stringify({ drop_id: dropId, open_to_nearby: true }),
    }),
  getGroup: (groupId: string) => request<GroupSnapshot>(`/groups/${groupId}`),
  joinGroup: (groupId: string) =>
    request<GroupSnapshot>(`/groups/${groupId}/join`, { method: "POST" }),
  leaveGroup: (groupId: string) =>
    request<GroupSnapshot | null>(`/groups/${groupId}/leave`, { method: "POST" }),
  // The business confirms a claim by scanning this — check-in isn't
  // something the consumer does at all beyond displaying the code. See
  // apps/api/app/services/redemption.py.
  getSquadQr: (groupId: string) =>
    request<{ qr_token: string }>(`/groups/${groupId}/qr`),
  searchUsers: (query: string) =>
    request<UserSearchResult[]>(`/connections/search?q=${encodeURIComponent(query)}`),
  getRecentSquadmates: () => request<RecentSquadmate[]>("/connections/recent-squadmates"),
  getIncomingRequests: () => request<ConnectionSummary[]>("/connections/requests"),
  sendConnectionRequest: (addresseeId: string) =>
    request<ConnectionSummary>("/connections/requests", {
      method: "POST",
      body: JSON.stringify({ addressee_id: addresseeId }),
    }),
  respondToRequest: (connectionId: string, accept: boolean) =>
    request<ConnectionSummary>(`/connections/requests/${connectionId}/respond`, {
      method: "POST",
      body: JSON.stringify({ accept }),
    }),
  getConnections: () => request<ConnectionSummary[]>("/connections"),
  getConversations: () => request<Conversation[]>("/chat/conversations"),
  getMessages: (connectionId: string) =>
    request<Message[]>(`/chat/conversations/${connectionId}/messages`),
  sendMessage: (connectionId: string, body: string) =>
    request<Message>(`/chat/conversations/${connectionId}/messages`, {
      method: "POST",
      body: JSON.stringify({ body }),
    }),
};
