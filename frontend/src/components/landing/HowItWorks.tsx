const STEPS = [
  {
    n: "1",
    icon: "🏥",
    title: "Patient & Sitzung",
    description: "Patient auswählen oder Demo-Modus starten — keine Registrierung nötig.",
  },
  {
    n: "2",
    icon: "🎙",
    title: "Anamnese führen",
    description: "Die KI stellt klinisch relevante Fragen — per Text tippen oder per Sprache antworten (Groq Whisper).",
  },
  {
    n: "3",
    icon: "📄",
    title: "Bericht generieren",
    description: "Llama-3.3-70b erstellt den strukturierten Klinikbericht — als PDF exportierbar.",
  },
];

export function HowItWorks() {
  return (
    <section className="w-full max-w-4xl mx-auto px-6 py-12">
      <h2 className="mb-8 text-center text-xl font-semibold text-foreground">
        Wie es funktioniert
      </h2>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {STEPS.map(({ n, icon, title, description }) => (
          <div
            key={n}
            className="relative rounded-xl border border-border bg-surface p-6 shadow-sm"
          >
            <span className="absolute -top-3 left-5 flex h-6 w-6 items-center justify-center rounded-full bg-accent text-xs font-bold text-white">
              {n}
            </span>
            <div className="mb-3 text-2xl">{icon}</div>
            <h3 className="mb-1.5 text-sm font-semibold text-foreground">{title}</h3>
            <p className="text-xs leading-relaxed text-muted-foreground">{description}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
