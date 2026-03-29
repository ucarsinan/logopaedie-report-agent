# Visual Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the warm-beige/indigo color scheme with a Teal+Slate editorial design and rebuild the header as a breadcrumb + pill-step navigation with a pill-style theme toggle.

**Architecture:** Three file changes only — `globals.css` (token replacement), `ThemeToggle.tsx` (pill switch), `page.tsx` (header + all indigo→teal + welcome screen unification). No new files, no structural changes to component logic or API calls.

**Tech Stack:** Next.js 16, Tailwind CSS v4 (`@theme inline`), next-themes, TypeScript

**Design Spec:** `docs/superpowers/specs/2026-03-29-visual-redesign-design.md`

---

## File Map

| File | Change |
|------|--------|
| `frontend/src/app/globals.css` | Replace all CSS variables with Teal+Slate system; add shadow variables |
| `frontend/src/components/ThemeToggle.tsx` | Replace icon-button with pill-switch (32×18px) |
| `frontend/src/app/page.tsx` | New header JSX (breadcrumb + pills + tabs), indigo→teal everywhere, WelcomeScreen accent unification, dark mode shadow classes |

---

## Dev Server

All visual verification steps use the dev server:
```bash
cd frontend && npm run dev
# opens http://localhost:3000
```

---

## Task 1: Replace CSS Design Tokens

**Files:**
- Modify: `frontend/src/app/globals.css`

- [ ] **Step 1: Replace the entire file content**

Replace `frontend/src/app/globals.css` with:

```css
@import "tailwindcss";

/* ── Class-based dark mode (next-themes adds .dark to <html>) ── */
@custom-variant dark (&:where(.dark, .dark *));

/* ── Light mode tokens (default) ── */
:root {
  --background:        #f9fafb;
  --surface:           #ffffff;
  --surface-elevated:  #f3f4f6;
  --border:            #e5e7eb;
  --border-strong:     #d1d5db;
  --foreground:        #111827;
  --muted-foreground:  #6b7280;
  --muted:             #9ca3af;
  --input-bg:          #f9fafb;
  --ring:              #0d9488;
  --accent:            #0d9488;
  --accent-hover:      #0f766e;
  --accent-muted:      #ccfbf1;
  --accent-text:       #0f766e;
  --error-surface:     #fef2f2;
  --error-border:      #fecaca;
  --error-text:        #b91c1c;
}

/* ── Dark mode tokens ── */
.dark {
  --background:        #0f172a;
  --surface:           #1e293b;
  --surface-elevated:  #0f172a;
  --border:            rgba(255, 255, 255, 0.04);
  --border-strong:     #334155;
  --foreground:        #f1f5f9;
  --muted-foreground:  #64748b;
  --muted:             #475569;
  --input-bg:          #0f172a;
  --ring:              #2dd4bf;
  --accent:            #0d9488;
  --accent-hover:      #14b8a6;
  --accent-muted:      rgba(13, 148, 136, 0.15);
  --accent-text:       #2dd4bf;
  --error-surface:     rgba(69, 10, 10, 0.8);
  --error-border:      #991b1b;
  --error-text:        #fca5a5;
}

/* ── Tailwind 4 token bindings ── */
@theme inline {
  --color-background:      var(--background);
  --color-surface:         var(--surface);
  --color-surface-elevated: var(--surface-elevated);
  --color-border:          var(--border);
  --color-border-strong:   var(--border-strong);
  --color-foreground:      var(--foreground);
  --color-muted-foreground: var(--muted-foreground);
  --color-muted:           var(--muted);
  --color-input:           var(--input-bg);
  --color-accent:          var(--accent);
  --color-accent-muted:    var(--accent-muted);
  --color-accent-text:     var(--accent-text);
  --color-error-surface:   var(--error-surface);
  --color-error-border:    var(--error-border);
  --color-error-text:      var(--error-text);
  --font-sans:             var(--font-geist-sans);
  --font-mono:             var(--font-geist-mono);
}

body {
  background-color: var(--background);
  color: var(--foreground);
  font-family: var(--font-geist-sans), system-ui, sans-serif;
}
```

- [ ] **Step 2: Verify tokens load**

Open http://localhost:3000 — page background should be `#f9fafb` (light cool gray, not warm beige). In dark mode: `#0f172a` (deep slate, not near-black zinc). No console errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/globals.css
git commit -m "design: replace warm-beige/indigo tokens with teal+slate system"
```

---

## Task 2: Pill-Switch Theme Toggle

**Files:**
- Modify: `frontend/src/components/ThemeToggle.tsx`

- [ ] **Step 1: Replace the component**

Replace the entire content of `frontend/src/components/ThemeToggle.tsx` with:

```tsx
"use client";

import { useTheme } from "next-themes";
import { useEffect, useState } from "react";

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);

  if (!mounted) {
    return <div className="w-8 h-[18px]" aria-hidden="true" />;
  }

  const isDark = resolvedTheme === "dark";

  return (
    <button
      onClick={() => setTheme(isDark ? "light" : "dark")}
      role="switch"
      aria-checked={isDark}
      aria-label={isDark ? "Light Mode aktivieren" : "Dark Mode aktivieren"}
      className="relative w-8 h-[18px] rounded-full transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)] focus-visible:ring-offset-2 focus-visible:ring-offset-background"
      style={{ background: isDark ? "var(--accent)" : "#e5e7eb" }}
    >
      <span
        className="absolute top-[2px] w-[14px] h-[14px] rounded-full bg-white shadow-sm transition-transform duration-200"
        style={{ transform: isDark ? "translateX(16px)" : "translateX(2px)" }}
      />
    </button>
  );
}
```

- [ ] **Step 2: Verify toggle**

Open http://localhost:3000. Toggle should appear as a pill switch top-right:
- Light mode: gray pill, knob left
- Dark mode: teal pill, knob right
- Click switches modes smoothly, no flash

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ThemeToggle.tsx
git commit -m "design: replace icon-button toggle with teal pill-switch"
```

---

## Task 3: Redesign Header — Breadcrumb + Pill-Steps + Tabs

**Files:**
- Modify: `frontend/src/app/page.tsx` (lines 325–373 and 1451–1472)

This task replaces the header JSX and the `PhaseStep` component. The module tabs stay for navigation but are restyled. The old `PhaseStep` component is replaced by inline pill markup.

- [ ] **Step 1: Replace the header JSX**

Find this block in `page.tsx` (around line 325):
```tsx
      {/* Header */}
      <header className="border-b border-border print:hidden">
        <div className="max-w-5xl mx-auto px-6">
          <div className="flex items-center justify-between py-4">
            <div className="flex items-center gap-3">
              <span className="text-lg font-semibold tracking-tight">
                Logopädie Report Agent
              </span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-surface-elevated text-muted-foreground font-mono">
                v2.0
              </span>
            </div>
            <div className="flex items-center gap-3">
              {/* Phase indicator (only for report module) */}
              {activeModule === "report" && (
                <nav className="flex items-center gap-1 text-xs">
                  <PhaseStep label="Anamnese" active={phase === "chat"} done={phase !== "chat"} />
                  <ChevronRight />
                  <PhaseStep label="Materialien" active={phase === "upload"} done={phase === "generating" || phase === "preview"} />
                  <ChevronRight />
                  <PhaseStep label="Bericht" active={phase === "generating" || phase === "preview"} done={phase === "preview"} />
                </nav>
              )}
              <ThemeToggle />
            </div>
          </div>
          {/* Module tabs */}
          <nav className="flex gap-1 -mb-px overflow-x-auto">
            {([
              ["report", "Berichterstellung"],
              ["phonology", "Ausspracheanalyse"],
              ["therapy-plan", "Therapieplan"],
              ["compare", "Berichtsvergleich"],
              ["suggest", "Textbausteine"],
            ] as [AppModule, string][]).map(([key, label]) => (
              <button
                key={key}
                onClick={() => setActiveModule(key)}
                className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                  activeModule === key
                    ? "border-indigo-500 text-indigo-400"
                    : "border-transparent text-muted-foreground hover:text-foreground hover:border-border"
                }`}
              >
                {label}
              </button>
            ))}
          </nav>
        </div>
      </header>
```

Replace with:
```tsx
      {/* Header */}
      <header className="border-b border-border print:hidden">
        <div className="max-w-5xl mx-auto px-6">
          {/* Top bar: breadcrumb + controls */}
          <div className="flex items-center justify-between h-12">
            <div className="flex items-center gap-2 text-sm">
              <span className="font-extrabold tracking-tight text-foreground">
                Logopädie
              </span>
              <span className="text-border-strong font-light">/</span>
              <span className="font-semibold" style={{ color: "var(--accent-text)" }}>
                {({
                  report: "Berichterstellung",
                  phonology: "Ausspracheanalyse",
                  "therapy-plan": "Therapieplan",
                  compare: "Berichtsvergleich",
                  suggest: "Textbausteine",
                } as Record<AppModule, string>)[activeModule]}
              </span>
            </div>
            <div className="flex items-center gap-3">
              <kbd className="hidden sm:inline-flex items-center gap-1 px-1.5 py-0.5 rounded border border-border-strong text-[10px] text-muted-foreground font-mono">
                ⌘K
              </kbd>
              <ThemeToggle />
            </div>
          </div>

          {/* Phase pills — report module only */}
          {activeModule === "report" && (
            <div className="flex items-center gap-2 pb-2 text-xs">
              {(
                [
                  { label: "① Anamnese", active: phase === "chat", done: phase !== "chat" },
                  { label: "② Material", active: phase === "upload", done: phase === "generating" || phase === "preview" },
                  { label: "③ Bericht", active: phase === "generating" || phase === "preview", done: false },
                ] as { label: string; active: boolean; done: boolean }[]
              ).map((step, i) => (
                <span key={i} className="flex items-center gap-2">
                  {i > 0 && <span className="text-muted-foreground">→</span>}
                  <span
                    className={`px-3 py-1 rounded-full font-medium transition-colors ${
                      step.active
                        ? "text-white"
                        : step.done
                        ? "text-accent-text"
                        : "text-muted-foreground"
                    }`}
                    style={
                      step.active
                        ? { background: "var(--accent)" }
                        : step.done
                        ? { background: "var(--accent-muted)" }
                        : { background: "var(--surface-elevated)" }
                    }
                  >
                    {step.label}
                  </span>
                </span>
              ))}
            </div>
          )}

          {/* Module tabs */}
          <nav className="flex gap-1 -mb-px overflow-x-auto">
            {([
              ["report", "Berichterstellung"],
              ["phonology", "Ausspracheanalyse"],
              ["therapy-plan", "Therapieplan"],
              ["compare", "Berichtsvergleich"],
              ["suggest", "Textbausteine"],
            ] as [AppModule, string][]).map(([key, label]) => (
              <button
                key={key}
                onClick={() => setActiveModule(key)}
                className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                  activeModule === key
                    ? "border-[var(--accent)] text-[var(--accent-text)]"
                    : "border-transparent text-muted-foreground hover:text-foreground hover:border-border-strong"
                }`}
              >
                {label}
              </button>
            ))}
          </nav>
        </div>
      </header>
```

- [ ] **Step 2: Remove the old PhaseStep component**

Find and delete the `PhaseStep` function (around line 1451):
```tsx
function PhaseStep({
  label,
  active,
  done,
}: {
  label: string;
  active: boolean;
  done: boolean;
}) {
  return (
    <span
      className={`px-2 py-0.5 rounded text-xs font-medium ${
        active
          ? "bg-indigo-600 text-white"
          : done
          ? "bg-surface-elevated text-muted-foreground line-through"
          : "text-muted-foreground"
      }`}
    >
      {label}
    </span>
  );
}
```

Delete it entirely — it is no longer used.

- [ ] **Step 3: Verify header**

Open http://localhost:3000:
- Header shows "Logopädie / Berichterstellung" with teal module name
- ⌘K badge visible top-right next to toggle
- Phase pills visible below breadcrumb (① Anamnese active in teal)
- Module tabs below with teal underline on active tab
- Switching modules updates the breadcrumb text and removes pills for non-report modules

- [ ] **Step 4: Commit**

```bash
git add frontend/src/app/page.tsx
git commit -m "design: replace header with breadcrumb + pill-steps + teal tabs"
```

---

## Task 4: Replace Indigo → Teal in page.tsx

**Files:**
- Modify: `frontend/src/app/page.tsx`

All remaining `indigo` Tailwind classes get replaced. This is a systematic find-and-replace pass.

- [ ] **Step 1: Replace primary button classes (multiple locations)**

Find all occurrences of:
```
bg-indigo-600 hover:bg-indigo-500
```
Replace all with:
```
bg-[var(--accent)] hover:bg-[var(--accent-hover)]
```

Affected lines (approx): 477, 492, 549, 582, 1007, 1116, 1193, 1264 — use editor find-and-replace for all occurrences.

- [ ] **Step 2: Replace input focus classes**

Find all occurrences of:
```
focus:border-indigo-500
```
Replace all with:
```
focus:border-[var(--ring)]
```

Affected lines (approx): 454, 976, 988, 996, 1385, 1395, 1407, 1418.

- [ ] **Step 3: Replace anamnesis-complete banner**

Find (around line 485):
```tsx
              <div className="flex items-center gap-3 rounded-lg bg-indigo-950/50 border border-indigo-800 px-5 py-4">
                <span className="text-sm text-indigo-300">
```
Replace with:
```tsx
              <div className="flex items-center gap-3 rounded-lg border px-5 py-4" style={{ background: "var(--accent-muted)", borderColor: "var(--accent)" }}>
                <span className="text-sm" style={{ color: "var(--accent-text)" }}>
```

- [ ] **Step 4: Replace ChatBubble indigo class**

Find (around line 610):
```tsx
            ? "bg-indigo-600 text-white rounded-br-md"
```
Replace with:
```tsx
            ? "text-white rounded-br-md"
```
And add `style` to the same element. Find the full ChatBubble `div` that contains this class:
```tsx
      <div
        className={`max-w-[80%] rounded-xl px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap ${
          role === "user"
            ? "bg-indigo-600 text-white rounded-br-md"
            : "bg-surface-elevated text-foreground rounded-bl-md"
        }`}
      >
```
Replace with:
```tsx
      <div
        className={`max-w-[80%] rounded-xl px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap ${
          role === "user"
            ? "text-white rounded-br-md"
            : "bg-surface-elevated text-foreground rounded-bl-md"
        }`}
        style={role === "user" ? { background: "var(--accent)" } : undefined}
      >
```

- [ ] **Step 5: Replace remaining scattered indigo references**

Find and replace each of these individually:

| Find | Replace |
|------|---------|
| `text-indigo-400` | `text-[var(--accent-text)]` |
| `text-indigo-300` | `text-[var(--accent-text)]` |
| `text-indigo-500` | `text-[var(--accent-text)]` |
| `hover:text-indigo-300` | `hover:text-[var(--accent-text)]` |
| `bg-indigo-900 text-indigo-300` | `bg-[var(--accent-muted)] text-[var(--accent-text)]` |
| `w-1.5 h-1.5 rounded-full bg-indigo-500` | `w-1.5 h-1.5 rounded-full bg-[var(--accent)]` |
| `hover:border-indigo-600` | `hover:border-[var(--accent)]` |

- [ ] **Step 6: Replace DropZone indigo classes (around line 793)**

Find:
```tsx
          ? "border-indigo-500 bg-indigo-500/10"
```
Replace with:
```tsx
          ? "border-[var(--accent)] bg-[var(--accent-muted)]"
```

Find (around line 799):
```tsx
        Dateien hierher ziehen oder <span className="text-indigo-500">durchsuchen</span>
```
Replace with:
```tsx
        Dateien hierher ziehen oder <span style={{ color: "var(--accent)" }}>durchsuchen</span>
```

- [ ] **Step 7: Verify — no indigo classes remain**

Run:
```bash
grep -n "indigo" frontend/src/app/page.tsx
```
Expected output: empty (no results).

- [ ] **Step 8: Commit**

```bash
git add frontend/src/app/page.tsx
git commit -m "design: replace all indigo color classes with teal accent tokens"
```

---

## Task 5: Unify WelcomeScreen Accent Colors

**Files:**
- Modify: `frontend/src/app/page.tsx` (WelcomeScreen component, around lines 627–695)

Currently each report-type card has a different accent color (indigo, emerald, violet, amber). All become teal.

- [ ] **Step 1: Replace the accent color map**

Find the `accentColors` object (around line 673):
```tsx
  const accentColors = {
    indigo: {
      icon: 'bg-indigo-500/15 text-indigo-400',
      ring: 'hover:ring-indigo-500/40 hover:border-indigo-500/50',
      badge: 'bg-indigo-500/10 text-indigo-400',
    },
    emerald: {
      icon: 'bg-emerald-500/15 text-emerald-400',
      ring: 'hover:ring-emerald-500/40 hover:border-emerald-500/50',
      badge: 'bg-emerald-500/10 text-emerald-400',
    },
    violet: {
      icon: 'bg-violet-500/15 text-violet-400',
      ring: 'hover:ring-violet-500/40 hover:border-violet-500/50',
      badge: 'bg-violet-500/10 text-violet-400',
    },
    amber: {
      icon: 'bg-amber-500/15 text-amber-400',
      ring: 'hover:ring-amber-500/40 hover:border-amber-500/50',
      badge: 'bg-amber-500/10 text-amber-400',
    },
  };
```
Replace with:
```tsx
  const accentColors = {
    indigo: {
      icon: 'bg-[var(--accent-muted)] text-[var(--accent-text)]',
      ring: 'hover:ring-[var(--accent)]/40 hover:border-[var(--accent)]/50',
      badge: 'bg-[var(--accent-muted)] text-[var(--accent-text)]',
    },
    emerald: {
      icon: 'bg-[var(--accent-muted)] text-[var(--accent-text)]',
      ring: 'hover:ring-[var(--accent)]/40 hover:border-[var(--accent)]/50',
      badge: 'bg-[var(--accent-muted)] text-[var(--accent-text)]',
    },
    violet: {
      icon: 'bg-[var(--accent-muted)] text-[var(--accent-text)]',
      ring: 'hover:ring-[var(--accent)]/40 hover:border-[var(--accent)]/50',
      badge: 'bg-[var(--accent-muted)] text-[var(--accent-text)]',
    },
    amber: {
      icon: 'bg-[var(--accent-muted)] text-[var(--accent-text)]',
      ring: 'hover:ring-[var(--accent)]/40 hover:border-[var(--accent)]/50',
      badge: 'bg-[var(--accent-muted)] text-[var(--accent-text)]',
    },
  };
```

- [ ] **Step 2: Replace WelcomeScreen subtitle indigo class**

Find (around line 705):
```tsx
        <p className="text-xs font-semibold tracking-widest text-indigo-400 uppercase">
```
Replace with:
```tsx
        <p className="text-xs font-semibold tracking-widest uppercase" style={{ color: "var(--accent-text)" }}>
```

- [ ] **Step 3: Verify WelcomeScreen**

Open http://localhost:3000, ensure chat phase is at greeting. All 4 report-type cards should have consistent teal icon backgrounds. No green/purple/amber cards.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/app/page.tsx
git commit -m "design: unify welcome screen card accents to teal"
```

---

## Task 6: Add Dark Mode Shadows to Cards

**Files:**
- Modify: `frontend/src/app/page.tsx`

In dark mode, card surfaces get elevation via `box-shadow`. We add a helper CSS class in `globals.css` and apply it to the chat container and section cards.

- [ ] **Step 1: Add shadow utility to globals.css**

Append to `frontend/src/app/globals.css`:
```css
/* ── Dark mode card elevation ── */
.dark .card-elevated {
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4), 0 0 0 1px rgba(255, 255, 255, 0.04);
}

.dark .btn-accent-glow {
  box-shadow: 0 2px 8px rgba(13, 148, 136, 0.35);
}
```

- [ ] **Step 2: Apply card-elevated to chat container**

Find (around line 428):
```tsx
            <div className="flex-1 flex flex-col gap-3 overflow-y-auto max-h-[60vh] rounded-lg border border-border bg-surface/50 p-4">
```
Replace with:
```tsx
            <div className="flex-1 flex flex-col gap-3 overflow-y-auto max-h-[60vh] rounded-lg border border-border bg-surface p-4 card-elevated">
```

- [ ] **Step 3: Apply btn-accent-glow to primary buttons**

Find the send button (around line 474):
```tsx
                className="px-6 py-3 rounded-lg bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-white font-medium text-sm transition-colors disabled:opacity-40"
```
Replace with:
```tsx
                className="px-6 py-3 rounded-lg bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-white font-medium text-sm transition-colors disabled:opacity-40 btn-accent-glow"
```

Apply the same `btn-accent-glow` addition to the "Bericht generieren" button (around line 549) and the "Weiter" button (around line 492).

- [ ] **Step 4: Verify dark mode elevation**

Switch to dark mode. The chat container should appear to float above the background with a visible shadow. Teal buttons have a subtle glow. Light mode: no visual change (utility only applies to `.dark`).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/globals.css frontend/src/app/page.tsx
git commit -m "design: add dark mode card elevation and button glow utilities"
```

---

## Task 7: Spinner and Minor Token Cleanup

**Files:**
- Modify: `frontend/src/app/page.tsx`

- [ ] **Step 1: Fix Spinner color**

Find (around line 1529):
```tsx
    <svg className="w-4 h-4 motion-safe:animate-spin text-indigo-400 shrink-0"
```
Replace with:
```tsx
    <svg className="w-4 h-4 motion-safe:animate-spin shrink-0" style={{ color: "var(--accent)" }}
```

- [ ] **Step 2: Verify no indigo remains anywhere**

```bash
grep -rn "indigo" frontend/src/
```
Expected: no output.

- [ ] **Step 3: Full smoke test**

Open http://localhost:3000 and check each module:
1. **Berichterstellung** — breadcrumb shows teal "Berichterstellung", phase pills visible, chat bubbles teal/slate, buttons teal
2. **Ausspracheanalyse** — breadcrumb shows "Ausspracheanalyse", no phase pills, teal analyze button
3. **Therapieplan** — breadcrumb shows "Therapieplan", teal generate button
4. **Berichtsvergleich** — breadcrumb shows "Berichtsvergleich", teal button
5. **Textbausteine** — breadcrumb shows "Textbausteine", teal interactions
6. Toggle light↔dark — smooth, pill switches, no layout flash, correct shadows in dark

- [ ] **Step 4: Final commit**

```bash
git add frontend/src/app/page.tsx
git commit -m "design: fix spinner color, complete teal+slate visual redesign"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Covered in task |
|-----------------|-----------------|
| Teal `#0d9488` accent, slate monochrome | Task 1 (globals.css) |
| Shadow variables (dark mode) | Task 1 + Task 6 |
| Pill-switch theme toggle | Task 2 |
| Breadcrumb header | Task 3 |
| Pill-steps for report phases | Task 3 |
| ⌘K hint (visual only) | Task 3 |
| Module tabs with teal underline | Task 3 |
| PhaseStep component removed | Task 3 |
| All indigo → teal | Task 4 |
| ChatBubble teal | Task 4 |
| WelcomeScreen unified teal | Task 5 |
| Dark mode card elevation | Task 6 |
| Teal button glow (dark) | Task 6 |
| Spinner teal | Task 7 |
| No structural changes | ✓ All tasks |

**Placeholder scan:** No TBDs. All replacement code is complete and exact.

**Type consistency:** `AppModule` type used in Task 3 breadcrumb lookup is the same type defined at line 62 of `page.tsx`. No new types introduced.
