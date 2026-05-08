import Image from "next/image";

const SCREENSHOTS = [
  {
    src: "/screenshots/screenshot-anamnese.png",
    caption: "Geführte Anamnese",
    alt: "Berichterstellung-Interface mit Auswahl des Berichtstyps — Befundbericht, Therapiebericht, Abschlussbericht",
  },
  {
    src: "/screenshots/screenshot-bericht.png",
    caption: "Generierter Bericht",
    alt: "KI generiert in Echtzeit einen strukturierten Klinikbericht via Llama-3.3-70b",
  },
];

export function ScreenshotSection() {
  return (
    <section className="w-full max-w-4xl mx-auto px-6 py-12">
      <h2 className="mb-8 text-center text-xl font-semibold text-foreground">
        Einblick
      </h2>
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
        {SCREENSHOTS.map(({ src, caption, alt }) => (
          <figure key={caption} className="flex flex-col gap-3">
            <div className="relative aspect-video overflow-hidden rounded-xl border border-border">
              <Image
                src={src}
                alt={alt}
                fill
                className="object-cover object-top"
                sizes="(max-width: 640px) 100vw, 50vw"
              />
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
