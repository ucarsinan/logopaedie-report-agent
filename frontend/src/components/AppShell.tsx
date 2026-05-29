"use client";

import { Suspense } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ThemeToggle } from "@/components/ThemeToggle";
import { BrandLogo } from "@/components/BrandLogo";
import { DemoBanner } from "@/components/DemoBanner";
import { BurgerButton } from "@/components/BurgerButton";
import { MobileSidebar } from "@/components/MobileSidebar";
import { UserAccountBar } from "@/features/auth/components/UserAccountBar";
import { useMobileNav } from "@/hooks/useMobileNav";

export const MODULE_TABS: [string, string, string][] = [
  ["report", "Berichte", "Berichterstellung – KI-geführtes Anamnesegespräch → professioneller Bericht"],
  ["phonology", "Aussprache", "Ausspracheanalyse – Phonologische Prozesse aus Wortpaaren erkennen"],
  ["therapy-plan", "Therapieplan", "ICF-basierten Therapieplan automatisch generieren"],
  ["compare", "Vergleich", "Berichtsvergleich – Zwei Berichte gegenüberstellen und Fortschritt messen"],
  ["suggest", "Textbausteine", "KI-Formulierungsvorschläge während des Schreibens"],
  ["history", "Verlauf", "Bericht-Verlauf – Alle gespeicherten Berichte anzeigen und durchsuchen"],
  ["soap", "SOAP", "SOAP-Notizen – Strukturierte klinische Notizen im SOAP-Format generieren"],
];

export const MODULE_LABELS: Record<string, string> = Object.fromEntries(
  MODULE_TABS.map(([key, label]) => [key, label]),
);

type AppShellProps = {
  children: React.ReactNode;
  /** Extra elements rendered in the header action row (e.g. help button) */
  headerExtras?: React.ReactNode;
  /** Content rendered between header and main (e.g. PatientContextBar) */
  subheader?: React.ReactNode;
};

export function AppShell({ children, headerExtras, subheader }: AppShellProps) {
  const pathname = usePathname();
  const isPatientenSection = pathname.startsWith("/patienten");
  const activeSlug = pathname.split("/").pop() ?? "report";

  const sectionLabel = isPatientenSection
    ? "Patienten"
    : (MODULE_LABELS[activeSlug] ?? "Modul");

  const logoHref = isPatientenSection ? "/patienten" : "/module/report";

  const { isOpen: isMobileNavOpen, toggle: toggleMobileNav, close: closeMobileNav } = useMobileNav();

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      <MobileSidebar
        isOpen={isMobileNavOpen}
        activeSlug={isPatientenSection ? "patienten" : activeSlug}
        onClose={closeMobileNav}
      />

      <header className="border-b border-border print:hidden">
        <div className="max-w-5xl mx-auto px-6">
          <div className="flex min-h-12 flex-wrap items-center justify-between gap-3 py-2">
            <Link
              href={logoHref}
              aria-label="Praxis für Logopädie Şimşek"
              className="flex min-w-0 items-center gap-3 text-sm"
            >
              <BrandLogo compact showSubtitle={false} className="min-w-0" />
              <span className="text-border-strong font-light md:hidden">/</span>
              <span className="font-semibold md:hidden" style={{ color: "var(--accent-text)" }}>
                {sectionLabel}
              </span>
            </Link>

            <div className="flex min-w-0 flex-wrap items-center justify-end gap-3">
              <Link
                href="/"
                className="text-xs text-muted-foreground/60 hover:text-muted-foreground transition-colors"
                title="Zurück zur Startseite"
              >
                ← Start
              </Link>
              <UserAccountBar />
              {headerExtras}
              <ThemeToggle />
              <BurgerButton isOpen={isMobileNavOpen} onClick={toggleMobileNav} />
            </div>
          </div>

          <nav className="relative hidden md:flex items-stretch gap-1 -mb-px overflow-x-auto after:pointer-events-none after:absolute after:right-0 after:top-0 after:h-full after:w-8 after:bg-linear-to-l after:from-background after:to-transparent md:after:hidden">
            <Link
              href="/patienten"
              title="Patienten verwalten"
              aria-current={isPatientenSection ? "page" : undefined}
              className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                isPatientenSection
                  ? "border-accent text-accent-text"
                  : "border-transparent text-muted-foreground hover:text-foreground hover:border-border-strong"
              }`}
            >
              Patienten
            </Link>
            <div className="mx-2 my-2 w-px bg-border shrink-0" />
            {MODULE_TABS.map(([key, label, tooltip]) => {
              const isActive = !isPatientenSection && activeSlug === key;
              return (
                <Link
                  key={key}
                  href={`/module/${key}`}
                  title={tooltip}
                  aria-current={isActive ? "page" : undefined}
                  className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                    isActive
                      ? "border-accent text-accent-text"
                      : "border-transparent text-muted-foreground hover:text-foreground hover:border-border-strong"
                  }`}
                >
                  {label}
                </Link>
              );
            })}
          </nav>
        </div>
      </header>

      <Suspense fallback={null}>
        <DemoBanner />
      </Suspense>
      {subheader}

      <main className="flex-1 max-w-5xl mx-auto w-full px-6 py-8 flex flex-col gap-6">
        {children}
      </main>

      <footer className="border-t border-border px-6 py-4 text-center text-xs text-muted print:hidden">
        Logopädie Report Agent · Groq API · FastAPI + Next.js
      </footer>
    </div>
  );
}
