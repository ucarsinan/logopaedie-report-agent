"use client";

import { useActiveSessions } from "../hooks/useActiveSessions";

export function ActiveSessionsList() {
  const { sessions, loading, error, revoke } = useActiveSessions();

  async function onRevoke(id: string) {
    const res = await revoke(id);
    if (res.current_session_revoked) {
      window.location.replace("/login");
    }
  }

  if (loading) return <p className="text-sm">Lädt…</p>;
  if (error)
    return (
      <p role="alert" className="text-sm text-red-600">
        {error}
      </p>
    );

  return (
    <ul className="divide-y divide-neutral-200 dark:divide-neutral-800">
      {sessions.map((s) => (
        <li
          key={s.id}
          className="py-3 flex items-center justify-between gap-4"
        >
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-medium truncate">
                {s.user_agent ?? "Unbekanntes Gerät"}
              </span>
              {s.is_current && (
                <span className="text-xs rounded bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 px-2 py-0.5">
                  Dieses Gerät
                </span>
              )}
            </div>
            <div className="text-xs text-neutral-500 dark:text-neutral-400">
              {s.ip_address ?? "—"} · zuletzt aktiv{" "}
              {new Date(s.last_used_at).toLocaleString("de-DE")}
            </div>
          </div>
          <button
            type="button"
            onClick={() => onRevoke(s.id)}
            className="text-sm text-red-600 hover:underline"
          >
            Widerrufen
          </button>
        </li>
      ))}
    </ul>
  );
}
