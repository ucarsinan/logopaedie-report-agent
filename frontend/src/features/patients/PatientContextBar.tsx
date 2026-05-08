"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { Patient } from "@/types";

interface PatientContextBarProps {
  patientId: string;
}

export function PatientContextBar({ patientId }: PatientContextBarProps) {
  const [patient, setPatient] = useState<Patient | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api.patients
      .get(patientId)
      .then((p) => {
        if (!cancelled) {
          setPatient(p);
          setLoading(false);
        }
      })
      .catch(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [patientId]);

  if (loading) {
    return (
      <div className="border-b border-border print:hidden">
        <div className="max-w-5xl mx-auto px-6 py-2">
          <div className="h-4 w-64 rounded animate-pulse bg-muted" />
        </div>
      </div>
    );
  }

  if (!patient) return null;

  const initial = patient.pseudonym.charAt(0).toUpperCase();

  const disorderHint =
    patient.disorder_text
      ? patient.disorder_text.slice(0, 50)
      : patient.icd10_codes[0] ?? null;

  return (
    <div className="border-b border-border bg-surface print:hidden">
      <div className="max-w-5xl mx-auto px-6 py-2 flex items-center gap-3">
        {/* Avatar */}
        <span className="flex-shrink-0 inline-flex items-center justify-center w-7 h-7 rounded-full bg-accent text-white text-xs font-semibold select-none">
          {initial}
        </span>

        {/* Name + system_id */}
        <span className="font-semibold text-sm text-foreground leading-tight">
          {patient.pseudonym}
        </span>
        <span className="text-xs text-muted-foreground leading-tight">
          {patient.system_id}
        </span>

        {/* Disorder hint */}
        {disorderHint && (
          <span className="hidden sm:inline text-xs text-muted-foreground leading-tight truncate max-w-xs">
            · {disorderHint}
            {patient.disorder_text && patient.disorder_text.length > 50 ? "…" : ""}
          </span>
        )}

        {/* Spacer */}
        <span className="flex-1" />

        {/* Link to patient profile */}
        <Link
          href={`/patienten/${patient.id}`}
          className="text-xs text-accent-text hover:underline whitespace-nowrap"
        >
          Profil ansehen →
        </Link>
      </div>
    </div>
  );
}
