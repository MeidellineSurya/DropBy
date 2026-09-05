const API_BASE_URL = "http://localhost:8000/api/v1";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, options);
  if (!response.ok) {
    throw new Error(`Request to ${path} failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  createDrop: (payload: Record<string, unknown>) =>
    request("/business/drops", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  listDrops: () => request("/business/drops"),
  confirmRedemption: (redemptionId: string, participantCount: number) =>
    request(`/redemptions/${redemptionId}/confirm`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ participant_count: participantCount }),
    }),
  dropFunnel: (dropId: string) => request(`/business/analytics/drops/${dropId}`),
};
