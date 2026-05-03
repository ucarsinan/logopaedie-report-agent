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
];

export function FeatureHighlights() {
  return (
    <section className="w-full max-w-4xl mx-auto px-6 py-12">
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
