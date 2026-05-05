const WORKFLOW_STEPS = [
  {
    step: "01",
    title: "Therapeutische Beobachtung",
    body: "Klinische Beobachtungen, Spontansprache und Testergebnisse werden in der Sitzung aufgezeichnet — als Audiodatei oder strukturierte Texteingabe.",
  },
  {
    step: "02",
    title: "Logopädische Einordnung",
    body: "Störungsmuster werden klassifiziert: Phonologie, Semantik, Pragmatik, Redeflussstörung. Die Einordnung folgt dem klinischen Kontext des Patienten.",
  },
  {
    step: "03",
    title: "Berichtsfähige Dokumentation",
    body: "Der Bericht gliedert sich in Befund, Diagnose, Therapieziel und Empfehlung — im Format, das Kassen, Ärzte und Gutachter erwarten.",
  },
];

export function FeatureHighlights() {
  return (
    <section className="w-full max-w-4xl mx-auto px-6 py-12">
      <p className="mb-8 text-xs uppercase tracking-widest text-muted-foreground">
        Dokumentationsablauf
      </p>
      <div className="grid grid-cols-1 gap-8 sm:grid-cols-3 sm:gap-6">
        {WORKFLOW_STEPS.map(({ step, title, body }) => (
          <div key={step} className="border-t border-border pt-5">
            <span className="font-mono text-xs tabular-nums text-muted-foreground">
              {step}
            </span>
            <h3 className="mt-3 text-sm font-semibold leading-snug text-foreground">
              {title}
            </h3>
            <p className="mt-2 text-xs leading-relaxed text-muted-foreground">
              {body}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}
