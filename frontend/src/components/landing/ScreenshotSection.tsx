const PLACEHOLDERS = [
  { caption: "Geführte Anamnese" },
  { caption: "Generierter Bericht" },
];

export function ScreenshotSection() {
  return (
    <section className="w-full max-w-4xl mx-auto px-6 py-12">
      <h2 className="mb-8 text-center text-xl font-semibold text-foreground">
        Einblick
      </h2>
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
        {PLACEHOLDERS.map(({ caption }) => (
          <figure key={caption} className="flex flex-col gap-3">
            {/* TODO: Replace div with <Image> once screenshots are ready */}
            <div className="flex aspect-video items-center justify-center rounded-xl border-2 border-dashed border-border bg-surface">
              <p className="text-xs text-muted-foreground">{caption}</p>
            </div>
            <figcaption className="text-center text-xs text-muted-foreground">
              {caption}
            </figcaption>
          </figure>
        ))}
      </div>
    </section>
  );
}
