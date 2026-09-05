// Minimal localStorage-backed session for the business dashboard. There's no
// refresh-token flow yet — a business simply logs in again once the JWT expires.
const TOKEN_KEY = "dropby_business_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export function isLoggedIn(): boolean {
  return getToken() !== null;
}
