"use client";
import { useState } from "react";
import { authApi } from "@/features/auth/api";

export function useRegister() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  async function submit(email: string, password: string) {
    setLoading(true);
    setError(null);
    try {
      await authApi.register(email, password);
      setDone(true);
    } catch {
      setError("Registrierung fehlgeschlagen. Bitte später erneut versuchen.");
    } finally {
      setLoading(false);
    }
  }

  return { submit, loading, error, done };
}
