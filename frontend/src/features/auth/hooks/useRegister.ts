"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { authApi } from "@/features/auth/api";

export function useRegister() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const router = useRouter();

  async function submit(email: string, password: string) {
    setLoading(true);
    setError(null);
    try {
      const res = await authApi.register(email, password);
      if (res.auto_verified) {
        router.push("/login");
      } else {
        setDone(true);
      }
    } catch {
      setError("Registrierung fehlgeschlagen. Bitte später erneut versuchen.");
    } finally {
      setLoading(false);
    }
  }

  return { submit, loading, error, done };
}
