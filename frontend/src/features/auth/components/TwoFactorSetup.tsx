"use client";

import { useState } from "react";
import { QRCodeSVG } from "qrcode.react";

interface SetupPayload {
  secret: string;
  provisioning_uri: string;
}

export function TwoFactorSetup() {
  const [setup, setSetup] = useState<SetupPayload | null>(null);
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  async function startSetup() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/auth/2fa/setup", {
        method: "POST",
        credentials: "include",
      });
      if (!res.ok) throw new Error();
      setSetup(await res.json());
    } catch {
      setError("Einrichtung konnte nicht gestartet werden.");
    } finally {
      setLoading(false);
    }
  }

  async function enable() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/auth/2fa/enable", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code }),
      });
      if (!res.ok) throw new Error();
      setDone(true);
    } catch {
      setError("Code ist ungültig.");
    } finally {
      setLoading(false);
    }
  }

  if (done) {
    return (
      <p className="text-sm text-green-600">
        2FA aktiviert. Sie wurden von allen anderen Sitzungen abgemeldet.
      </p>
    );
  }

  if (!setup) {
    return (
      <button
        type="button"
        onClick={startSetup}
        disabled={loading}
        className="rounded bg-blue-600 text-white px-4 py-2 disabled:opacity-50"
      >
        2FA einrichten
      </button>
    );
  }

  const valid = /^\d{6}$/.test(code);

  return (
    <div className="space-y-4">
      <div
        data-testid="totp-qr"
        className="inline-block bg-white p-3 rounded border"
      >
        <QRCodeSVG value={setup.provisioning_uri} size={160} />
      </div>
      <p className="text-xs text-neutral-600 dark:text-neutral-400">
        Können Sie den QR-Code nicht scannen? Geben Sie den folgenden Schlüssel
        manuell in Ihre Authenticator-App ein:
      </p>
      <code className="block font-mono text-sm bg-neutral-100 dark:bg-neutral-800 p-2 rounded">
        {setup.secret}
      </code>
      <label className="block">
        <span className="text-sm font-medium">6-stelliger Code</span>
        <input
          type="text"
          inputMode="numeric"
          maxLength={6}
          value={code}
          onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
          className="mt-1 block w-full rounded border border-neutral-300 dark:border-neutral-700 px-3 py-2 bg-white dark:bg-neutral-900 tracking-widest text-center"
        />
      </label>
      {error && (
        <p role="alert" className="text-sm text-red-600">
          {error}
        </p>
      )}
      <button
        type="button"
        onClick={enable}
        disabled={!valid || loading}
        className="rounded bg-blue-600 text-white px-4 py-2 disabled:opacity-50"
      >
        Aktivieren
      </button>
    </div>
  );
}
