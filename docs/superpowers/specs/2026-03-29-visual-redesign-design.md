# Visual Redesign — Logopädie Report Agent

**Date:** 2026-03-29
**Approach:** B — Token-Redesign + Header/Navigation
**Status:** Approved

---

## Context

The current UI uses a warm-beige/indigo color scheme with a flat tab navigation and a large monolithic `page.tsx` (19.8KB). While functional, it looks generic — similar to many SaaS tools using default Tailwind indigo. The goal is to give it a distinctive, professional identity appropriate for a medical documentation tool, without touching the component architecture.

The redesign targets the visual layer only: CSS design tokens, header/navigation pattern, and component styling. No structural changes to `page.tsx` or the route hierarchy.

---

## Design Decisions

| Dimension | Decision | Rationale |
|-----------|----------|-----------|
| Style direction | Editorial & Focused | Professional, content-first, no decorative noise |
| Accent color | Teal (`#0d9488` light / `#2dd4bf` dark) | Medizinisch assoziiert, differenziert von generischem Indigo |
| Secondary palette | Slate monochrome only | Keine Rainbow-Akzente — Emerald/Violet/Amber werden entfernt |
| Navigation | Breadcrumb + Pill-Steps + ⌘K hint | Fokus auf aktuelle Aufgabe, kein Tab-Rauschen |
| Light mode surfaces | Flat / Border-only | Papierhaftes Gefühl, ruhig |
| Dark mode surfaces | Elevated / Schatten | Layering durch box-shadow, tiefes Schiefer-Layering |
| Toggle | Bestehendes next-themes toggle, verbessertes Design | Bereits implementiert, nur visuell aufgewertet |

---

## Color Token System

### Light Mode
```css
--background:       #f9fafb   /* Gray-50 — sauberes Off-White */
--surface:          #ffffff   /* reine Weiß-Karten */
--surface-elevated: #f3f4f6   /* Gray-100 — AI-Bubble-Hintergrund */
--border:           #e5e7eb   /* Gray-200 — subtile Trennlinien */
--border-strong:    #d1d5db   /* Gray-300 — Input-Rahmen */
--foreground:       #111827   /* Gray-900 */
--muted-foreground: #6b7280   /* Gray-500 */
--muted:            #9ca3af   /* Gray-400 */
--input-bg:         #f9fafb   /* =background */
--accent:           #0d9488   /* Teal-600 — Buttons, Links, aktive Pills */
--accent-hover:     #0f766e   /* Teal-700 — Hover-State */
--accent-muted:     #ccfbf1   /* Teal-100 — Badge-Hintergrund */
--accent-text:      #0f766e   /* Teal-700 — Text auf hellem Badge */
--ring:             #0d9488   /* Focus-Ring */
```

### Dark Mode
```css
--background:       #0f172a   /* Slate-900 */
--surface:          #1e293b   /* Slate-800 — Karten (mit Schatten) */
--surface-elevated: #0f172a   /* Slate-900 — AI-Bubble-Hintergrund */
--border:           rgba(255,255,255,0.04)  /* sehr subtil */
--border-strong:    #334155   /* Slate-600 — Input-Rahmen */
--foreground:       #f1f5f9   /* Slate-100 */
--muted-foreground: #64748b   /* Slate-500 */
--muted:            #475569   /* Slate-600 */
--input-bg:         #0f172a   /* =background */
--accent:           #0d9488   /* Teal-600 — gleich wie light */
--accent-hover:     #14b8a6   /* Teal-500 — etwas heller im Dark */
--accent-muted:     rgba(13,148,136,0.15)  /* subtile Teal-Tint */
--accent-text:      #2dd4bf   /* Teal-400 — Text auf dunklem Badge */
--ring:             #2dd4bf   /* hellerer Focus-Ring */
```

### Shadow System (Dark Mode only)
```css
--shadow-card:   0 8px 32px rgba(0,0,0,0.4), 0 0 0 1px rgba(255,255,255,0.04)
--shadow-btn:    0 2px 8px rgba(13,148,136,0.35)   /* nur auf Teal-Buttons */
--shadow-header: 0 1px 0 rgba(255,255,255,0.05)
```

---

## Header & Navigation

### Structure
```
[Logopädie / <ModulName>]              [⌘K]  [☀/☾ toggle]
[① Anamnese →  ② Material →  ③ Bericht]     ← nur im Berichterstellungs-Modul
```

### Breadcrumb
- `Logopädie` = statischer Brand-Name (font-weight: 800, letter-spacing: -0.03em)
- `/` = Separator (color: --border-strong)
- `<ModulName>` = aktives Modul (color: --accent, font-weight: 600)
- Bei anderen Modulen (Ausspracheanalyse etc.): kein Breadcrumb-Separator, nur `Logopädie · Ausspracheanalyse`

### ⌘K Hint
- Kleines `kbd`-Element oben rechts
- Öffnet keinen echten Command-Palette-Dialog (nicht in Scope) — rein visuell als Design-Element
- Tooltip: "Modul wechseln" on hover

### Pill-Steps (nur Berichterstellung)
```
Zustand          Background               Text
─────────────    ──────────────────────   ────────────────
done (✓)         --accent-muted           --accent-text
active           --accent                 white
inactive         --surface-elevated       --muted
```
- Separator zwischen Pills: `→` in --muted-foreground
- Nur in der Berichterstellungs-Route sichtbar (phaseBased Workflow)

### Theme Toggle
- Pill-Switch (32×18px), border-radius: 9px
- Light: background gray-200, knob white+shadow (links)
- Dark: background --accent, knob white (rechts)

---

## Component Styling Changes

### Chat Bubbles
```
User-Bubble:   bg --accent, color white, border-radius: 12px 12px 4px 12px
               dark: + box-shadow --shadow-btn
AI-Bubble:     bg --surface-elevated, color --foreground, border-radius: 12px 12px 12px 4px
```

### Primary Buttons
```
bg --accent, hover: bg --accent-hover
dark: + box-shadow --shadow-btn
border-radius: 8px (statt bisherigem rounded-lg — bleibt gleich)
```

### Input Fields
```
bg --input-bg, border: 1px solid --border-strong
focus: border-color --accent, ring --ring
```

### Cards / Panels
```
Light: bg --surface, border: 1px solid --border, border-radius: 8px, no shadow
Dark:  bg --surface, box-shadow --shadow-card, border-radius: 8px
```

### Status Badges (vereinfacht)
```
Success:  bg teal-100  / teal-900(dark), text teal-700  / teal-300(dark)
Warning:  bg amber-100 / amber-900(dark), text amber-700 / amber-300(dark)
Error:    bg red-100   / red-900(dark),   text red-700   / red-300(dark)
Neutral:  bg --surface-elevated,          text --muted-foreground
```
Entfernt: Emerald, Violet als strukturelle Akzente (nur noch Teal + Status-Farben)

### Welcome Screen Cards (Report-Typ-Auswahl)
Alle 4 Karten bekommen einheitliche Icon-Farbe: --accent. Kein Emerald/Violet/Amber mehr für Icon-Hintergründe.

---

## Files to Modify

| File | Changes |
|------|---------|
| `frontend/src/app/globals.css` | Alle CSS-Variablen ersetzen (Teal+Slate), Shadow-Variablen hinzufügen |
| `frontend/src/app/page.tsx` | Header-JSX ersetzen, Phase-Steps → Pills, Indigo → Teal überall, Dark-Mode-Schatten |
| `frontend/src/components/ThemeToggle.tsx` | Pill-Switch Design |

---

## Out of Scope

- `page.tsx` Komponentenextraktion (bleibt monolithisch)
- shadcn/ui Migration
- ⌘K Command-Palette Implementierung (nur visuelles Hint-Element)
- Neue Features oder Layout-Änderungen
- Print-Styles Überarbeitung

---

## Verification

1. `npm run dev` im `frontend/`-Verzeichnis starten
2. Light-Mode prüfen: Flat-Look, Teal-Buttons, Breadcrumb-Header, Pills
3. Dark-Mode prüfen: Elevated Cards (Schatten sichtbar), Slate-Hintergrund, Toggle rechtsseitig
4. Toggle-Wechsel: smooth, kein Flash, kein Layout-Shift
5. Alle 5 Module durchklicken: Breadcrumb zeigt richtigen Modulnamen
6. Chat-Workflow: Bubbles korrekt gefärbt, Send-Button Teal mit Schatten (dark)
7. Welcome Screen: alle 4 Karten mit Teal-Icon-Hintergrund
8. Keine Indigo-Farben mehr sichtbar
