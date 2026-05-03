# Implementierungsplan: Production-Ready Upgrade

**Spec:** `docs/specs/2026-05-03-production-ready-upgrade-design.md`
**Zeitrahmen:** 1–2 Tage
**Reihenfolge:** Color Tokens → Demo Mode → Mobile Nav → Landing Page

---

## Phase 1 — Color Tokens (ca. 2h)

### Schritt 1.1 — globals.css aktualisieren

**Datei:** `frontend/src/app/globals.css`

Folgende Token-Änderungen in `:root`:
```css
/* Ersetzen: */
--accent:       #2a7f6f  →  #2079C0
--accent-hover: #206958  →  #1860a0
--accent-muted: #dceee8  →  #e8f4ff
--accent-text:  #236f60  →  #1860a0

/* Neu hinzufügen: */
--ai:           #72B52A
--ai-hover:     #5a9620
--ai-muted:     #f0f9e8
--ai-text:      #5a9620

/* Entfernen: */
--brand-warm:   #c4714f  (nicht mehr benötigt)
```

Dark Mode (`.dark`):
```css
--accent:       #2079C0  (unverändert — guter Kontrast auf dark)
--accent-text:  #6db3f0  (heller für dark bg)
--accent-muted: rgba(32, 121, 192, 0.15)
--ai:           #72B52A  (unverändert)
--ai-text:      #a0d462  (heller für dark bg)
--ai-muted:     rgba(114, 181, 42, 0.12)
```

`@theme inline` Block — neue Bindings hinzufügen:
```css
--color-accent:     var(--accent);
--color-ai:         var(--ai);
--color-ai-hover:   var(--ai-hover);
--color-ai-muted:   var(--ai-muted);
--color-ai-text:    var(--ai-text);
```

### Schritt 1.2 — Bestehende Verwendungen prüfen

Grep nach `brand-warm` und `#2a7f6f` im Frontend — alle ersetzen durch neue Token.

```bash
grep -r "brand-warm\|2a7f6f\|accent-text" frontend/src --include="*.tsx" --include="*.ts" -l
```

---

## Phase 2 — Demo Mode (ca. 2h)

### Schritt 2.1 — middleware.ts erweitern

**Datei:** `frontend/src/middleware.ts`

Demo-Mode: wenn URL-Parameter `demo=true` vorhanden UND Ziel `/module/report` oder `/module/soap` → kein Redirect zu `/login`.

```typescript
function isDemoAllowed(pathname: string): boolean {
  return pathname === "/module/report" || pathname === "/module/soap";
}

// In middleware() — vor dem "if (!access)" Block einfügen:
const isDemo = req.nextUrl.searchParams.get("demo") === "true";
if (!access && isDemoAllowed(pathname) && isDemo) {
  return NextResponse.next();
}
```

Demo-Flag in Cookie persistieren damit es nicht bei jedem Request neu übergeben werden muss:
```typescript
// Wenn demo=true in URL: Cookie setzen
if (isDemo) {
  const response = NextResponse.next();
  response.cookies.set("demo_mode", "true", { maxAge: 3600, path: "/" });
  return response;
}
// Demo-Cookie auch prüfen:
const demoMode = req.cookies.get("demo_mode")?.value === "true";
if (!access && isDemoAllowed(pathname) && demoMode) {
  return NextResponse.next();
}
```

### Schritt 2.2 — useDemoMode Hook

**Datei:** `frontend/src/hooks/useDemoMode.ts`

```typescript
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

export function useDemoMode() {
  const searchParams = useSearchParams();
  const [isDemo, setIsDemo] = useState(false);

  useEffect(() => {
    const fromUrl = searchParams.get("demo") === "true";
    const fromStorage = localStorage.getItem("demo_mode") === "true";
    if (fromUrl) {
      localStorage.setItem("demo_mode", "true");
      setIsDemo(true);
    } else {
      setIsDemo(fromStorage);
    }
  }, [searchParams]);

  return { isDemo };
}
```

### Schritt 2.3 — DemoBanner Komponente

**Datei:** `frontend/src/components/DemoBanner.tsx`

Schmales Banner oben: "Demo-Modus · Kein Account erforderlich" + Link zu `/login`.
Grüner Hintergrund (`bg-ai-muted`), grüner Text, nur sichtbar wenn `isDemo === true`.

### Schritt 2.4 — DemoBanner in Layout einbinden

**Datei:** `frontend/src/app/module/layout.tsx`

`<DemoBanner />` direkt unter `<header>` vor `<main>` einfügen.

---

## Phase 3 — Mobile Navigation Burger Menu (ca. 2.5h)

### Schritt 3.1 — useMobileNav Hook

**Datei:** `frontend/src/hooks/useMobileNav.ts`

```typescript
import { useState, useCallback, useEffect } from "react";

export function useMobileNav() {
  const [isOpen, setIsOpen] = useState(false);

  const close = useCallback(() => setIsOpen(false), []);
  const toggle = useCallback(() => setIsOpen((v) => !v), []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && close();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [close]);

  return { isOpen, toggle, close };
}
```

### Schritt 3.2 — MobileSidebar Komponente

**Datei:** `frontend/src/components/MobileSidebar.tsx`

Drawer von links, `fixed inset-y-0 left-0 z-50 w-64`.
- Backdrop: `fixed inset-0 bg-black/40 z-40` → click schließt
- Inhalt: BrandLogo oben, dann vertikale Liste aller 7 Module als `<Link>`
- Aktives Modul: `text-accent font-semibold border-l-2 border-accent`
- Slide-Animation via `translate-x-0 / -translate-x-full transition-transform`

### Schritt 3.3 — BurgerButton Komponente

**Datei:** `frontend/src/components/BurgerButton.tsx`

```tsx
// Einfaches 3-Streifen Icon, onClick = toggle
// className="md:hidden" — nur auf Mobile
```

### Schritt 3.4 — Layout erweitern

**Datei:** `frontend/src/app/module/layout.tsx`

```tsx
// 1. useMobileNav() Hook einbinden
// 2. <BurgerButton> im Header rechts hinzufügen (vor ThemeToggle, nur md:hidden)
// 3. <MobileSidebar> einbinden
// 4. Horizontale Tab-Nav: 'hidden md:flex' statt nur 'flex'
```

---

## Phase 4 — Landing Page (ca. 3h)

### Schritt 4.1 — TypingDemo Komponente

**Datei:** `frontend/src/components/landing/TypingDemo.tsx`

```typescript
const DEMO_TEXT = `Befundbericht: Die Patientin (6 Jahre) zeigt phonologische Auffälligkeiten. Es wurden Prozesse der Plosivierung (/f/ → /p/) sowie Fronting (/k/ → /t/) dokumentiert. Therapieempfehlung: Intensive phonologische Förderung, 2x wöchentlich.`;
```

`useEffect` + `setInterval` mit 25ms Intervall. Nach vollständigem Text: 2s Pause, dann reset.

### Schritt 4.2 — HeroSection Komponente

**Datei:** `frontend/src/components/landing/HeroSection.tsx`

```
Headline: "Logopädische Berichte in Sekunden"
Subline:  "mit KI erstellen" (Blau)
Tech-Badge: "● Groq · Whisper · Llama-3.3-70b" (Grün, pulsierender Dot)
CTA Primary: "▶ Demo starten — ohne Login" → href="/module/report?demo=true"
CTA Secondary: "Anmelden →" → href="/login"
TypingDemo Komponente darunter
```

### Schritt 4.3 — FeatureHighlights Komponente

**Datei:** `frontend/src/components/landing/FeatureHighlights.tsx`

3 Karten:
1. "Sprachaufnahme → Bericht" — Whisper STT transkribiert automatisch
2. "SOAP-Notes in Sekunden" — strukturierte klinische Dokumentation
3. "Phonologische Analyse" — Störungsmuster automatisch erkennen

### Schritt 4.4 — page.tsx ersetzen

**Datei:** `frontend/src/app/page.tsx`

Aktuell: `redirect("/module/report")`
Neu: Vollständige Landing Page mit Header (sticky), HeroSection, FeatureHighlights, Footer.

Landing Page ist öffentlich (kein Auth-Guard nötig — `middleware.ts` leitet authentifizierte User bereits zu `/` weiter, das ist ok).

---

## Reihenfolge & Abhängigkeiten

```
Phase 1 (Color Tokens)
  └─→ Phase 4 (Landing Page nutzt neue Token)

Phase 2 (Demo Mode)
  └─→ Phase 3 (DemoBanner in Layout — nach Mobile Nav)

Phase 3 und Phase 4 sind parallel möglich nach Phase 1
```

**Empfohlene Reihenfolge für 1-2 Tage:**
1. Phase 1 — Color Tokens (Fundament)
2. Phase 2 — Demo Mode Middleware + Hook
3. Phase 3 — Mobile Nav
4. Phase 4 — Landing Page

---

## Tests & Verifikation

Nach jeder Phase:
```bash
cd frontend && npm run build   # TypeScript + Build-Fehler
```

Nach Phase 3 (Mobile Nav):
- Browser DevTools auf 375px (iPhone SE) setzen
- Burger-Button sichtbar?
- Drawer öffnet/schließt?
- Navigation zu allen 7 Modulen funktioniert?

Nach Phase 4 (Landing Page):
- `localhost:3000/` zeigt Landing Page
- CTA öffnet `localhost:3000/module/report?demo=true` ohne Login-Redirect
- Demo-Banner sichtbar in der App

---

## Nicht ändern

- Backend — keine Änderungen
- `frontend/src/features/*` — interne Module-Logik unverändert
- Auth-Flow für eingeloggte User — unverändert
- Tests in `frontend/` — müssen grün bleiben
