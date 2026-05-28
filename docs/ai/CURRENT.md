# CURRENT.md — Current Working State

> **This file must be updated at the end of every meaningful AI session.**
> It represents the live state of the work — not a backlog, not a history.
> If it is out of date, the next agent will start from wrong assumptions.

---

## Last Updated

- **Date:** 2026-05-28
- **Updated by:** Claude Code
- **Session focus:** Anamnesis pseudonym-verbatim rule + SSR/CSR hydration fix in useDemoMode

---

## Current Goal

No active agent-driven feature work. Two small fixes landed this session
on local `main` (not yet pushed):

- `feat(anamnesis): accept free-form pseudonyms verbatim` (`8879cad`) —
  both anamnesis and therapy-plan prompts now accept short/free-form
  pseudonyms (e.g. `ji`, `X`, `AB`) without re-asking. Pure prompt
  change, no Python logic, all 383 backend tests green.
- `fix(frontend): avoid SSR/CSR mismatch in useDemoMode` (`92bb84a`) —
  `localStorage` read moved out of the render body into `useEffect`,
  initial state `false`. 11/11 hook tests green.

**M-6** (anamnesis completion logic) is still the remaining 2026-05-26
audit item — confirm with the owner before picking it up, since the area
is owner-driven.

---

## Current Branch

```text
main
```

Local `main` is **3 commits ahead** of `origin/main`:
`8879cad` (anamnesis pseudonym verbatim) → `92bb84a` (useDemoMode SSR
fix) → this state-file refresh. Working tree is clean.

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
- [x] useDemoMode SSR/CSR hydration fix (`92bb84a`, 2026-05-28).

### In Progress

- Nothing in progress. `main` carries three unpushed commits ready for
  `git push`.

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
HEAD:   92bb84a fix(frontend): avoid SSR/CSR mismatch in useDemoMode
Behind: 0
Ahead:  3   (8879cad, 92bb84a, plus this CURRENT.md refresh)
Uncommitted: none
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
