"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { authApi } from "@/features/auth/api";

export default function VerifyEmailPage() {
  const params = useSearchParams();
  const token = params.get("token");
  const [state, setState] = useState<"pending" | "ok" | "error">(() =>
    token ? "pending" : "error",
  );

  useEffect(() => {
    if (!token) return;
    authApi
      .verifyEmail(token)
      .then(() => setState("ok"))
      .catch(() => setState("error"));
  }, [token]);

  if (state === "pending") {
    return <p className="text-sm">Bestätige Email-Adresse…</p>;
  }

  if (state === "ok") {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-semibold">Email bestätigt</h1>
        <p className="text-sm">Sie können sich jetzt anmelden.</p>
        <Link
          href="/login"
          className="block text-center rounded bg-blue-600 text-white py-2"
        >
          Zur Anmeldung
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Bestätigung fehlgeschlagen</h1>
      <p role="alert" className="text-sm text-red-600">
        Der Bestätigungslink ist ungültig oder abgelaufen.
      </p>
      <Link href="/login" className="text-sm text-blue-600 hover:underline">
        Zur Anmeldung
      </Link>
    </div>
  );
}
