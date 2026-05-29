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

### From 2026-05-29 security audit (High)

- [ ] Restrict `X-Forwarded-For` trust in `backend/middleware/rate_limiter.py:27-39`
      to known proxy CIDRs, or assert `TRUSTED_PROXY` is configured at startup.
      Right now any client can spoof the header and bypass IP rate limits.
- [ ] Add `@limiter.limit("3/hour")` to `POST /auth/resend-verification`
      (`backend/routers/auth.py:251-260`) — currently unlimited email-flooding vector.
- [ ] Add `@limiter.limit("10/hour")` to `POST /auth/password/reset/confirm`
      (`backend/routers/auth.py:210-223`) — defense-in-depth on the reset path.
- [ ] Add `@limiter.limit("5/minute")` to `POST /auth/2fa/enable` and
      `POST /auth/2fa/disable` (`backend/routers/auth.py:284-309`).
- [ ] Add rate limits to `verify-email` and `password/change` endpoints
      (`backend/routers/auth.py:109-122` and `:226-248`).
- [ ] Remove `auto_verified` field from `POST /auth/register` response
      (`backend/routers/auth.py:106`) — leaks production config state to
      unauthenticated callers.
- [ ] Harden `ServiceTokenMiddleware` fail-open behavior
      (`backend/middleware/service_token.py:20-22`): assert `SERVICE_TOKEN`
      is set when `ENV=production`, raise on missing rather than passing all
      requests through.
- [ ] Cap `offset` on `GET /admin/audit` (`backend/routers/auth_admin.py:26-31`)
      — admin pagination can trigger unbounded scans as the audit table grows.

### From 2026-05-29 performance audit (High)

- [ ] Replace per-call Redis client construction in `backend/services/session_store.py:48-53`
      with a module-level singleton — currently rebuilt 2-3× per session-touching request.
- [ ] Remove duplicate `SessionStore()` in `backend/routers/soap.py:23`;
      import and reuse the singleton from `services.session_store`.
- [ ] Add migration: `CREATE INDEX idx_reports_user_created ON reports(user_id, created_at DESC)`
      and `CREATE INDEX idx_reports_patient_id ON reports(patient_id)` — current
      list/stats endpoints fall back to full index scans for users with many reports.
- [ ] Add migration: partial composite index on `patients(user_id, created_at DESC) WHERE deleted_at IS NULL`.
- [ ] Add migration: composite `(user_id, created_at DESC)` on `therapyplanrecord`
      (migration 0010 only added single-column `user_id` index).
- [ ] Add `limit`/`offset` pagination to `GET /patients/{id}/history`
      (`backend/routers/patients.py:205-227`) — currently returns all reports unbounded.
- [ ] Wrap `EmailService._send()` (`backend/services/email_service.py:22`)
      with `asyncio.to_thread` or push to FastAPI BackgroundTasks — sync
      Resend SDK call blocks the event loop on every auth email.
- [ ] Move `audit_service.log()` writes (`backend/services/audit_service.py:32`)
      to BackgroundTasks to eliminate the second per-request `db.commit()`.
- [ ] Evaluate `get_optional_user` (`backend/dependencies.py:140-148`):
      JWT payload already has user id + role, the per-request DB fetch is
      unnecessary on most endpoints.

### From 2026-05-29 a11y audit (High)

- [ ] Add `aria-current="page"` to nav links in `AppShell` and `MobileSidebar`.
- [ ] Add `aria-label="Aufnahme stoppen"` and `aria-label="Transkription läuft"`
      to `DictationButton` icon-only buttons (`frontend/src/features/chat/components/DictationButton.tsx:28-43`).
- [ ] Add `motion-reduce:animate-none` to `TypingIndicator` bounce dots
      (`frontend/src/features/chat/components/ChatBubble.tsx:89-91`) and
      `TypingDemo` blink/pulse (`frontend/src/components/landing/TypingDemo.tsx:32,39`).
- [ ] Add `<label>` / `aria-label` to unlabelled inputs: `TherapyPlanModule`
      mini-chat (`TherapyPlanModule.tsx:304`), `SuggestModule` textarea
      (`SuggestModule.tsx:103`), `PhonologyModule` word-pair rows
      (`PhonologyModule.tsx:88-116`).
- [ ] Add `scope="col"` to `<th>` cells in `AuditLogTable.tsx:88-96`.
- [ ] Move `role="dialog" aria-modal="true"` from the backdrop to the inner panel
      `<div ref={dialogRef}>` in `PatientPickerModal.tsx:73-93`.
- [ ] Add skip-to-main-content link before `<header>` in `AppShell.tsx`.
- [ ] Wrap `WorkflowStepper` in `<nav aria-label="Arbeitsschritte">` and add
      `aria-current="step"` + step-number labels (`WorkflowStepper.tsx:31-53`).
- [ ] Add `aria-hidden="true"` to decorative AI robot SVGs in `ChatBubble.tsx:27-30,82-85`.
- [ ] Change `ReportPreview` AI disclaimer from `role="note"` to `role="alert"`
      so it announces on report load (`ReportPreview.tsx:27-32`).
- [ ] Audit dark-mode `--muted-foreground` (#64748b) contrast on `--surface`
      (#1e293b) — currently ~3.7:1 for small text, below AA.

### Other

- [ ] Fix the pre-existing Vercel preview deploy failure (separate
      deployment-config issue; ignore for CI green-up).

---

## Done

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
