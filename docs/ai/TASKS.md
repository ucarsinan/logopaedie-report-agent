# TASKS.md — AI Task Board

> Simple task board for AI agents and humans.
> Keep this file updated. Move tasks as they progress.
> One task = one checkbox. Be concrete enough that any agent can act on it.

---

## In Progress

- [ ] **Owner-driven (not agent work):** anamnesis engine + phonological analyzer
      iterations (uncommitted WIP on `main`). Agents must not touch
      `backend/services/anamnesis_engine.py`,
      `backend/services/phonological_analyzer.py`,
      `backend/services/anamnesis_catalog.py`, or
      `backend/tests/test_phonological_analyzer.py` until this is settled.

---

## Next

Tasks ready to be picked up by an agent once the WIP above clears. Ordered by priority (top = highest).

- [ ] **M-6** (audit 2026-05-26) — Anamnese-Abschlusslogik: when the
      anamnesis is complete, generate a structured handoff that wires into
      the report flow. Likely overlaps with the in-progress owner work →
      coordinate before starting.

### From 2026-05-29 performance audit (still open)

- [ ] Move `audit_service.log()` writes (`backend/services/audit_service.py:32`)
      to BackgroundTasks to eliminate the second per-request `db.commit()`.
- [ ] After Postgres EXPLAIN confirms the composite indexes from migration 0011
      are picked, drop the now-redundant single-column `ix_reports_user_id`,
      `ix_patients_user_id`, and `ix_therapyplanrecord_user_id` in a follow-up.

### From 2026-05-29 schema audit (`AUDIT_2026-05-29_schema.md`)

- [ ] **Land `0012_align_declared_fks` migration** — sketch ready in
      `docs/ai/AUDIT_2026-05-29_schema.md`. Conditional inspector pattern
      makes it a no-op on Neon for `therapyplanrecord.user_id` and additive
      on every other declared-but-not-enforced FK. Owner decision before
      apply.
- [ ] **Add `alembic check` CI step** — sketched in
      `docs/ai/AUDIT_2026-05-29_schema.md`. Would catch the next
      column-vs-FK split at PR time, structurally preventing the
      2026-05-29 incident class.
- [ ] **`ix_patients_pseudonym` index** — declared `index=True` on model,
      never created by migration 0007. Low severity, additive.
- [ ] **Type-encoding cleanup (`VARCHAR(36)` → `UUID`)** across 13
      legacy-id columns. Low priority; cosmetic until alembic autogenerate
      is on.
- [ ] **Fix `test_no_api_key_references` exclusion** — one-line: add
      `"worktrees"` to the exclusion tuple at
      `backend/tests/test_no_api_key_references.py:17`. Currently false-fails
      when `.claude/worktrees/` is present.

### Other

- [ ] Fix the pre-existing Vercel preview deploy failure (separate
      deployment-config issue; ignore for CI green-up).

---

## Done

- [x] Schema-vs-migrations static audit (parallel sub-agent A3) — report at `docs/ai/AUDIT_2026-05-29_schema.md`; sketches `0012_align_declared_fks` migration + `alembic check` CI step (no code commit) — 2026-05-29
- [x] Auth email path async end-to-end: `register` / `reset_request` / `resend` handlers + `AuthService.register` / `request_password_reset` / `resend_verification` + `EmailService.send_*` all async; `_run_send` sync bridge dropped (`0467587`) — 2026-05-29
- [x] `get_optional_user` JWT optimization: new `AuthIdentity` dataclass; per-request DB fetch removed from session-router endpoints; `get_current_user` chains on it for routers that need the full `User` row (`c0980ab`) — 2026-05-29
- [x] `GET /patients/{id}/history` pagination + `EmailService._send` async seam (`64800ce`) — 2026-05-29
- [x] Production assertions: `TRUSTED_PROXY` for rate-limiter, `SERVICE_TOKEN` for service-token middleware; flaky rate-limit tests hardened via unique per-test `X-Forwarded-For` IPs (`4117ae9`) — 2026-05-29
- [x] A11y/cleanup batch: skip-link, WorkflowStepper nav semantics, PatientPickerModal role placement, dark-mode `--muted-foreground` contrast, `useRegister` dead branch (`d8ea14e`) — 2026-05-29
- [x] A11y batch: nav `aria-current="page"`, icon-button labels, `motion-reduce` guards, input labels in TherapyPlanModule/SuggestModule/PhonologyModule, AuditLogTable `scope="col"`, ChatBubble SVG `aria-hidden`, ReportPreview disclaimer `role="alert"` (`f715700`) — 2026-05-29
- [x] Redis client singleton + duplicate SessionStore removal + migration 0011 with composite/partial indexes on reports/patients/therapyplanrecord (`5af7c4a`) — 2026-05-29
- [x] Security batch: rate limits on 6 previously-unlimited auth endpoints, `auto_verified` leak removed, audit offset capped (`c44de76`) — 2026-05-29
- [x] OnboardingOverlay real dialog with focus trap + Escape + focus rings (`5672716`) — 2026-05-29
- [x] PDF render offloaded to worker thread via `asyncio.to_thread` (`bbbe5ce`) — 2026-05-29
- [x] Logout BFF actually revokes backend session by forwarding `refresh_token` (`24eef4e`) — 2026-05-29
- [x] GeneratingView test moved into `__tests__/` for convention alignment (`6b37ba0`/`60a18c6`) — 2026-05-29
- [x] `_make_footer` mock pinned so `canvas._generated_at` is deterministic (`6b37ba0`) — 2026-05-29
- [x] TherapyPlanModule dead `sessionId` prop removal (`241f7fd`) — 2026-05-28
- [x] SOAPModule.generateFromReport stale-session 404 recovery (`11ce3cd`) — 2026-05-28
- [x] Therapy-plan ownership enforcement across GET-list / GET-by-id / PUT,
      plus test-file consolidation (`9c27c7e`) — 2026-05-28
- [x] PDF export typography, layout, and thread-safe per-render context
      (`6840168`) — 2026-05-28
- [x] Layout-aware loading skeletons for report / SOAP / therapy-plan
      (`36c29d0`) — 2026-05-28
- [x] Stale-session 404 wiring across modules (`c332a13`, `a56b1ef`) — 2026-05-28
- [x] Stale-session 404 via SessionProvider helper (`339b7a4`) — 2026-05-28
- [x] Derive onboarding overlay visibility instead of setState-in-effect
      (`fc2cab1`) — 2026-05-28
- [x] Extract `useOnboarding` hook (`11540d1`) — 2026-05-28
- [x] Reset picker `dismissed` on slug change (`cbf4d72`) — 2026-05-28
- [x] Centralize demo-mode access in `useDemoMode` (`129333c`) — 2026-05-28
- [x] Bump JS actions to v6 (Node-24-native), drop FORCE_JAVASCRIPT_ACTIONS_TO_NODE24
      flag (`4d1f0f6`) — 2026-05-28
- [x] Demo-mode persistence in module router (`ded7c1a`) — 2026-05-28
- [x] Opt JS actions into Node 24 (PR #6) — 2026-05-28
- [x] Sync CLAUDE.md + docs/ai/PROJECT.md with current architecture (PR #5, M-4) — 2026-05-28
- [x] CI E2E green-up — drop NEXT_PUBLIC_API_URL override (PR #4) — 2026-05-27
- [x] Security & quality audit fixes (PR #3): C-1/C-2, H-1..H-4, M-1/2/3/5, L-2/3/4 — 2026-05-27
- [x] Anamnesis slot-driven `process_message` + ICD derivation + report-lifecycle test alignment — 2026-05-26
- [x] Workflow template install + initial state-file fill — 2026-05-10
- [x] Multi-user auth — all 10 phases merged — 2026-05-09
- [x] E2E test stabilization (32 chromium tests) — 2026-05-09
- [x] UX polish — Suspense, ErrorBoundary, loading states — 2026-05-09

---

## Blocked

- **M-6** — blocked on owner's in-progress anamnesis work (see "In Progress").

---

## Parking Lot

- [ ] Gemini CLI integration: use Gemini for planning/review sessions to reduce Claude quota usage.
- [ ] SOAP notes UI improvement — currently raw text, could use structured display.
- [ ] Phonological analysis: add export to PDF.
- [ ] Consider adding session sharing / read-only report links.
- [ ] i18n: English version of the UI for broader portfolio appeal.

---

## Archive

<!-- Move completed tasks older than ~2 weeks here -->

- [x] Install ai-dev-workflow-template (AGENTS.md, GEMINI.md, docs/ai/, scripts/) — 2026-05-10
- [x] Fill all docs/ai/ template files with real project content — 2026-05-10
- [x] Resolve .new files — 2026-05-10
