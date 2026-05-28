# CURRENT.md — Current Working State

> **This file must be updated at the end of every meaningful AI session.**
> It represents the live state of the work — not a backlog, not a history.
> If it is out of date, the next agent will start from wrong assumptions.

---

## Last Updated

- **Date:** 2026-05-28
- **Updated by:** Claude Code
- **Session focus:** Follow-ups to the demo-mode fix surfaced by parallel code-review + repo-scan agents: centralize the `"demo_mode"` localStorage key in `useDemoMode`, reset the picker `dismissed` flag on module slug change, and extract a sibling `useOnboarding` hook for the `"logopaedie_onboarding_done"` key.

---

## Current Goal

Three new local commits ready to push (stacked on top of the previously
pushed `a3ba15a`):

- `129333c` — `refactor(frontend): centralize demo_mode access in useDemoMode`
  (adds `getDemoMode`/`setDemoMode` exports, migrates `ReportModule` +
  `LoginForm` + `useRegister` off direct `localStorage` writes, fixes
  the fragile `window.location.search.includes("demo=true")` parse).
- `cbf4d72` — `fix(frontend): reset dismissed picker state on module slug change`
  (latent bug exposed by the original demo persistence fix `ded7c1a`).
- `11540d1` — `refactor(frontend): extract useOnboarding hook from module layout`
  (mirrors the `useDemoMode` pattern for `"logopaedie_onboarding_done"`).

**M-6** (anamnesis completion logic) is still the remaining 2026-05-26
audit item — confirm with the owner before picking it up, since the area
is owner-driven.

---

## Current Branch

```text
main
```

Local `main` is **3 commits ahead** of `origin/main` (`a3ba15a`):
`129333c` (demo centralization) → `cbf4d72` (picker dismissed reset) →
`11540d1` (useOnboarding extraction). Working tree carries only this
state-file update plus owner-WIP in
`frontend/src/lib/api.ts` + `frontend/src/features/report/__tests__/ReportModule.test.tsx`
(an `ApiError` extraction with a stale-session 404 recovery test — not
touched by this session's commits).

---

## Status

### Done (recent — see `TASKS.md` "Done" for the full log)

- [x] Security & quality audit fixes (PR #3, 2026-05-27): C-1/C-2, H-1..H-4,
      M-1/2/3/5, L-2/3/4
- [x] CI E2E green-up — drop `NEXT_PUBLIC_API_URL` override (PR #4, 2026-05-27)
- [x] Sync `CLAUDE.md` + `docs/ai/PROJECT.md` with current architecture
      (PR #5, 2026-05-28, M-4)
- [x] Opt JS actions into Node 24 ahead of 2026-06-02 cutover (PR #6, 2026-05-28)
- [x] Branch cleanup: deleted three merged stale branches
      (`claude-security-fixes`, `feat/anamnese-slot-flow`,
      `security-audit-followup`) and the now-obsolete
      `project_security_quarantine_branch.md` memory entry.
- [x] Anamnesis pseudonym verbatim rule (`8879cad`, 2026-05-28) —
      both system + extraction prompts in `anamnesis_engine.py`.
- [x] useDemoMode SSR/CSR hydration fix (`92bb84a`, 2026-05-28),
      refactored to `useSyncExternalStore` in `f326f95` (lint-clean,
      handles cross-tab changes).
- [x] Move preview noindex header out of `vercel.json` into
      `next.config.ts` (`02b5be0`, 2026-05-28) — vercel.json schema
      rejected `has.type: "env"`.
- [x] Demo-mode persistence in module router (`ded7c1a`, 2026-05-28) —
      `frontend/src/app/module/[slug]/page.tsx` now reads `isDemo` from
      the shared `useDemoMode()` hook (URL **or** persisted localStorage)
      instead of the URL-only `searchParams.get("demo")`. Fixes the
      regression where the patient picker re-appeared after navigating
      between `/module/*` slugs even though demo mode was active.
      `tsc` clean, all 146 vitest tests green.
- [x] Bump JS actions to v6 (`4d1f0f6`, 2026-05-28) — checkout v4→v6,
      setup-node v4→v6, setup-python v5→v6; dropped the
      `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24` env flag (no longer needed
      since all three majors ship Node 24 natively). YAML validated;
      `ubuntu-latest` runners auto-satisfy the v2.327.1+ requirement.
- [x] Centralize demo-mode access in `useDemoMode` (`129333c`,
      2026-05-28) — new `getDemoMode()` snapshot + `setDemoMode(value)`
      setter with a same-tab `demo-mode-changed` event. `ReportModule`
      (init read + `onDemo` setter), `LoginForm`, and `useRegister` all
      migrated off direct `localStorage` access. Robust URL parse via
      `URLSearchParams` replaces the fragile
      `window.location.search.includes("demo=true")`. +7 vitest cases
      (18 total on `useDemoMode`).
- [x] Reset picker `dismissed` on slug change (`cbf4d72`, 2026-05-28) —
      `ModuleContent` now clears the dismissed flag whenever `slug`
      changes. Latent bug exposed once `ded7c1a` removed the URL-derived
      re-evaluation; dismissing the picker on `/module/report` no
      longer suppresses it on later `/module/*` visits.
- [x] Extract `useOnboarding` hook (`11540d1`, 2026-05-28) — same
      pattern as `useDemoMode` for `"logopaedie_onboarding_done"`:
      `useSyncExternalStore`-backed hook plus `markOnboardingDone()` /
      `resetOnboarding()` helpers. `module/layout.tsx` dropped the
      `setTimeout(0)` + direct `localStorage` read. +5 vitest cases.

### In Progress

- Nothing in progress. Three local commits pending push.

### Blocked

- **M-6** (anamnesis completion logic, from the 2026-05-26 audit) — blocked
  on the in-progress owner work above. Pick up only after the WIP is
  committed/merged or the owner explicitly hands it over.

---

## Relevant Files

```text
.github/workflows/ci.yml          — last touched by PR #4 and PR #6
CLAUDE.md                         — last touched by PR #5
docs/ai/PROJECT.md                — last touched by PR #5
docs/ai/CURRENT.md                — this file
docs/ai/TASKS.md                  — task board
docs/ai/HANDOFF.md                — handoff state
docs/ai/AUDIT_2026-05-26.md       — source of the M-* / H-* / L-* / C-* items
backend/services/anamnesis_engine.py
backend/services/phonological_analyzer.py
backend/tests/test_phonological_analyzer.py
```

---

## Current Git State

```text
Branch: main
HEAD:   11540d1 refactor(frontend): extract useOnboarding hook from module layout
Behind: 0
Ahead:  3   (129333c, cbf4d72, 11540d1)
Uncommitted:
  M docs/ai/CURRENT.md
  M docs/ai/HANDOFF.md
  M frontend/src/features/report/__tests__/ReportModule.test.tsx   (owner WIP)
  M frontend/src/lib/api.ts                                        (owner WIP)
```

---

## Known Problems

- **Vercel deploy check** fails on every PR with a separate deployment-config
  error. Pre-existing, unrelated to the CI workflow. Do not attempt to fix
  without explicit instruction from the owner.
- Backend test count drifts as anamnesis/phonology work continues — do not
  hard-code a pytest number in fresh docs (use a range like "~270").

---

## Assumptions Made

- Single-developer project (Sinan + Claude/Codex/Gemini). No multi-agent
  parallel write conflicts unless an agent touches files the owner is
  actively editing.
- Portfolio/demo status — no production users, but doc accuracy and CI
  hygiene still matter (it is the showcase).

---

## Next Step

If the owner hands over: pick from `TASKS.md` "Next" column. Otherwise wait.

If picking work proactively, prefer items that do **not** touch
`backend/services/anamnesis_engine.py`, `phonological_analyzer.py`, or
`anamnesis_catalog.py` until M-6 is unblocked.

---

## Notes for Next Agent

- Read this file plus `HANDOFF.md` first; both are current as of 2026-05-28.
- The full architectural picture is in `PROJECT.md` (also freshly synced).
- Don't trust the cached "9 routers / 11 services / 6 CI jobs / 35 tests"
  numbers if you see them in older docs — they are pre-auth-rollout. The
  current numbers are 13 routers / ~22 services / 7 CI jobs / ~270 backend tests.
- E2E: `cd frontend && npx playwright test` (chromium only).
- Backend: `cd backend && python -m pytest`.
- Dev: `./dev.sh`.
- BFF architecture: browser → `/auth-api/*` or `/backend-api/*` Next route
  handlers → backend. Never client-direct. Playwright mocks match
  `**/backend-api/**` and `**/auth-api/**`.
