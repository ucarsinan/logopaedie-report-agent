"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { Patient } from "@/types";
import { ProgressSnapshot } from "@/features/patient-progress/ProgressSnapshot";
import { ConsentManager } from "./ConsentManager";
import { PatientHistory } from "./PatientHistory";

type PatientDetailProps = {
  patientId: string;
};

function formatDate(value: string): string {
  return new Date(value).toLocaleDateString("de-DE", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

function InfoItem({
  label,
  value,
}: {
  label: string;
  value: string | null | undefined;
}) {
  return (
    <div className="min-w-0">
      <dt className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">
        {label}
      </dt>
      <dd className="mt-1 truncate text-sm text-foreground">{value || "-"}</dd>
    </div>
  );
}

export function PatientDetail({ patientId }: PatientDetailProps) {
  const router = useRouter();
  const [patient, setPatient] = useState<Patient | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  async function handleDelete() {
    if (!window.confirm("Patient wirklich archivieren? Die Aktion kann nicht rückgängig gemacht werden.")) return;
    setDeleting(true);
    try {
      await api.patients.delete(patientId);
      router.push("/patienten");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Archivieren fehlgeschlagen.");
      setDeleting(false);
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true);
    setError(null);
    api.patients
      .get(patientId)
      .then(setPatient)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [patientId]);

  if (loading) {
    return (
      <div className="mx-auto w-full max-w-5xl px-6 py-8">
        <div className="rounded-lg border border-border bg-card px-4 py-10 text-center text-sm text-muted-foreground">
          Lade Patientendaten...
        </div>
      </div>
    );
  }

  if (error || !patient) {
    return (
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-4 px-6 py-8">
        <Link
          href="/patienten"
          className="text-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          ← Zurück zur Patientenliste
        </Link>
        <div className="rounded-md border border-error-border bg-error-surface px-4 py-3 text-sm text-error-text">
          {error ?? "Patient nicht gefunden."}
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6 px-6 py-8">
      <div className="flex flex-col gap-4 border-b border-border pb-5 md:flex-row md:items-end md:justify-between">
        <div className="min-w-0">
          <Link
            href="/patienten"
            className="text-sm text-muted-foreground transition-colors hover:text-foreground"
          >
            ← Zurück zur Patientenliste
          </Link>
          <p className="mt-4 text-xs font-semibold uppercase tracking-[0.18em] text-accent-text">
            {patient.system_id}
          </p>
          <h1 className="mt-2 truncate text-2xl font-semibold tracking-tight text-foreground">
            {patient.pseudonym}
          </h1>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            href={`/module/report?patient=${patient.id}`}
            className="inline-flex min-h-10 items-center justify-center rounded-md border border-border bg-surface px-4 text-sm font-medium text-foreground transition-colors hover:bg-surface-elevated"
          >
            Bericht starten
          </Link>
          <Link
            href={`/patienten/${patient.id}/bearbeiten`}
            className="inline-flex min-h-10 items-center justify-center rounded-md bg-accent px-4 text-sm font-semibold text-white transition-colors hover:bg-accent-hover"
          >
            Bearbeiten
          </Link>
          <button
            type="button"
            onClick={handleDelete}
            disabled={deleting}
            className="inline-flex min-h-10 items-center justify-center rounded-md border border-error-border px-4 text-sm font-medium text-error-text transition-colors hover:bg-error-surface disabled:cursor-not-allowed disabled:opacity-50"
          >
            {deleting ? "Archiviert..." : "Archivieren"}
          </button>
        </div>
      </div>

      <section className="rounded-lg border border-border bg-card">
        <div className="border-b border-border px-4 py-3">
          <h2 className="text-base font-semibold text-foreground">Stammdaten</h2>
        </div>
        <dl className="grid gap-4 px-4 py-4 sm:grid-cols-2 lg:grid-cols-4">
          <InfoItem label="Realname" value={patient.realname} />
          <InfoItem label="Geburtsdatum" value={patient.birthdate} />
          <InfoItem label="Altersgruppe" value={patient.age_group} />
          <InfoItem label="Geschlecht" value={patient.gender} />
          <InfoItem label="Telefon" value={patient.phone} />
          <InfoItem label="E-Mail" value={patient.email} />
          <InfoItem label="Krankenkasse" value={patient.insurance_name} />
          <InfoItem label="Angelegt" value={formatDate(patient.created_at)} />
        </dl>
      </section>

      <section className="rounded-lg border border-border bg-card">
        <div className="border-b border-border px-4 py-3">
          <h2 className="text-base font-semibold text-foreground">Klinik</h2>
        </div>
        <dl className="grid gap-4 px-4 py-4 md:grid-cols-3">
          <InfoItem
            label="ICD-10"
            value={patient.icd10_codes.length ? patient.icd10_codes.join(", ") : null}
          />
          <InfoItem
            label="Indikationsschlüssel"
            value={patient.indikationsschluessel}
          />
          <InfoItem label="Sorgeberechtigte" value={patient.guardian_name} />
          <div className="md:col-span-3">
            <dt className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">
              Störungsbild
            </dt>
            <dd className="mt-1 text-sm leading-6 text-foreground">
              {patient.disorder_text || "-"}
            </dd>
          </div>
        </dl>
      </section>

      <div className="grid gap-6 lg:grid-cols-[1fr_22rem]">
        <div className="grid gap-6">
          <ProgressSnapshot patientId={patient.id} />
          <PatientHistory patientId={patient.id} />
        </div>
        <ConsentManager patientId={patient.id} />
      </div>
    </div>
  );
}
