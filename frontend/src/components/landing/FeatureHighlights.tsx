const FEATURES = [
  {
    icon: "🎙",
    title: "Sprachaufnahme → Bericht",
    description:
      "Groq Whisper transkribiert die Therapiesitzung in Echtzeit. Llama-3.3-70b strukturiert daraus einen professionellen Befundbericht.",
  },
  {
    icon: "📋",
    title: "SOAP-Notes automatisch",
    description:
      "Strukturierte klinische Dokumentation im S-O-A-P-Format — in Sekunden generiert, sofort exportierbar.",
  },
  {
    icon: "📊",
    title: "Phonologische Analyse",
    description:
      "Störungsmuster wie Plosivierung oder Fronting werden automatisch aus Wortpaaren erkannt und dokumentiert.",
  },
  {
    icon: "👤",
    title: "Patientenverwaltung",
    description:
      "Persistente Patientenprofile mit verschlüsselten Stammdaten (Fernet) und sitzungsübergreifendem Therapieverlauf.",
  },
  {
    icon: "🔐",
    title: "Multi-user Auth",
    description:
      "Registrierung, E-Mail-Verifikation, optionales TOTP 2FA, Passwort-Reset und aktive Sessions mit Geräte-Revoke.",
  },
  {
    icon: "📄",
    title: "PDF Export",
    description:
      "Professionelle PDFs via ReportLab — mit Patientendaten, Diagnose, Abschnittsgliederung und Unterschriftsfeld.",
  },
];

export function FeatureHighlights() {
  return (
    <section className="w-full max-w-4xl mx-auto px-6 py-12">
      <h2 className="mb-8 text-center text-xl font-semibold text-foreground">
        Alle Features
      </h2>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {FEATURES.map(({ icon, title, description }) => (
          <div
            key={title}
            className="rounded-xl border border-border bg-surface p-5 shadow-sm"
          >
            <div className="mb-3 text-2xl">{icon}</div>
            <h3 className="mb-1.5 text-sm font-semibold text-foreground">{title}</h3>
            <p className="text-xs leading-relaxed text-muted-foreground">{description}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
