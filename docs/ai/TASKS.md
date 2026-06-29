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

- [ ] After Postgres EXPLAIN confirms the composite indexes from migration 0011
      are picked, drop the now-redundant single-column `ix_reports_user_id`,
      `ix_patients_user_id`, and `ix_therapyplanrecord_user_id` in a follow-up.

### Still open after M-wave (all non-agent-actionable)

- [ ] **S-8** (informational) — `get_optional_user` does not check
      `locked_until` / `email_verified` / `revoked_at`. Documented
      trade-off from `c0980ab`. Only safe while every consumer reads
      `user.id` and nothing else; add a runtime guard if more
      handlers adopt `AuthIdentity`.
- [ ] **X-RateLimit-* response headers** — slowapi 0.1.9
      `headers_enabled=True` is incompatible with FastAPI dict
      handlers (raises `parameter response must be Response`).
      L2's broad attempt broke 85 tests. Requires either slowapi
      version bump OR per-route refactor returning `JSONResponse`.
      Deferred indefinitely.
- [x] **`.env.example` `TRUSTED_PROXY` entry** — resolved by setting
      env vars directly in Vercel dashboard (2026-06-03). TRUSTED_PROXY,
      SERVICE_TOKEN, JWT_SECRET, SESSION_ENCRYPTION_KEY, PATIENT_ENCRYPTION_KEY,
      RATE_LIMIT_REDIS_URL all added to Vercel production.
- [x] **`login_2fa:755` compound assert** — fixed in N1 as `c941910`.

### Open follow-ups

- [ ] **Frontend `end-of-file-fixer` baseline** — visible after E1's
      pre-commit `--all-files` run. 5 `frontend/public/*.svg` files
      were missing trailing newlines and were fixed as part of `e089942`.
      No further frontend hygiene gap surfaced; leave as a watch item.

### Other

- [ ] Add/restore `scripts/verify.sh` or document the canonical replacement
      command before final Git close-out. A close-out planning run on
      2026-06-29 could not execute it because the file does not exist.
- [ ] Verify Vercel Preview deploy after local hardening — requires explicit
      human approval to run `vercel deploy`. Expected smoke: Preview deployment
      Ready, frontend 200, `/api/livez` 200, `/api/health` 401 without service
      token.
---

## Done

- [x] **Split and land remaining dirty scopes** (2026-06-29) — Used three
      parallel explorer agents to audit backend N2 cleanup, claim/presentation
      cleanup, and docs/testing + AI-state scope. Landed separate commits for
      backend token/health edge cases, demo claim/presentation alignment, and
      manual QA docs. AI-state/reality docs are handled in the final Scribe
      commit for this session. No broad `git add .` was used.
- [x] **Vercel Preview local hardening** (2026-06-29) — Investigated old
      Preview Error deployments with two explorer agents and Vercel CLI.
      Old logs were unavailable; current `vercel build --yes` with Preview
      settings succeeds. Added BFF fallback so Vercel runtime defaults to
      same-origin `/api` when `BACKEND_URL` is unset, while local dev still
      defaults to `http://localhost:8001`. Added proxy-target tests and updated
      README deploy guidance. No external deploy was run.
- [x] **N2 cleanup batch H-2/M-1/M-3** (2026-06-28) — Made
      `AccessTokenBlocklist.is_token_revoked` inclusive at the same-second
      boundary (`iat <= cutoff`) with a regression test; added
      `TokenService.access_ttl_seconds` and updated
      `get_access_token_blocklist` to use it instead of `_access_ttl`;
      made the exactly-120-years-old age-group test leap-year-safe.
      Targeted pytest: `18 passed`; targeted Ruff: all checks passed.
- [x] **Live synthetic-data smoke test** (2026-06-28) — Verified local
      backend `/livez` 200 and `/health` 401, local frontend `/` and
      `/module/report?demo=true` 200, targeted backend/PDF tests
      `4 passed`, browser report flow with synthetic `/backend-api/*`
      mocks through generated report preview, and Vercel public `/`,
      `/api/livez`, `/api/health` behavior. No real Groq chat/generate
      or patient data used.
- [x] **Project reality check** (2026-06-26) — Audited repo/docs/state against
      the real problem and current implementation. Added `PROJECT_REALITY.md`.
      Recommendation: `validate` before more implementation; strongest risk is
      compliance/product-readiness claim drift, not lack of a working demo.
- [x] **Reality audit follow-up: claim cleanup** (2026-06-26) — With two
      parallel worker agents, synchronized README, landing copy,
      `docs/qa-catalog.md`, `scripts/generate_presentation.py`, and regenerated
      `docs/mvp-presentation.pdf`. Removed false `AIProvider`/`LocalProvider`
      implemented wording, stale README/Landing test counters, and current-state
      "100% DSGVO"/practice-ready overclaims.
- [x] **Local project startup** (2026-06-12) — Started backend on `127.0.0.1:8001` using a local SQLite override to avoid external Neon side effects, and frontend on `127.0.0.1:3001` because `3000` was occupied by another Next.js app. Repaired the local Next SWC package by reinstalling `@next/swc-darwin-arm64@16.2.1` in `frontend/node_modules`.
- [x] **MVP Presentation PDF & Q&A Catalog** (2026-06-08) — Generated a 10-slide PowerPoint-style presentation PDF at `docs/mvp-presentation.pdf` (compiled via a custom ReportLab script `scripts/generate_presentation.py` and verified as exactly 10 pages) and created a comprehensive German Q&A catalog at `docs/qa-catalog.md` covering tech stack, AI pipeline, security, and GDPR compliance.
- [x] **O-wave** (2026-06-03) — Vercel production fix + CI green-up:
      SESSION_ENCRYPTION_KEY added to `_set_env` autouse fixture (`1c19ff2`);
      mypy 0010/0011 errors fixed (`95a71fb`);
      TRUSTED_PROXY + RATE_LIMIT_REDIS_URL + SERVICE_TOKEN + JWT_SECRET +
      SESSION_ENCRYPTION_KEY + PATIENT_ENCRYPTION_KEY added to Vercel production;
      `EmailStr` replaced with local `Annotated[str, AfterValidator]` to remove
      `email-validator` Vercel vendoring issue (`5298d30`).
      Vercel production: livez 200, health 401, frontend 200. — 2026-06-03

- [x] **N-wave** (post-M-wave hygiene + review + test coverage uplift) — three parallel sub-agents:
      N1 login_2fa compound-assert split + full service-layer sweep (only that 1 match existed outside owner-WIP) (`c941910`);
      N2 independent M-wave review (caught H-1 bare-except scope, H-2 same-second iat edge, M-1 private attr access, M-3 leap-year test edge — all logged as follow-ups in HANDOFF.md);
      N3 +9 P2-tier service tests (email/password/challenge_store/report_comparator contract pinning) (`11540a4`).
      Plus inline H-1 attempted-narrow-then-revert: kept `except Exception` (test env needs broad catch for `redis.exceptions.ConnectionError`), elevated log WARNING → ERROR for production monitoring (`fd46f35`).
      **533 passed, 9 skipped** (was 522+9; +11 net). — 2026-06-02
- [x] **M-wave** (L3-review + L-wave-deferred closure) — three parallel sub-agents, all auto-merged clean:
      M1 S-7 access-token revocation via per-user Redis `revoked_until` cutoff comparing JWT `iat` — new `services/access_token_blocklist.py`, middleware lazy-import, fail-open on Redis error, +10 tests (`7636d9f`);
      M2 L-1 fixture consolidation (3 tests onto `deps_with_2fa`) + L-2 bare-assert → `if/raise RuntimeError` on `start_2fa_setup`/`enable_2fa`/`disable_2fa` matching J1 style (`0c1f9b0`);
      M3 derive_age_group `[0, 120]` years clinical guard + 2 boundary tests + `_audit` docstring (M-1) + `rate_limit_exceeded_handler` comment (M-2 Retry-After semantic) (`c4890f0`).
      **522 passed, 9 skipped** (was 510+9). The complete I1+I2+I3 audit cycle from 2026-06-01 is now closed end-to-end. — 2026-06-02
- [x] **L-wave** (post-K-wave deferred closure attempt — partial). Three parallel agents dispatched; two hit Anthropic socket-close errors mid-run.
      L1 (S-7 access-token revocation) discarded — only stubbed service file, no commit.
      L2 (disable_2fa P-3 + X-RateLimit-* headers) **disable_2fa portion salvaged inline** as `24ce58f` (same bulk `sa.update` pattern as change_password/enable_2fa); `headers_enabled=True` + SlowAPIMiddleware addition **dropped** (broke 85 tests via slowapi's `parameter response must be Response` error — not solvable by middleware-order alone).
      L3 (independent J/K code review) **completed** — caught H-1 (frontend type widening, applied inline as `b39c72b`), H-2 (TRUSTED_PROXY missing from deploy artifacts), and 4 medium/low items now in "Next" below.
      510 passed, 9 skipped (was 508+9; +2 disable_2fa tests). — 2026-06-01
- [x] **K-wave** (post-J-wave deferred closure) — three parallel sub-agents:
      K1 perf trio (P-1 `GET /auth/sessions` pagination + P-3 bulk-update consolidation in `change_password`/`enable_2fa` + P-5 `GET /reports` COUNT opt-in via `include_total`) — `77da09a`;
      K2 security hygiene (S-6 `TRUSTED_PROXY`-gated XFF — **breaking config change**, operator must set `TRUSTED_PROXY` for production XFF trust; 429 `Retry-After` header) — `63ce9e0`;
      K3 +18 service tests (auth_service 2FA paths + patient_service + totp_service error branches) — `1b22548`. **508 passed, 9 skipped** (was 474+9). Inline fixes during integration: K1↔K3 merge conflict in `test_auth_service.py` (kept both sets), K1 test env-var bug (`TOTP_ENCRYPTION_KEY` → `SESSION_ENCRYPTION_KEY`). — 2026-06-01
- [x] **J-wave** (post-H-wave audit follow-ups) — three parallel sub-agents:
      J1 security bundle (S-1 email PII → SHA-256 email_hash; S-3 `/auth/2fa/setup` rate-limit `3/hour` + audit emit `user.2fa_setup_started`; S-4 `_audit` assert→RuntimeError; S-5 `hmac.compare_digest` for service-token bearer) — `869c77f`;
      J2 rate-limits `30/min` on `/auth/logout` + `GET/DELETE /auth/sessions` — `de96f6c`;
      J3 +9 tests for `session_store.save/get_or_raise/get_authorized`, +6 tests for `audit_service.query`, plus latent `_apply_0018` transaction fix from I1 Medium [3] — `102e592`. **474 passed, 9 skipped** (was 448+9). — 2026-06-01
- [x] **I-wave audits** (read-only): I1 H-wave code-review (caught Critical 0017 FK gap, see next item), I2 backend test-coverage audit (`session_store` + `audit_service.query` zero direct refs, etc.), I3 security/perf sweep (S-1 email PII, S-3 unaudited 2FA setup, etc.). Reports inline in chat; key findings captured in CURRENT.md "Key things the next agent should know". — 2026-06-01
- [x] **Critical fix: 0017 missing soaprecord+therapyplanrecord FK drops.** Migration would have failed on first Postgres deploy with "cannot alter type of a column used in a foreign key constraint". Added both to `_FK_SPECS`; `_column_is_varchar` guard correctly skips the redundant ALTER for their already-UUID columns. SQLite was no-op so CI never caught it. Caught by I1 review. (`bf04e8b`) — 2026-06-01
- [x] **Type-encoding cleanup (`VARCHAR(36)` → `UUID`) — 13/13 columns CLOSED.** 0008/0009 handled `reports.patient_id` + `soaprecord.user_id` early; 0013/0014/0015/0016 (E2 + G1/G2/G3) handled the 4 leaf PKs; 0017/0018 (H1/H2) closed the 9-column users.id + patients.id clusters via coordinated drop-FKs / ALTER-types / recreate-FKs pattern. `alembic check` clean end-to-end on the resulting 0001→0018 chain. (`a557a4f` + `b24d6ee` + earlier waves) — 2026-05-31
- [x] **F2** — explicit `@pytest.mark.asyncio` markers on 19 bare `async def test_*` across 3 backend test files (parallel sub-agent F2). Pure hygiene against potential future `asyncio_mode = "strict"` migrations; pytest counts unchanged. `import pytest` added to `test_email_service.py` (only touched file that was missing it) (`b5bca62`) — 2026-05-31
- [x] `0017_users_id_uuid_cluster` + `0018_patients_id_uuid_cluster` VARCHAR(36)→UUID alignment for the 9 columns clustered around `users.id` (7 cols: PK + 6 FKs) and `patients.id` (2 cols: PK + `consent_records.patient_id`) — parallel sub-agents H1/H2. Coordinated drop/ALTER/recreate-FKs pattern. Drift finding worth flagging: 0002 created 3 FKs inline without explicit names; 0017 renames them to canonical `fk_<table>_<col>_users` during recreate. Followup mypy cleanup (`0833506`) replaced `op.Operations.context()` with explicit `from alembic.operations import Operations` (`a557a4f` / `b24d6ee` / `0833506`) — 2026-05-31
- [x] `0014`+`0015`+`0016` VARCHAR(36)→UUID alignment for `email_tokens.id`, `user_sessions.id`, `consent_records.id` (parallel sub-agents G1/G2/G3). All leaf PKs, no incoming FKs; each migration mirrors `0013` pattern. 9 columns from A3's audit remain (all are FKs to `users.id` or `users.id` itself — coordinated cluster) (`facf364` / `559ed9f` / `aadea60`) — 2026-05-31
- [x] F1: T3's audit-logger re-enable scoped via `monkeypatch.setattr` (E3-review follow-up). Was a bare module-level mutation that would have leaked into later tests; now restored at teardown (`16aad7e`) — 2026-05-29
- [x] `0013_audit_log_id_uuid_type` migration (parallel sub-agent E2). Postgres-only conditional `ALTER TABLE audit_log ALTER COLUMN id TYPE uuid USING id::uuid`, SQLite no-op via dialect gate. Proof-of-pattern for the broader `VARCHAR(36)→UUID` cleanup; chose `audit_log.id` as safest first target (no incoming FKs to cascade-break). `test_migration_0013.py` covers SQLite no-op + Postgres-only skip-marker (`0e5d302`) — 2026-05-29
- [x] Ruff version skew + I001 baseline cleared (parallel sub-agent E1). Real root cause was NOT a hook-id circular conflict — it was a version pin skew (`.pre-commit-config.yaml` and `requirements-dev.txt` both pinned ruff 0.11.12, dev CLI was 0.15.10). Bumped both to 0.15.15, renamed deprecated `id: ruff` → `id: ruff-check`. `ruff check .` → All checks passed!. Also fixed 5 SVG trailing-newline issues surfaced by `pre-commit run --all-files` (`e089942`) — 2026-05-29
- [x] Code-review pass on `3d57bc1` (D1) + `44ff83b` (D2) by parallel sub-agent E3. No Critical, one High (F1, applied), two Medium (F2 deferred, M2 informational), four Lows (all confirmations that D2 is correct). Approval: both safe to keep as landed. Risk: Low (report inline in chat) — 2026-05-29
- [x] M4: `AuthService.refresh` happy path now emits `event="user.token_refreshed"` audit row (parallel sub-agent D2). Metadata: `{"old_session_id": ..., "new_session_id": ...}`. Route was already wired with `background_tasks` + `db_factory` from B1; only the svc-side emit was missing (`44ff83b`) — 2026-05-29
- [x] T1 + T2 + T3 end-to-end tests for the BackgroundTasks audit path (parallel sub-agent D1): T1 drives `log_in_background` directly + asserts fresh-session landing; T2 hits admin lock route + asserts row via `GET /admin/audit`; T3 monkeypatches `Session.commit` to raise + asserts the worker swallows + `logger.exception` is called. T3 verified by removing the `except` clause and watching it fail (`3d57bc1`) — 2026-05-29
- [x] Code-review hardening on `6c18482` (parallel sub-agent C3 + M2 follow-up): `AuthService._audit` now asserts `(background is None) == (db_factory is None)` so partial wiring fails loud instead of silently degrading to the sync path (`222c708`) — 2026-05-29
- [x] `ix_patients_pseudonym` drift resolution (parallel sub-agent C2): dropped the `index=True` declaration from `Patient.pseudonym` (call-site audit showed only `ILIKE '%q%'` searches always co-anded with `user_id`/`deleted_at`; `idx_patients_user_active` from 0011 covers the access path); removed the entry from `_MIGRATION_ONLY_INDEXES` so `alembic check` now actively guards against re-introducing it (`90c51e3`) — 2026-05-29
- [x] BackgroundTasks audit-wiring audit (parallel sub-agent C1): grep confirmed every audit emit site in the codebase was already converted in `6c18482` — `reports.py`, `sessions.py`, `soap.py`, etc. don't emit audit events. No code change required; HANDOFF's anticipation of "remaining routers" was incorrect. (No commit.) — 2026-05-29
- [x] `test_no_api_key_references` exclusion fix (parallel sub-agent B3): switched from absolute `path.parts` to `relative_to(root).parts`; added `.claude` + `worktrees` to the exclusion set so agent-worktree dispatch no longer false-fails the suite (`33c542e`) — 2026-05-29
- [x] `0012_align_declared_fks` migration + `alembic check` CI guard (parallel sub-agent B2): emits 7 declared-but-missing FKs idempotently (no-op on Neon for therapyplanrecord), tunes `alembic/env.py` (add `models.patient` import, `compare_type=False`, `include_object` filter), CI step runs after pytest (`6e31983`) — 2026-05-29
- [x] `audit_service.log()` writes deferred via FastAPI BackgroundTasks (parallel sub-agent B1): new `log_in_background` + `get_db_factory` plumbing in `database.py`; sync `log()` preserved for test direct-callers; routes in auth/auth_admin/patients wire the deferred path (`6c18482`) — 2026-05-29
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
