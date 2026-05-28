# CURRENT.md — Current Working State

> **This file must be updated at the end of every meaningful AI session.**
> It represents the live state of the work — not a backlog, not a history.
> If it is out of date, the next agent will start from wrong assumptions.

---

## Last Updated

- **Date:** 2026-05-28
- **Updated by:** Claude Code
- **Session focus:** Audit follow-up — CI green-up, docs sync, Node 24 prep, AI state-file refresh

---

## Current Goal

No active agent-driven feature work. The owner (Sinan) is currently iterating
on the anamnesis flow himself (uncommitted WIP in
`backend/services/anamnesis_engine.py` and
`backend/services/phonological_analyzer.py` plus its test). Agents must NOT
touch those files until that work is settled.

---

## Current Branch

```text
main
```

`main` is at `9119077` (the last of three PRs that landed today). The local
working tree carries the owner's WIP files (above) — those are not agent
work and must not be staged or committed by an agent.

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

### In Progress

- Owner-driven: anamnesis engine + phonological analyzer iterations
  (uncommitted on local `main`). Agent-facing scope is paused on this area
  until those files settle.

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
HEAD:   9119077 chore(ci): opt JS actions into Node.js 24 ahead of 2026-06-02 cutover (#6)
Behind: 0
Ahead:  0
Uncommitted (owner WIP, do not touch):
  M backend/services/anamnesis_engine.py
  M backend/services/phonological_analyzer.py
  M backend/tests/test_phonological_analyzer.py
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
