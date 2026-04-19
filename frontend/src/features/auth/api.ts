import type { LoginResponse, User } from "./types";

async function jsonFetch<T>(url: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(url, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(init.headers || {}) },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail ?? res.statusText);
  }
  return res.json() as Promise<T>;
}

export const authApi = {
  register: (email: string, password: string) =>
    jsonFetch<{ message: string; auto_verified: boolean }>("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  login: (email: string, password: string) =>
    jsonFetch<LoginResponse>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  loginTwoFactor: (challenge_id: string, code: string) =>
    jsonFetch<LoginResponse>("/api/auth/login/2fa", {
      method: "POST",
      body: JSON.stringify({ challenge_id, code }),
    }),

  logout: () =>
    jsonFetch<{ ok: true }>("/api/auth/logout", { method: "POST" }),

  me: () => jsonFetch<User>("/api/auth/me"),

  resendVerification: (email: string) =>
    jsonFetch<{ message: string }>("/api/auth/resend-verification", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),

  verifyEmail: (token: string) =>
    jsonFetch<{ ok: true }>("/api/auth/verify-email", {
      method: "POST",
      body: JSON.stringify({ token }),
    }),

  requestPasswordReset: (email: string) =>
    jsonFetch<{ message: string }>("/api/auth/password/reset/request", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),

  confirmPasswordReset: (token: string, new_password: string) =>
    jsonFetch<{ ok: true }>("/api/auth/password/reset/confirm", {
      method: "POST",
      body: JSON.stringify({ token, new_password }),
    }),

  changePassword: (current_password: string, new_password: string) =>
    jsonFetch<{ ok: true }>("/api/auth/password/change", {
      method: "POST",
      body: JSON.stringify({ current_password, new_password }),
    }),
};
