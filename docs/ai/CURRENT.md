# CURRENT.md — Current Working State

> **This file must be updated at the end of every meaningful AI session.**
> It represents the live state of the work — not a backlog, not a history.
> If it is out of date, the next agent will start from wrong assumptions.

---

## Last Updated

- **Date:** 2026-05-31 (morning)
- **Updated by:** Claude Code
- **Session focus:** Fifth parallel-agent wave (E1, E2, E3) + F1 inline. E1 found the real cause behind the stuck I001 baseline — a ruff version pin skew, not the hook-id conflict we assumed — and cleared it by bumping ruff to 0.15.15. E2 landed `0013_audit_log_id_uuid_type` as proof-of-pattern for the broader VARCHAR(36)→UUID alignment. E3 reviewed D1/D2 and flagged F1 (T3 logger leak), applied inline. Pre-push gotcha discovered: the hook false-fails on unstaged changes — commit docs first.

---

## Current Goal

No agent-driven goal active. The three follow-ups dispatched this late
evening (C1 null, C2, C3+M2) all landed; remaining `TASKS.md` "Next" is
LOW-severity follow-ups (T1/T2/T3 missing BG-tests, M4 refresh audit
gap, `VARCHAR(36)→UUID` type alignment, dropping redundant
single-column `ix_*_user_id` indexes after EXPLAIN).

**M-6** (anamnesis completion logic) remains the outstanding audit item
and is still blocked on owner-driven WIP in
`backend/services/anamnesis_engine.py`, `phonological_analyzer.py`, and
`anamnesis_catalog.py`. Treat them as untouchable until the owner
explicitly hands them over.

---

## Current Branch

```text
main
```

Local `main` is **3 ahead of `origin/main`** (E1/E2/F1 commits not yet
pushed). About to push: `e089942` + `0e5d302` + `16aad7e` + this docs
commit.
Today's commits (newest first):

- `16aad7e` — `fix(tests): scope T3's audit-logger re-enable via monkeypatch (F1 from E3 review)`
- `0e5d302` — `feat(backend): land 0013_audit_log_id_uuid_type migration`
- `e089942` — `chore(tooling): bump ruff to 0.15.15 + clear the I001 baseline`
- `1abc5a5` — `docs(ai): record D1/D2/D3 overnight batch — T1/T2/T3 + M4 done, D3 blocked`
- `44ff83b` — `feat(backend): emit audit row on AuthService.refresh happy path`
- `3d57bc1` — `test(backend): add T1+T2+T3 end-to-end tests for audit BackgroundTasks path`
- `166c09d` — `docs(ai): record C1/C2/C3 late-evening batch and surface T1/T2/T3/M4 follow-ups`
- `222c708` — `fix(backend): assert (background, db_factory) pass together in AuthService._audit`
- `90c51e3` — `fix(backend): drop ix_patients_pseudonym index declaration; alembic check now strict`
- `6c18482` — `perf(backend): defer audit_service.log() writes to BackgroundTasks`
- `1a53f79` — `docs(ai): record A1/A2 commits and persist A3 schema audit`
- `0467587` — `perf(backend): make auth email path async end-to-end`
- `c0980ab` — `perf(backend): skip per-request DB fetch in get_optional_user; add AuthIdentity`

Working tree carries the docs/ai state-file refresh for this
overnight session.

---

## Status

### Done (recent — see `TASKS.md` "Done" for the full log)

- [x] **M4: refresh happy-path audit row** (D2, `44ff83b`, 2026-05-29
      overnight) — `AuthService.refresh()` now emits
      `event="user.token_refreshed"` with `metadata={"old_session_id":
      ..., "new_session_id": ...}` via the standard `_audit` router.
      Discovery: the route handler in `routers/auth.py` was already
      wired with `background_tasks` + `db_factory` from `6c18482`; only
      the svc-side emit was missing. The reuse-detection branch's
      `session.refresh_reuse_detected` emit was already in place.
- [x] **T1 + T2 + T3 BG-audit end-to-end tests** (D1, `3d57bc1`,
      2026-05-29 overnight) — T1 drives `log_in_background` directly
      with a fresh-session factory and asserts the row lands; T2 hits
      `/admin/users/{id}/lock` and queries `/admin/audit` to confirm
      the row materialized post-response; T3 monkeypatches
      `Session.commit` to raise and asserts the worker swallows + logs.
      T3 verified by removing the `except` clause and watching it fail.
      Subtlety caught: `alembic.ini`'s `disable_existing_loggers=True`
      disables `services.audit_service` when alembic tests load first;
      T3 re-enables it before the assertion. Closes C3's Medium-risk
      rating on `6c18482`.
- [x] **D3 (failed) — pre-commit-vs-`ruff check` I001 conflict** —
      D3 produced a sort that `ruff check --fix` accepts but the
      project's `.pre-commit-config.yaml` "ruff (legacy alias)" hook
      reverts it (the conflict `9c27c7e` flagged is still live). No
      code commit; conflict promoted to `TASKS.md` "Open follow-ups"
      so a future agent can adjust the hook config (not the test
      files).
- [x] **`AuthService._audit` partial-wiring assert** (M2 from C3 review,
      `222c708`, 2026-05-29 late evening) — `assert (background is None)
      == (db_factory is None)` so a future route refactor that wires
      only one of the two new deps fails loud instead of silently
      degrading to the sync audit path. The C3 review of `6c18482`
      flagged this as the highest-confidence Medium-risk follow-up.
- [x] **`ix_patients_pseudonym` drift resolved** (C2, `90c51e3`,
      2026-05-29 late evening) — model-declaration drop chosen over a
      0013 index migration. Call-site audit: `routers/patients.py:113`
      uses `ILIKE '%q%'` (leading wildcard, B-tree useless; gin_trgm_ops
      would be needed) and is always co-anded with user_id +
      deleted_at, which `idx_patients_user_active` from 0011 covers;
      `routers/reports.py:57` only projects pseudonym on a JOIN over PK.
      Filter entry removed from `_MIGRATION_ONLY_INDEXES` so
      `alembic check` now actively enforces the absence. New
      `test_patient_pseudonym_has_no_standalone_index` regression guard.
- [x] **C1 — audit-wiring extension audit** (C1, no commit) — grep
      confirmed every audit-emitting site was already converted in
      `6c18482`. The "remaining routers" called out in the prior
      handoff (`reports.py`, `sessions.py`, etc.) have zero audit
      references; HANDOFF anticipated work that doesn't exist. 31 tool
      calls, null diff, useful negative result.
- [x] **C3 — code review of `6c18482`** (C3, report only) — read-only
      review of the B1 BackgroundTasks audit refactor whose final
      summary was lost to a socket error. No Critical, three High judged
      safe-as-landed, one Medium applied inline (M2), three missing
      tests (T1/T2/T3) and one pre-existing gap (M4) tracked in
      `TASKS.md`.
- [x] **`test_no_api_key_references` scoped exclusions** (B3,
      `33c542e`, 2026-05-29 evening) — switched from absolute
      `path.parts` to `relative_to(root).parts`; added `.claude` +
      `worktrees` to the exclusion set. Latent bug: the absolute-path
      comparison would have silently passed on *every* file when run
      from inside `.claude/worktrees/<agent-id>/` if `.claude` was
      naively added to the existing tuple. 419/419.
- [x] **`0012_align_declared_fks` + `alembic check` CI guard** (B2,
      `6e31983`, 2026-05-29 evening) — migration emits 7 declared FKs
      idempotently via `inspector.get_foreign_keys()` guards (no-op on
      Neon for the manually-hotfixed `therapyplanrecord.user_id`).
      `env.py` gets missing `models.patient` import + `compare_type=False`
      + `_MIGRATION_ONLY_INDEXES` filter excluding the 0011 composites
      and `ix_patients_pseudonym` (both deferred to a future 0013).
      `.github/workflows/ci.yml` runs `alembic upgrade head && alembic
      check` after pytest. New `test_migration_0012.py` covers upgrade /
      idempotency / downgrade. 422/422 (419 + 3 new).
- [x] **`audit_service.log()` → BackgroundTasks** (B1, `6c18482`,
      2026-05-29 evening) — new `audit_service.log_in_background(...)`
      schedules `_persist_with_fresh_session` after the response; new
      `database.get_db_factory(request)` resolves
      `dependency_overrides[get_db]` at request time so the background
      task opens its own session against the same engine (including test
      overrides). `AuthService` methods gain optional `(background,
      db_factory)` kwargs + internal `_audit()` router. Routes in
      `routers/auth.py`, `routers/auth_admin.py`, `routers/patients.py`
      wire the deferred path; remaining routers still take the sync
      path (follow-up).
- [x] **Schema-vs-migrations static audit** (A3, 2026-05-29 PM) — no
      missing-column drift found (0010 closed that class); persistent
      risk is FK constraints declared on models but never emitted by
      migrations (6 columns + the manually-hotfixed
      `therapyplanrecord.user_id`). Report at
      `docs/ai/AUDIT_2026-05-29_schema.md`; sketched
      `0012_align_declared_fks` migration uses the conditional
      `inspector.get_foreign_keys` pattern so it's a no-op on Neon for the
      hotfixed row and additive elsewhere. Recommends `alembic check` as
      a CI guard. No code commit.
- [x] **Auth email path async end-to-end** (`0467587`, 2026-05-29 PM) —
      A2 flipped `register` / `reset_request` / `resend` to `async def`,
      made the corresponding `AuthService` methods async, dropped
      `EmailService._run_send`, and turned `send_verify_email` /
      `send_password_reset` into coroutines that `await self._send`.
      `FakeEmailService.send_*` mirrored. Tests adjusted to async + await
      (pytest-asyncio already in auto mode). 13 other handlers stayed
      sync — no email/no async dep, so no event-loop benefit. 419/419.
- [x] **`get_optional_user` JWT optimization** (`c0980ab`, 2026-05-29 PM)
      — A1 introduced `AuthIdentity` (`id`, `role`, `sid`) frozen-slots
      dataclass built from `request.state.user`; removed `Depends(get_db)`
      from `get_optional_user`. The 9 endpoints in
      `backend/routers/sessions.py` only ever read `user.id` so this is
      behavior-preserving. `get_current_user` chains on the optional dep,
      still returns the full `User` row for routers that need it; accepts
      `AuthIdentity | User` so existing `dependency_overrides[…] = lambda:
      fake_user` test fixtures keep working via `isinstance`. 418 → 418.
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
HEAD:   44ff83b feat(backend): emit audit row on AuthService.refresh happy path
Behind: 0
Ahead:  0 (D1 + D2 pushed; this docs commit goes next)
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

The natural next item is **fixing the pre-commit-vs-`ruff check` I001
conflict** so the 4-error baseline can actually clear. D3's worktree
attempt was reverted by `.pre-commit-config.yaml`'s "ruff (legacy
alias)" hook, which enforces a sort `ruff check` rejects. Real fix:
replace the legacy alias with `ruff check --fix` in the hook config
(so it respects `pyproject.toml` like the local CLI does) OR adjust
the isort config in `pyproject.toml`. Verify by running `pre-commit
run --all-files` locally before and after.

Otherwise pick from `TASKS.md` "Next" / "Open follow-ups". Remaining
items are all LOW-severity (`VARCHAR(36)→UUID` type alignment as a
0013_* migration, dropping redundant single-column `ix_*_user_id`
indexes after EXPLAIN verification on Neon). Don't touch
`anamnesis_engine.py`, `phonological_analyzer.py`, `anamnesis_catalog.py`,
or `test_phonological_analyzer.py` until the owner explicitly hands
them over.

---

## Notes for Next Agent

- Read this file plus `HANDOFF.md` first; both are current as of 2026-05-29
  (overnight). The session chain in `HANDOFF.md`: overnight (D1/D2/D3 —
  audit testing + refresh audit) → late evening (C1/C2/C3 — pseudonym
  drift + C3 review of B1) → evening (B1/B2/B3 — closing the FK class)
  → PM (A1/A2/A3 — perf + audit) → earlier 2026-05-29 (the original
  schema-drift hotfix).
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
