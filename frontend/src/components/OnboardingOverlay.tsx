// frontend/src/components/OnboardingOverlay.tsx
"use client";

import { useState } from "react";

interface OnboardingOverlayProps {
  onComplete: () => void;
}

const MODULES = [
  { icon: "📋", name: "Berichterstellung", desc: "KI-geführtes Anamnesegespräch → fertiger Befund-/Therapiebericht" },
  { icon: "🔊", name: "Ausspracheanalyse", desc: "Phonologische Prozesse automatisch erkennen und dokumentieren" },
  { icon: "📅", name: "Therapieplan", desc: "Strukturierten ICF-basierten Therapieplan generieren" },
  { icon: "⚖️", name: "Berichtsvergleich", desc: "Zwei Berichte gegenüberstellen und Fortschritt dokumentieren" },
  { icon: "✏️", name: "Textbausteine", desc: "KI-Vorschläge für Formulierungen während des Schreibens" },
];

const SCREENS = [
  {
    emoji: "👋",
    title: "Willkommen!",
    body: "Ihr KI-Assistent für logopädische Berichte. Statt stundenlang zu tippen, führen Sie einfach ein Gespräch — der Rest passiert automatisch.",
  },
  {
    emoji: null,
    title: "Was kann dieses Tool?",
    body: null,
  },
  {
    emoji: "✅",
    title: "Alles klar!",
    body: "Diese Einführung können Sie jederzeit über den ? Hilfe-Button oben rechts erneut aufrufen.",
  },
];

export function OnboardingOverlay({ onComplete }: OnboardingOverlayProps) {
  const [screen, setScreen] = useState(0);
  const isLast = screen === SCREENS.length - 1;

  function handleSkip() {
    onComplete();
  }

  function handleNext() {
    if (isLast) {
      onComplete();
    } else {
      setScreen((s) => s + 1);
    }
  }

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.6)",
        zIndex: 50,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "16px",
      }}
    >
      <div
        style={{
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: "12px",
          padding: "28px 28px 24px",
          maxWidth: "420px",
          width: "100%",
          boxShadow: "0 20px 60px rgba(0,0,0,0.4)",
        }}
      >
        {/* Skip */}
        <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: "16px" }}>
          <button
            onClick={handleSkip}
            style={{
              fontSize: "12px",
              color: "var(--muted-foreground)",
              background: "none",
              border: "none",
              cursor: "pointer",
              padding: "2px 4px",
            }}
          >
            Überspringen
          </button>
        </div>

        {/* Screen content */}
        {screen === 1 ? (
          /* Module list screen */
          <div>
            <h2 style={{ fontSize: "18px", fontWeight: "700", margin: "0 0 16px 0", color: "var(--foreground)" }}>
              Was kann dieses Tool?
            </h2>
            <div style={{ display: "flex", flexDirection: "column", gap: "10px", marginBottom: "24px" }}>
              {MODULES.map((mod) => (
                <div
                  key={mod.name}
                  style={{
                    display: "flex",
                    gap: "12px",
                    alignItems: "flex-start",
                    background: "var(--surface-elevated)",
                    borderRadius: "8px",
                    padding: "10px 12px",
                  }}
                >
                  <span style={{ fontSize: "18px", flexShrink: 0 }}>{mod.icon}</span>
                  <div>
                    <div style={{ fontSize: "13px", fontWeight: "600", color: "var(--foreground)", marginBottom: "2px" }}>
                      {mod.name}
                    </div>
                    <div style={{ fontSize: "11px", color: "var(--muted-foreground)", lineHeight: "1.4" }}>
                      {mod.desc}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          /* Text screens (0 and 2) */
          <div style={{ textAlign: "center", marginBottom: "24px" }}>
            <div style={{ fontSize: "40px", marginBottom: "14px" }}>{SCREENS[screen].emoji}</div>
            <h2 style={{ fontSize: "20px", fontWeight: "700", margin: "0 0 10px 0", color: "var(--foreground)" }}>
              {SCREENS[screen].title}
            </h2>
            <p style={{ fontSize: "13px", color: "var(--muted-foreground)", lineHeight: "1.6", margin: 0 }}>
              {SCREENS[screen].body}
            </p>
          </div>
        )}

        {/* Dot progress */}
        <div style={{ display: "flex", justifyContent: "center", gap: "6px", marginBottom: "20px" }}>
          {SCREENS.map((_, i) => (
            <div
              key={i}
              style={{
                width: "24px",
                height: "3px",
                borderRadius: "2px",
                background: i === screen ? "var(--accent)" : "var(--border)",
                transition: "background 0.2s ease",
              }}
            />
          ))}
        </div>

        {/* CTA */}
        <button
          onClick={handleNext}
          style={{
            width: "100%",
            padding: "10px",
            borderRadius: "8px",
            background: "var(--accent)",
            color: "white",
            fontSize: "14px",
            fontWeight: "600",
            border: "none",
            cursor: "pointer",
          }}
        >
          {isLast ? "App öffnen →" : "Weiter →"}
        </button>
      </div>
    </div>
  );
}
