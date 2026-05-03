# Design Spec: Production-Ready Upgrade — Logopädie Report Agent

**Datum:** 2026-05-03
**Scope:** 1–2 Tage · Portfolio-Showcase + Weiterbildung MVP
**Ziel:** KI sofort sichtbar, Praxis-Brand durchgängig, mobil nutzbar

---

## 1. Zielsetzung

Das Tool soll zwei Zielgruppen überzeugen:

1. **Weiterbildungs-Präsentation** — funktionaler MVP mit echten KI-Funktionen
2. **AI-Engineer Portfolio** — Showcase-Qualität, KI-Technologie prominent sichtbar

Kernbotschaft: "Ein Logopäde öffnet die Seite → sieht sofort, dass KI arbeitet → versteht den Nutzen → kann ohne Login eine Demo starten."

---

## 2. Scope (was wird gebaut)

| Feature | Priorität | Aufwand |
|---|---|---|
| Landing Page (KI als Hero) | Hoch | ~3h |
| Color Redesign (CSS Tokens) | Hoch | ~2h |
| Demo Mode (ohne Login) | Hoch | ~2h |
| Mobile Navigation (Burger Menu) | Hoch | ~2.5h |

**Explizit außerhalb des Scope:**
- Patienten-Management / Patientendatenbank
- PDF-Export UI (Backend-Endpunkt existiert, UI bleibt as-is)
- Neue KI-Module
- Authentifizierung erweitern

---

## 3. Color Design System

### Primärfarben (aus Şimşek-Logo)

| Token | Wert | Semantik |
|---|---|---|
| `--color-brand` | `#2079C0` | Praxis-Brand: Navigation, Buttons, aktiver Tab-Indicator, Links |
| `--color-ai` | `#72B52A` | KI-Aktionen: Badges, generierte Inhalte, AI-Status, Typing-Cursor |

### Neutrals

| Token | Wert | Verwendung |
|---|---|---|
| `--color-bg` | `#ffffff` | Page Background |
| `--color-surface` | `#f8fafc` | Cards, Panels |
| `--color-border` | `#e2e8f0` | Divider, Card-Borders |
| `--color-text` | `#111827` | Body-Text |
| `--color-muted` | `#6b7280` | Sekundärer Text |

### Abgeleitete Tokens

```css
--color-brand-light: #e8f4ff;   /* Backgrounds für Brand-Elemente */
--color-brand-dark:  #1860a0;   /* Hover-States */
--color-ai-light:    #f0f9e8;   /* Backgrounds für KI-Elemente */
--color-ai-dark:     #5a9620;   /* Hover-States auf KI-Buttons */
```

### Dark Mode

Dark Mode bleibt über `next-themes` erhalten. In Dark Mode:
- `--color-bg` → `#0f172a` (slate-900)
- `--color-surface` → `#1e293b` (slate-800)
- Brand-Blau und KI-Grün bleiben identisch (nur Helligkeit leicht angepasst für Kontrast)

### Semantische Regel

> **Grün erscheint NUR wenn KI aktiv ist oder KI-Inhalte angezeigt werden.**
> Praxis-Navigation, Buttons, Links → immer Blau.

---

## 4. Landing Page

### Route
`/` → neue Landing Page (ersetzt aktuelles `redirect("/module/report")`)
`/module/*` bleibt unverändert — CTA auf Landing Page verlinkt auf `/module/report?demo=true`

### Aufbau

```
┌─────────────────────────────────────────┐
│  [Logo] Logopädie Report Agent          │  ← Header (sticky)
│                          [Demo starten] │     Button → /module/report?demo=true
├─────────────────────────────────────────┤
│                                         │
│  Hero Section:                          │
│  "Logopädische Berichte in Sekunden"    │  ← H1, Blau-Akzent
│  "mit KI erstellen"                     │
│                                         │
│  ● Groq · Whisper · Llama-3.3-70b       │  ← Grüner Dot + Tech-Badge
│                                         │
│  [▶ Demo starten — ohne Login]          │  ← CTA Blau
│  [Anmelden →]                           │  ← Sekundär
│                                         │
│  ┌──────────────────────────────────┐   │
│  │ ⬡ KI generiert gerade...         │   │  ← Typing-Animation (Grün)
│  │ Befundbericht: Die Patientin...▌  │   │
│  └──────────────────────────────────┘   │
│                                         │
├─────────────────────────────────────────┤
│  Feature-Highlights (3 Karten):         │
│  🎙 Sprachaufnahme → Bericht            │
│  📋 SOAP-Notes automatisch              │
│  📊 Phonologische Analyse               │
└─────────────────────────────────────────┘
```

### Typing-Animation

Statische Simulation (kein echter API-Call):
- Vordefinierten Muster-Befundbericht Zeichen für Zeichen einblenden
- 30ms pro Zeichen, loop nach vollständigem Text
- Implementiert mit `useEffect` + `setInterval` in einer `TypingDemo`-Komponente

### Komponenten

- `LandingPage` — Page-Komponente (`/app/page.tsx`)
- `HeroSection` — Headline + CTA + Typing-Demo
- `TypingDemo` — Animierte KI-Vorschau
- `FeatureHighlights` — 3 Feature-Karten

---

## 5. Demo Mode

### Konzept

Ein URL-Parameter `?demo=true` aktiviert den Demo-Modus:
- Auth-Guard wird übersprungen für Demo-zugängliche Seiten
- Demo-Banner oben in der App: "Demo-Modus · Kein Account erforderlich · [Jetzt anmelden]"
- Demo-Session wird automatisch erstellt beim ersten API-Call

### Zugängliche Module im Demo-Modus

| Modul | Demo-Zugang | Begründung |
|---|---|---|
| Report (Bericht generieren) | ✅ | Kern-Feature, muss demonstrierbar sein |
| SOAP Notes | ✅ | Zeigt strukturierte KI-Ausgabe |
| Phonologie | ❌ | Benötigt Audio-Upload, komplexer Flow |
| Therapieplan | ❌ | Setzt Report voraus |
| Vergleich | ❌ | Setzt mehrere Reports voraus |
| Textbausteine | ❌ | Weniger visuell eindrucksvoll |
| Verlauf/History | ❌ | Leer ohne echte Sessions |

### Technische Umsetzung

- `DemoBanner` — Komponente oben in `/app/module/layout.tsx`
- `useDemoMode()` — Hook liest `?demo=true` aus URL + localStorage-Fallback
- Auth-Middleware: wenn `demo=true` → keine Redirect zu `/login`
- Backend: Demo-Sessions bekommen Prefix `demo_` in der Session-ID

---

## 6. Mobile Navigation — Burger Menu

### Aktueller Zustand

`/app/module/layout.tsx` hat horizontale Tab-Leiste mit 7 Tabs → bricht auf Mobilgeräten.

### Neue Struktur

**Desktop (≥ 768px):** Aktuelle horizontale Tab-Navigation bleibt unverändert.

**Mobile (< 768px):**
- Horizontale Tabs werden ausgeblendet (`hidden md:flex`)
- Burger-Button (☰) erscheint rechts im Header
- Sidebar-Drawer öffnet sich von links
- Drawer enthält: Logo + Praxis-Name oben, alle 7 Module als vertikale Liste, aktives Modul bleibt markiert (Blau)
- Backdrop-Overlay zum Schließen
- `Escape` schließt ebenfalls

### Komponenten

- `MobileSidebar` — Drawer mit Modul-Liste
- `BurgerButton` — Toggle-Button im Header (nur mobile sichtbar)
- `useMobileNav()` — Hook: `isOpen`, `toggle`, `close`

---

## 7. KI-Sichtbarkeit (übergreifend)

Folgende Muster werden konsistent durch alle Module angewendet:

| Muster | Beschreibung |
|---|---|
| **KI-Badge** | `⬡ KI aktiv` — grüner Hintergrund (`--color-ai-light`), grüner Text |
| **Typing-Cursor** | Blinkender vertikaler Balken in `--color-ai` bei laufender Generierung |
| **AI-Status-Bar** | Schmale grüne Leiste oben wenn KI arbeitet: "⬡ Llama-3.3-70b generiert..." |
| **Generierter Content** | Grüner linker Border (`border-l-4 border-ai`) bei KI-generierten Textblöcken |

---

## 8. Architektur-Änderungen

### Routing

```
Vorher:  / → redirect(/module/report)
Nachher: / → LandingPage
         /module/* bleibt unverändert (bestehende Auth-Flows)
         Demo-Mode: /module/report?demo=true → Auth-Guard überspringen
```

### CSS Tokens

`globals.css` erhält neue Custom Properties (Abschnitt 3). Alle bestehenden Tailwind-Klassen, die `--accent` (teal) verwenden, werden auf `--color-brand` oder `--color-ai` migriert.

### Dateien erstellen

```
frontend/src/app/page.tsx                  → LandingPage (überschreiben)
frontend/src/components/landing/
  HeroSection.tsx
  TypingDemo.tsx
  FeatureHighlights.tsx
frontend/src/components/DemoBanner.tsx
frontend/src/components/MobileSidebar.tsx
frontend/src/components/BurgerButton.tsx
frontend/src/hooks/useDemoMode.ts
frontend/src/hooks/useMobileNav.ts
```

### Dateien modifizieren

```
frontend/src/app/globals.css               → Neue Color Tokens
frontend/src/app/module/layout.tsx         → BurgerButton + MobileSidebar integrieren
frontend/src/middleware.ts → Demo-Mode Auth-Bypass hinzufügen
```

---

## 9. Nicht-Ziele (explizit)

- Kein Redesign der bestehenden Module-Inhalte
- Keine Änderung an Backend-Endpunkten
- Kein neues Auth-System
- Keine Datenbankmigrationen
- Keine neuen KI-Features

---

## 10. Erfolgskriterien

- [ ] Öffnet man `/`, sieht man die Landing Page mit Typing-Animation
- [ ] CTA "Demo starten" führt ohne Login direkt zur App
- [ ] Demo-Banner ist in der App sichtbar
- [ ] Auf einem 375px-Viewport (iPhone) ist das Burger-Menu sichtbar und funktioniert
- [ ] Blau erscheint nur für Praxis-Elemente, Grün nur für KI-Elemente
- [ ] `npm run build` läuft fehlerfrei durch
- [ ] Kein Bruch in bestehenden Tests
