"use client";
import { useCallback, useEffect, useState } from "react";

export interface AuditEntry {
  id: string;
  user_id: string | null;
  event: string;
  ip_address: string | null;
  user_agent: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface AuditPage {
  items: AuditEntry[];
  total: number;
}

interface Params {
  event: string;
  user_id: string;
  offset: number;
  limit: number;
}

export function useAuditLog(initial: Partial<Params> = {}) {
  const [params, setParams] = useState<Params>({
    event: "",
    user_id: "",
    offset: 0,
    limit: 50,
    ...initial,
  });
  const [data, setData] = useState<AuditPage>({ items: [], total: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const qs = new URLSearchParams();
    if (params.event) qs.set("event", params.event);
    if (params.user_id) qs.set("user_id", params.user_id);
    qs.set("limit", String(params.limit));
    qs.set("offset", String(params.offset));
    try {
      const res = await fetch(`/api/admin/audit?${qs.toString()}`, {
        credentials: "include",
      });
      if (!res.ok) throw new Error();
      setData(await res.json());
    } catch {
      setError("Audit-Log konnte nicht geladen werden.");
    } finally {
      setLoading(false);
    }
  }, [params]);

  useEffect(() => {
    void load();
  }, [load]);

  return { data, params, setParams, loading, error, reload: load };
}
