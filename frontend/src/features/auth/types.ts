export type UserRole = "user" | "admin";

export interface User {
  id: string;
  email: string;
  role: UserRole;
  totp_enabled: boolean;
  created_at: string;
}

export type AuthState =
  | { status: "loading" }
  | { status: "authenticated"; user: User }
  | { status: "unauthenticated" };

export interface LoginSuccess {
  access_token: string;
  refresh_token: string;
  user: User;
}

export interface LoginTwoFactorRequired {
  step: "2fa_required";
  challenge_id: string;
}

export type LoginResponse = LoginSuccess | LoginTwoFactorRequired;
