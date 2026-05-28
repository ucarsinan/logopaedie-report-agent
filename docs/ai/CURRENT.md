# CURRENT.md — Current Working State

> **This file must be updated at the end of every meaningful AI session.**
> It represents the live state of the work — not a backlog, not a history.
> If it is out of date, the next agent will start from wrong assumptions.

---

## Last Updated

- **Date:** 2026-05-28
- **Updated by:** Claude Code
- **Session focus:** Dispatched three parallel agents for UI loading skeletons, PDF export quality, and backend test coverage; reviewed each in parallel; fixed reviewer-flagged high-priority items (PDF thread safety + therapy-plan ownership bugs); merged and pushed three thematic commits.

---

## Current Goal

No agent-driven goal active. The three "Next" items from the 2026-05-26
audit-followup backlog (UI skeletons, PDF export quality, therapy-plan /
SOAP / compare test coverage) landed today as `36c29d0`, `6840168`, and
`9c27c7e` and were pushed to `origin/main`.

**M-6** (anamnesis completion logic) remains the only outstanding
audit item and is still blocked on owner-driven WIP in
`backend/services/anamnesis_engine.py`, `phonological_analyzer.py`, and
`anamnesis_catalog.py`. Do not touch those files until the owner
explicitly hands them over.

Two sibling agents are running concurrently against the same working
tree on follow-ups to today's commits (SOAP stale-session branch +
TherapyPlanModule dead-prop investigation) — see "In Progress".

---

## Current Branch

```text
main
```

Local `main` is **at `origin/main`** (`9c27c7e`, 0 ahead / 0 behind).
The three thematic commits pushed earlier today are:

- `36c29d0` — `feat(frontend): add layout-aware loading skeletons for report/SOAP/therapy-plan`
- `6840168` — `feat(backend): improve PDF export typography, layout, and thread safety`
- `9c27c7e` — `feat(backend): enforce ownership on therapy-plan endpoints and consolidate tests`

Two follow-up commits landed after the three above and were pushed in
the same session:

- `11ce3cd` — `fix(frontend): wire SOAPModule.generateFromReport into stale-session helper`
- `241f7fd` — `refactor(frontend): drop unused sessionId prop from TherapyPlanModule`

Working tree currently carries only this state-file refresh.

---

## Status

### Done (recent — see `TASKS.md` "Done" for the full log)

- [x] Layout-aware loading skeletons for report / SOAP / therapy-plan
      (`36c29d0`, 2026-05-28) — new shared `frontend/src/components/Skeleton.tsx`
      primitive; layout-mirroring skeletons in `GeneratingView`, `SOAPModule`,
      and `TherapyPlanModule` (zero layout shift goal); `role="status"` +
      `aria-live` announcements; `motion-reduce:animate-none`. +4 vitest cases,
      163/163 green.
- [x] PDF export typography, layout, and thread safety (`6840168`, 2026-05-28) —
      `backend/services/pdf_generator.py` restructured with title / section /
      body hierarchy, running header (patient pseudonym + report type +
      `record.created_at`), "Seite X von Y" footer, A4 margins, KeepTogether
      section blocks, HR accent under headings. Module-level `_HEADER_CTX`
      replaced with a `_PageContext` dataclass captured per render via a
      closure-based `_make_on_page_hook` factory (defensive against future
      `loop.run_in_executor` use). `NumberedCanvas._generated_at` captures the
      timestamp once so both rendering passes agree across midnight UTC.
      Empty-list guard in `_build_section`. New `ThreadPoolExecutor` regression
      test `test_generate_pdf_no_cross_call_state_leak`. `backend/routers/exports.py`
      now passes `record.created_at` so the header date reflects the report,
      not the PDF-generation time. 397 → 399 backend tests.
- [x] Therapy-plan ownership enforcement + test consolidation (`9c27c7e`,
      2026-05-28) — closed three real security gaps in
      `backend/routers/therapy_plans.py`: `GET /therapy-plans` now filters
      on `user_id`, `GET /therapy-plans/{id}` and `PUT /therapy-plans/{id}`
      both enforce ownership, all three returning 404 (not 403, matching the
      `reports.py` / `sessions.py` convention to avoid leaking existence).
      `TherapyPlanRecord` gained a `user_id: UUID` FK mirroring `SOAPRecord`;
      alembic migration `0010_therapy_plan_user_id.py` follows the
      0005/0006 create-or-alter pattern (nullable column → delete orphans →
      flip to NOT NULL via `batch_alter_table` for SQLite). Same commit
      collapses duplicate test files: `test_soap.py` → `test_soap_routes.py`
      (8 unique cases absorbed), `test_therapy_plans.py` →
      `test_therapy_plans_routes.py` (new `TestGenerateTherapyPlanFromSession`
      class), `unauth_client` fixture promoted to `backend/tests/conftest.py`,
      and three new ownership-enforcement cases added. 399 backend tests green.
- [x] Stale-session 404 wiring across modules (`c332a13` / `a56b1ef`,
      2026-05-28) — earlier in this session, follow-ups to `339b7a4` landed
      (`ReportModule.generateReport`, `SOAPModule`, derived dismissed picker
      state) and were pushed.
- [x] Stale-session 404 via SessionProvider helper (`339b7a4`, 2026-05-28).
- [x] Derive onboarding overlay visibility instead of setState-in-effect
      (`fc2cab1`, 2026-05-28).
- [x] Reset picker `dismissed` on slug change (`cbf4d72`, 2026-05-28).
- [x] Extract `useOnboarding` hook (`11540d1`, 2026-05-28).
- [x] Centralize demo-mode access in `useDemoMode` (`129333c`, 2026-05-28).
- [x] Bump JS actions to v6 (Node-24-native) (`4d1f0f6`, 2026-05-28).
- [x] Demo-mode persistence in module router (`ded7c1a`, 2026-05-28).
- [x] Sync `CLAUDE.md` + `docs/ai/PROJECT.md` with current architecture
      (PR #5, 2026-05-28, M-4).
- [x] Opt JS actions into Node 24 ahead of 2026-06-02 cutover (PR #6, 2026-05-28).
- [x] CI E2E green-up — drop `NEXT_PUBLIC_API_URL` override (PR #4, 2026-05-27).
- [x] Security & quality audit fixes (PR #3, 2026-05-27): C-1/C-2, H-1..H-4,
      M-1/2/3/5, L-2/3/4.

### In Progress

- None on the agent side. Owner-driven anamnesis WIP continues (see "Blocked").

### Blocked

- **M-6** (anamnesis completion logic, from the 2026-05-26 audit) — still
  blocked on owner WIP in `anamnesis_engine.py`, `phonological_analyzer.py`,
  `anamnesis_catalog.py`, and `backend/tests/test_phonological_analyzer.py`.
  Pick up only after the WIP is committed/merged or the owner explicitly
  hands it over.

---

## Relevant Files

```text
.github/workflows/ci.yml                     — last touched by PR #4 and PR #6
CLAUDE.md                                    — last touched by PR #5
docs/ai/PROJECT.md                           — last touched by PR #5
docs/ai/CURRENT.md                           — this file
docs/ai/TASKS.md                             — task board
docs/ai/HANDOFF.md                           — handoff state
docs/ai/AUDIT_2026-05-26.md                  — source of the M-* / H-* / L-* / C-* items
backend/services/pdf_generator.py            — last touched by 6840168
backend/routers/exports.py                   — last touched by 6840168
backend/routers/therapy_plans.py             — last touched by 9c27c7e
backend/models/therapy_plan_record.py        — last touched by 9c27c7e
backend/alembic/versions/0010_therapy_plan_user_id.py — added by 9c27c7e
backend/tests/conftest.py                    — last touched by 9c27c7e
backend/tests/test_pdf_generator.py          — last touched by 6840168
backend/tests/test_soap_routes.py            — last touched by 9c27c7e
backend/tests/test_therapy_plans_routes.py   — last touched by 9c27c7e
frontend/src/components/Skeleton.tsx         — added by 36c29d0
frontend/src/features/report/components/GeneratingView.tsx        — last touched by 36c29d0
frontend/src/features/report/components/GeneratingView.test.tsx   — added by 36c29d0
frontend/src/features/soap/SOAPModule.tsx                         — last touched by 11ce3cd
frontend/src/features/therapy-plan/TherapyPlanModule.tsx          — last touched by 241f7fd
backend/services/anamnesis_engine.py         — owner WIP, do not touch
backend/services/phonological_analyzer.py    — owner WIP, do not touch
backend/services/anamnesis_catalog.py        — owner WIP, do not touch
backend/tests/test_phonological_analyzer.py  — owner WIP, do not touch
```

---

## Current Git State

```text
Branch: main
HEAD:   241f7fd refactor(frontend): drop unused sessionId prop from TherapyPlanModule
Behind: 0
Ahead:  0
Uncommitted:
  M docs/ai/CURRENT.md
  M docs/ai/TASKS.md
  M docs/ai/HANDOFF.md
```

---

## Known Problems

- **Vercel deploy check** fails on every PR with a separate deployment-config
  error. Pre-existing, unrelated to the CI workflow. Do not attempt to fix
  without explicit instruction from the owner.
- **Migration `0010_therapy_plan_user_id.py` is destructive on rollout.**
  It drops `therapyplanrecord` rows where `user_id IS NULL` before flipping
  the column to NOT NULL. Acceptable for the current portfolio/demo status;
  revisit before any production rollout where real users may have orphan
  rows from the pre-ownership era.
- **Commit `9c27c7e` message disclosure**: the message mentions a "trivial
  import-sort fix in three alembic migration tests"; that change was
  reverted by the pre-commit hook (`ruff format`) before it landed. `ruff
  check` is clean across the suite regardless. Minor message inaccuracy;
  not amended because the project rule is to prefer new commits over amend.
- `test_pdf_disclaimer.py` passes a `MagicMock` canvas, and
  `getattr(MagicMock, "_generated_at", None)` returns a `MagicMock`
  (truthy). Today's test only asserts the disclaimer string draw, which
  still passes, but a future test asserting the branding-line *text*
  would see `<MagicMock>` inside the string. Low priority.
- Backend test count drifts as anamnesis/phonology work continues — do not
  hard-code a pytest number in fresh docs (use a range like "~400").

---

## Assumptions Made

- Single-developer project (Sinan + Claude/Codex/Gemini). Multi-agent
  parallel writes only happen when the owner explicitly dispatches them;
  today's session is one such case (see "In Progress").
- Portfolio/demo status — no production users, but doc accuracy and CI
  hygiene still matter (it is the showcase). Destructive migrations are
  acceptable here only because of this status.

---

## Next Step

If the owner hands over: pick from `TASKS.md` "Next" column. Otherwise wait.

If picking work proactively, prefer items that do **not** touch
`backend/services/anamnesis_engine.py`, `phonological_analyzer.py`,
`anamnesis_catalog.py`, or the sibling-agent files listed under
"In Progress" until those settle.

---

## Notes for Next Agent

- Read this file plus `HANDOFF.md` first; both are current as of 2026-05-28.
- The full architectural picture is in `PROJECT.md`.
- Don't trust the cached "9 routers / 11 services / 6 CI jobs / 35 tests"
  numbers if you see them in older docs — they are pre-auth-rollout. The
  current numbers are 13 routers / ~22 services / 7 CI jobs / ~400 backend
  tests / 163 frontend tests.
- E2E: `cd frontend && npx playwright test` (chromium only).
- Backend: `cd backend && python -m pytest`.
- Dev: `./dev.sh`.
- BFF architecture: browser → `/auth-api/*` or `/backend-api/*` Next route
  handlers → backend. Never client-direct. Playwright mocks match
  `**/backend-api/**` and `**/auth-api/**`.
