"use client";

import Link from "next/link";
import { BrandLogo } from "@/components/BrandLogo";

const MODULE_TABS: [string, string][] = [
  ["report", "Berichterstellung"],
  ["phonology", "Ausspracheanalyse"],
  ["therapy-plan", "Therapieplan"],
  ["compare", "Berichtsvergleich"],
  ["suggest", "Textbausteine"],
  ["history", "Bericht-Verlauf"],
  ["soap", "SOAP-Notizen"],
];

type MobileSidebarProps = {
  isOpen: boolean;
  activeSlug: string;
  onClose: () => void;
};

export function MobileSidebar({ isOpen, activeSlug, onClose }: MobileSidebarProps) {
  return (
    <>
      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/40 md:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      {/* Drawer */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-64 flex-col bg-surface border-r border-border transition-transform duration-200 md:hidden ${
          isOpen ? "translate-x-0" : "-translate-x-full"
        }`}
        aria-label="Navigation"
      >
        <div className="flex items-center gap-3 border-b border-border px-4 py-3">
          <BrandLogo compact />
          <span className="text-sm font-semibold text-foreground">Logopädie Report</span>
        </div>

        <nav className="flex flex-col gap-0.5 p-2 flex-1 overflow-y-auto">
          <Link
            href="/patienten"
            onClick={onClose}
            className={`flex items-center rounded-md px-3 py-2.5 text-sm transition-colors ${
              activeSlug === "patienten"
                ? "bg-accent-muted text-accent-text font-semibold border-l-2 border-accent"
                : "text-muted-foreground hover:bg-surface-elevated hover:text-foreground"
            }`}
          >
            Patienten
          </Link>
          {MODULE_TABS.map(([key, label]) => (
            <Link
              key={key}
              href={`/module/${key}`}
              onClick={onClose}
              className={`flex items-center rounded-md px-3 py-2.5 text-sm transition-colors ${
                activeSlug === key
                  ? "bg-accent-muted text-accent-text font-semibold border-l-2 border-accent"
                  : "text-muted-foreground hover:bg-surface-elevated hover:text-foreground"
              }`}
            >
              {label}
            </Link>
          ))}
        </nav>
      </aside>
    </>
  );
}
