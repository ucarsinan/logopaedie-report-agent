"use client";
import { useState } from "react";
import { authApi } from "@/features/auth/api";
import type { LoginResponse } from "@/features/auth/types";

export function useLogin() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(
    email: string,
    password: string,
  ): Promise<LoginResponse | null> {
    setLoading(true);
    setError(null);
    try {
      const res = await authApi.login(email, password);
      return res;
    } catch {
      setError("Email oder Passwort ist falsch.");
      return null;
    } finally {
      setLoading(false);
    }
  }

  async function submit2fa(
    challenge_id: string,
    code: string,
  ): Promise<LoginResponse | null> {
    setLoading(true);
    setError(null);
    try {
      return await authApi.loginTwoFactor(challenge_id, code);
    } catch {
      setError("Code ist ungültig oder abgelaufen.");
      return null;
    } finally {
      setLoading(false);
    }
  }

  return { submit, submit2fa, loading, error };
}
