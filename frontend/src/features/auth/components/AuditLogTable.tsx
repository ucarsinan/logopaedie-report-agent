"use client";

import { useState } from "react";
import { useAuditLog } from "../hooks/useAuditLog";

const EVENTS = [
  "",
  "user.register",
  "user.email_verified",
  "login.success",
  "login.fail",
  "login.2fa_required",
  "login.2fa_success",
  "login.2fa_fail",
  "logout",
  "session.revoke",
  "session.refresh_reuse_detected",
  "password.change",
  "password.reset_requested",
  "password.reset_completed",
  "2fa.enable",
  "2fa.disable",
  "admin.user_lock",
  "admin.user_unlock",
  "admin.2fa_disable",
];

export function AuditLogTable() {
  const { data, params, setParams, loading, error } = useAuditLog();
  const [eventFilter, setEventFilter] = useState("");
  const [userFilter, setUserFilter] = useState("");

  function applyFilter() {
    setParams({ ...params, event: eventFilter, user_id: userFilter, offset: 0 });
  }

  function nextPage() {
    setParams({ ...params, offset: params.offset + params.limit });
  }
  function prevPage() {
    setParams({ ...params, offset: Math.max(0, params.offset - params.limit) });
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2 items-end">
        <label className="flex flex-col">
          <span className="text-xs">Event</span>
          <select
            value={eventFilter}
            onChange={(e) => setEventFilter(e.target.value)}
            className="rounded border px-2 py-1 bg-white dark:bg-neutral-900"
          >
            {EVENTS.map((e) => (
              <option key={e} value={e}>
                {e || "(alle)"}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col">
          <span className="text-xs">User-ID</span>
          <input
            type="text"
            value={userFilter}
            onChange={(e) => setUserFilter(e.target.value)}
            className="rounded border px-2 py-1 bg-white dark:bg-neutral-900"
          />
        </label>
        <button
          type="button"
          onClick={applyFilter}
          className="rounded bg-blue-600 text-white px-3 py-1"
        >
          Filter anwenden
        </button>
      </div>
      {error && (
        <p role="alert" className="text-sm text-red-600">
          {error}
        </p>
      )}
      {loading && <p className="text-sm">Lädt…</p>}
      {!loading && data.items.length === 0 && (
        <p className="text-sm text-neutral-500">Keine Einträge.</p>
      )}
      {data.items.length > 0 && (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left border-b">
              <th className="py-2">Zeit</th>
              <th>Event</th>
              <th>User</th>
              <th>IP</th>
            </tr>
          </thead>
          <tbody>
            {data.items.map((row) => (
              <tr key={row.id} className="border-b last:border-0">
                <td className="py-1">
                  {new Date(row.created_at).toLocaleString("de-DE")}
                </td>
                <td>{row.event}</td>
                <td className="font-mono text-xs">{row.user_id ?? "—"}</td>
                <td>{row.ip_address ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <div className="flex gap-2 justify-end">
        <button
          type="button"
          onClick={prevPage}
          disabled={params.offset === 0}
          className="rounded border px-3 py-1 disabled:opacity-50"
        >
          Zurück
        </button>
        <button
          type="button"
          onClick={nextPage}
          disabled={params.offset + params.limit >= data.total}
          className="rounded border px-3 py-1 disabled:opacity-50"
        >
          Weiter
        </button>
      </div>
    </div>
  );
}
