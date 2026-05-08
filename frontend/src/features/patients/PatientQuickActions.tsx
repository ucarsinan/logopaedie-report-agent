import Link from "next/link";

type PatientQuickActionsProps = {
  patientId: string;
};

type Action = {
  label: string;
  hint: string;
  href: string;
};

const ACTIONS: Action[] = [
  {
    label: "Neuer Bericht",
    hint: "KI-gestützte Befunderstellung",
    href: "/module/report",
  },
  {
    label: "Therapieplan",
    hint: "ICF-basierter Therapieplan",
    href: "/module/therapy-plan",
  },
  {
    label: "SOAP-Notizen",
    hint: "Strukturierte klinische Notizen",
    href: "/module/soap",
  },
  {
    label: "Phonologie",
    hint: "Phonologische Ausspracheanalyse",
    href: "/module/phonology",
  },
];

export function PatientQuickActions({ patientId }: PatientQuickActionsProps) {
  return (
    <section className="rounded-lg border border-border bg-card">
      <div className="border-b border-border px-4 py-3">
        <h2 className="text-base font-semibold text-foreground">
          Schnellaktionen
        </h2>
      </div>
      <div className="grid grid-cols-2 gap-3 p-4">
        {ACTIONS.map((action) => (
          <Link
            key={action.href}
            href={`${action.href}?patient=${patientId}`}
            className="flex flex-col gap-1.5 rounded-lg border border-border bg-surface p-4 transition-colors hover:bg-surface-elevated"
          >
            <span className="flex items-center justify-between">
              <span className="text-sm font-semibold text-foreground">
                {action.label}
              </span>
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="shrink-0 text-muted-foreground"
                aria-hidden="true"
              >
                <path d="M5 12h14" />
                <path d="m12 5 7 7-7 7" />
              </svg>
            </span>
            <span className="text-xs text-muted-foreground">{action.hint}</span>
          </Link>
        ))}
      </div>
    </section>
  );
}
