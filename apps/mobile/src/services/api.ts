const API_BASE_URL = "http://localhost:8000/api/v1";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, options);
  if (!response.ok) {
    throw new Error(`Request to ${path} failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  locationPing: (lat: number, lng: number) =>
    request("/drops/location/ping", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ lat, lng }),
    }),
  getDrop: (dropId: string) => request(`/drops/${dropId}`),
  createGroup: (dropId: string) =>
    request("/groups", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ drop_id: dropId }),
    }),
};
