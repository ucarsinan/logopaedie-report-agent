"use client";

import { useState } from "react";

interface Props {
  onSubmit: (code: string) => void;
  loading: boolean;
  error?: string | null;
}

export function TwoFactorChallenge({ onSubmit, loading, error }: Props) {
  const [code, setCode] = useState("");
  const valid = /^\d{6}$/.test(code);

  return (
    <form
      className="space-y-4"
      onSubmit={(e) => {
        e.preventDefault();
        if (valid) onSubmit(code);
      }}
    >
      <label className="block">
        <span className="text-sm font-medium">6-stelliger Code</span>
        <input
          type="text"
          inputMode="numeric"
          autoComplete="one-time-code"
          maxLength={6}
          pattern="\d{6}"
          value={code}
          onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
          className="mt-1 block w-full rounded border border-neutral-300 dark:border-neutral-700 px-3 py-2 bg-white dark:bg-neutral-900 text-center tracking-widest text-lg"
        />
      </label>
      {error && (
        <p role="alert" className="text-sm text-red-600">
          {error}
        </p>
      )}
      <button
        type="submit"
        disabled={!valid || loading}
        className="w-full rounded bg-blue-600 text-white py-2 disabled:opacity-50"
      >
        Bestätigen
      </button>
    </form>
  );
}
