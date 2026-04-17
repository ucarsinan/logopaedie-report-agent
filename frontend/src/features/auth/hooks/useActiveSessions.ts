"use client";
import { useCallback, useEffect, useState } from "react";

export interface ActiveSession {
  id: string;
  user_agent: string | null;
  ip_address: string | null;
  created_at: string;
  last_used_at: string;
  expires_at: string;
  is_current: boolean;
}

export function useActiveSessions() {
  const [sessions, setSessions] = useState<ActiveSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/auth/sessions", { credentials: "include" });
      if (!res.ok) throw new Error();
      setSessions(await res.json());
    } catch {
      setError("Sitzungen konnten nicht geladen werden.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function revoke(id: string): Promise<{ current_session_revoked?: boolean }> {
    const res = await fetch(`/api/auth/sessions/${id}`, {
      method: "DELETE",
      credentials: "include",
    });
    if (!res.ok) throw new Error("revoke failed");
    const body = await res.json().catch(() => ({}));
    if (!body.current_session_revoked) {
      setSessions((s) => s.filter((x) => x.id !== id));
    }
    return body;
  }

  return { sessions, loading, error, revoke };
}
