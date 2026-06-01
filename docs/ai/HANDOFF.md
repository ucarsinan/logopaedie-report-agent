# HANDOFF.md — Agent-to-Agent Handoff

> **This file enables any agent to continue work without chat history.**
> It must be updated at the end of every meaningful AI session.
> The rule: if the next agent cannot understand the situation from this file alone, the handoff is incomplete.

---

## Last Updated

- **Date:** 2026-06-01 (mid-morning — K-wave)
- **Updated by:** Claude Code
- **Handoff to:** next agent. K-wave (3 parallel agents) closed the
  remaining I3-deferred + I2-deferred items: K1 perf trio (P-1
  sessions pagination + P-3 bulk-update consolidation in
  change_password/enable_2fa + P-5 reports COUNT opt-in), K2 security
  hygiene (`TRUSTED_PROXY` strict XFF gate + 429 `Retry-After`
  header), K3 +18 service tests (2FA happy paths + patient_service
  + totp_service error branches). One merge conflict
  (test_auth_service.py K1↔K3) and one K1 test bug
  (`TOTP_ENCRYPTION_KEY` → `SESSION_ENCRYPTION_KEY`) resolved
  inline. **Breaking config change for production**: `TRUSTED_PROXY`
  must now be set explicitly or XFF is ignored — Vercel deploys
  need operator attention. Outstanding (all low/informational): S-7
  access-token revoke on password change, S-8 `get_optional_user`
  state checks, redundant `ix_*_user_id` index drop (Neon EXPLAIN),
  M-6 anamnesis (owner-WIP), Vercel preview (out of scope).

---

## Session Summary

**Agent:** Claude Code
**Date:** 2026-06-01 (mid-morning — K-wave)
**Role(s):** Coordinator + Implementer + Conflict-Resolver + Scribe
(three parallel sub-agents K1/K2/K3 + inline merge-conflict resolution
+ K1 test-bug fix)

### What was done

#### Phase 1 — K-wave (3 parallel agents, all from worktree-forks of `8a00903`)

- **K1** (perf bundle, `77da09a`):
  - **P-1**: `GET /auth/sessions` now accepts `limit` (Pydantic v2
    `Query(50, ge=1, le=200)`) and `offset` (`Query(0, ge=0)`).
    Previously unbounded; default cap is 50.
  - **P-3**: `AuthService.change_password` and `enable_2fa` replaced
    the `for s in db.exec(...).all(): s.revoked_at = ...; db.add(s)`
    loop with a single `sa.update(UserSession).where(...).values(...)`
    wrapped in the existing `_atomic()` helper. Matches
    `AuthService.refresh()` style.
  - **P-5**: `GET /reports` now has `include_total: bool = True`
    query param. Default behavior unchanged (returns `total: int`);
    `include_total=false` skips the COUNT subquery and returns
    `total: None`. Strategy (a) per the brief — smaller blast
    radius than cursor pagination.
  - +12 tests (5 P-1 in `test_auth_routes.py`, 4 P-3 in
    `test_auth_service.py`, 3 P-5 in `test_reports_extra.py`).
  - Side note from K1: `disable_2fa` has the same per-row loop
    pattern as `change_password`/`enable_2fa`. Not in K1's scope;
    follow-up opportunity for pattern consistency.
- **K2** (security hygiene, `63ce9e0`):
  - **S-6**: `client_ip_key` in `middleware/rate_limiter.py` no
    longer gates XFF trust on `_is_production()`. Trust is now
    bound to `TRUSTED_PROXY` env var being set AND matching the
    inbound socket IP. Preview deploys and non-Vercel staging are
    safe by default; enabling XFF requires deliberate config.
  - **429 `Retry-After` header**: `RateLimitExceeded` handler in
    `main.py` now includes `Retry-After` computed from
    `exc.limit.limit.get_expiry()` (slowapi 0.1.9 doesn't expose
    `retry_after` directly), wrapped in `contextlib.suppress` with
    a 60s fallback so header building can never turn a 429 into a
    500.
  - +4 tests (3 XFF gate variants + 1 Retry-After).
  - Updated `conftest.py` to pin `TRUSTED_PROXY="testclient"` so
    the existing `unique_ip_headers` fixture keeps isolating
    buckets per test under the new semantics.
  - Updated existing `test_client_key_uses_first_forwarded_ip` to
    set `TRUSTED_PROXY` (its old assumption "XFF always trusted in
    tests" no longer holds).
  - Optional `X-RateLimit-*` headers NOT added — slowapi has the
    plumbing (`headers_enabled=True`) but the project's
    `_build_limiter` doesn't enable it.
  - **Production-config caveat surfaced**: `TRUSTED_PROXY` is now a
    stronger contract (string compare to socket IP, not just "any
    truthy value"). Vercel edge IPs rotate, so operators must
    either set `TRUSTED_PROXY` to a known reverse-proxy IP if one
    exists in front of the function, or accept the more
    conservative per-instance bucketing. Worth a deploy-env audit.
- **K3** (test coverage uplift, `1b22548`):
  - +6 tests for `auth_service` 2FA service paths
    (`start_2fa_setup` shape, deferred-audit wiring, `disable_2fa`
    invalid/happy, `login_2fa` replay + stale challenge — direct
    service-unit, complementing the route-level coverage already
    in `test_2fa_routes.py`).
  - +7 tests for `patient_service` error branches (duplicate
    `system_id` collision + retry; ownership contract on
    `update_patient`; soft-delete read on the router helper;
    `derive_age_group` edges).
  - +5 tests for `totp_service` error branches (tampered
    ciphertext, drift-window boundary, shape rejection, matched
    step within window, special-char provisioning URI).
  - **Contract findings worth knowing**: `update_patient` doesn't
    enforce ownership at the service level (router does);
    `derive_age_group` doesn't validate DOB ranges (future dates
    silently become "kind"); `login_2fa` replay/expiry already
    had route-level coverage so K3 added service-level.

#### Phase 2 — Integration (inline)

- **Merge conflict in `test_auth_service.py`**: K1 (P-3 sibling-revoke
  tests) and K3 (2FA service-unit tests) both wanted to append to
  the same file. Resolved by keeping BOTH sections; the file now
  has K3's "I2 deferred: 2FA service-unit tests" block followed by
  K1's "P-3: bulk-update consolidation" block.
- **K1 test bug fix**: K1's two P-3 enable_2fa tests called
  `monkeypatch.setenv("TOTP_ENCRYPTION_KEY", ...)` but
  `services/totp_service.py:18` reads `SESSION_ENCRYPTION_KEY`.
  Tests failed at integration time with `RuntimeError:
  SESSION_ENCRYPTION_KEY env var is required`. Fixed both occurrences
  inline before K1's commit landed.

### Files changed

#### `1b22548` — K3 test coverage uplift

- `backend/tests/test_auth_service.py` — +6 tests, new
  `deps_with_2fa` fixture.
- `backend/tests/test_patient_service.py` — +7 tests.
- `backend/tests/test_totp_service.py` — +5 tests.

#### `77da09a` — K1 perf bundle

- `backend/routers/auth.py` — `list_sessions` limit/offset.
- `backend/services/auth_service.py` — bulk `sa.update` in
  `change_password` + `enable_2fa`.
- `backend/routers/reports.py` — `include_total` opt-in.
- `backend/tests/test_auth_routes.py` — +5 P-1 tests.
- `backend/tests/test_auth_service.py` — +4 P-3 tests (env var
  fixed inline during integration).
- `backend/tests/test_reports_extra.py` — +3 P-5 tests.

#### `63ce9e0` — K2 security hygiene

- `backend/middleware/rate_limiter.py` — `client_ip_key` polarity
  flip, gated on `TRUSTED_PROXY` not `_is_production()`.
- `backend/main.py` — `Retry-After` on 429 handler.
- `backend/tests/conftest.py` — pin `TRUSTED_PROXY="testclient"`.
- `backend/tests/test_rate_limiter.py` (or equivalent) — +3 XFF tests
  + 1 Retry-After test, updated 1 existing test.

### What is NOT done yet

- **I3 S-7** (informational) — access-token revocation on password
  change. Needs a `jti`/`session_hash` Redis blocklist with
  TTL == access_token TTL. Owner-decision (was marked
  informational).
- **I3 S-8** (informational) — `get_optional_user` doesn't check
  `locked_until`/`email_verified`/`revoked_at`. Documented trade-off
  from `c0980ab`; safe while every handler reads only `user.id`.
- **Drop redundant single-column `ix_*_user_id` indexes** — needs
  live Neon EXPLAIN. Not agent-safe.
- **`disable_2fa` bulk-update consolidation** — K1 noted this has
  the same per-row loop pattern as the two methods it fixed. Small
  follow-up.
- **Optional `X-RateLimit-*` headers** — slowapi plumbing exists,
  not enabled. K2 left it out per "minimal scope".
- **TRUSTED_PROXY deploy-env audit** — see Risks below.
- **Vercel preview deploy** — pre-existing failure, out of scope.
- **M-6** — anamnesis completion logic. Blocked on owner-WIP.

### Risks / Attention

- **Production XFF / rate-limit collapse risk**: with `TRUSTED_PROXY`
  unset (the new safe default), `client_ip_key` falls back to the
  socket IP, which on Vercel is the edge proxy IP. All traffic from
  Vercel will bucket under that single IP, collapsing per-IP rate
  limits into a global limit. To restore per-user-IP rate limiting,
  the operator must set `TRUSTED_PROXY` to the proxy IP that Vercel
  routes through to the function (if any deterministic IP exists).
  Vercel's documented edge IPs rotate, so this may require a
  redesign of the rate-limit strategy (e.g., bucket by user_id for
  authenticated routes, by socket IP for unauthenticated).
- **`include_total` API contract**: the response `total` field on
  `GET /reports` is now typed `int | None` rather than `int`.
  Default callers (no query param) keep `total: int`, but the
  TypeScript types in the frontend may need a one-line relaxation
  if/when the frontend adopts the opt-in path.
- **`update_patient` ownership at service level**: K3 surfaced
  that the service does NOT enforce ownership — the router does
  via `_get_active_or_404`. Any direct service call (background
  job, internal tooling) bypasses authorization. Worth a comment
  in the service docstring; not strictly broken.

### Next concrete action

Push the K-wave + this docs commit. Then triage S-7 (access-token
revocation — meaningful security improvement, ~half-day) vs.
`disable_2fa` bulk-update consolidation (15 minutes) vs. owner-WIP
clearance for M-6.

### Ideal next prompt

> Check `docs/ai/CURRENT.md` and `TASKS.md`. The post-H-wave audit
> cycle is fully closed except S-7 (informational). Decide between
> (a) implementing S-7 access-token revocation via a Redis blocklist,
> (b) the small `disable_2fa` bulk-update follow-up, or (c) auditing
> the production XFF / rate-limit posture surfaced by K2.

---

## Session Summary

**Agent:** Claude Code
**Date:** 2026-06-01 (morning — I/J-wave + H-wave Critical follow-up)
**Role(s):** Coordinator + Reviewer + Implementer + Scribe (three read-only
audit agents I1/I2/I3 + one critical-fix inline + three parallel
implementation agents J1/J2/J3)

### What was done

#### Phase 1 — Read-only audits (I-wave, three parallel agents)

- **I1** (code-review agent): independent review of the H-wave
  (commits `b5bca62` + `a557a4f` + `b24d6ee` + `0833506`). Verdict:
  **one Critical issue** — `0017_users_id_uuid_cluster` was missing
  `soaprecord.user_id` and `therapyplanrecord.user_id` from its
  `_FK_SPECS`. Both FKs reference `users.id` (CASCADE), formalized
  by 0012. Their `user_id` columns are already UUID (per 0009/0010),
  but Postgres still refuses to `ALTER TYPE` on a referenced PK while
  any dependent FK exists — same rule that drove H2's design call on
  `fk_reports_patient_id_patients`. SQLite is no-op so CI passed; first
  Postgres deploy would have raised "cannot alter type of a column
  used in a foreign key constraint". Also found two Medium (0017
  downgrade naming acceptable per grep; `_apply_0018` test harness
  using `eng.connect()` without a transaction) and two Lows (hardcoded
  `skipif(True)` class-wide pattern; F2 markers verified clean).
- **I2** (test-coverage audit): scanned `backend/services/` for
  modules with thin or missing unit coverage. Critical gaps:
  `session_store.save/get_or_raise/get_authorized` — ZERO direct
  references in any test file; `audit_service.query` — same; and
  `auth_service.start_2fa_setup` + `disable_2fa` — ZERO references
  even in route tests. P1 picks: `token_service`, `totp_service`
  (no `raises` tests), `patient_service`, `demo_quota` (no Redis-fail
  test). Report only — no code written.
- **I3** (security + performance sweep): audited backend diffs since
  `5af7c4a`. **High S-1**: email PII in `audit_log.metadata_json`
  across 3 register/reset/resend emit sites — GDPR-relevant since
  `/admin/audit` exposes the table unredacted. Medium: S-2 (3 unrated
  auth routes), S-3 (`/auth/2fa/setup` no rate limit + no audit
  emit — silent secret rotation possible under stolen access token),
  S-4 (`AuthService._audit` invariant `assert` strippable under
  `python -O`), S-6 (XFF trust in preview deploys outside the
  `_is_production()` gate). Low: S-5 (service-token bearer compare
  not constant-time), S-7 (access tokens not invalidated on
  password change), S-8 (`get_optional_user` doesn't check
  `locked_until`/`email_verified`/`revoked_at` — documented trade-off
  from `c0980ab`). Perf: P-1/P-3/P-5 list-route pagination & bulk
  update opportunities.

#### Phase 2 — Critical hotfix (inline)

- **0017 FK-graph fix** (`bf04e8b`): added `soaprecord` and
  `therapyplanrecord` entries to `_FK_SPECS` in
  `backend/alembic/versions/0017_users_id_uuid_cluster.py`. The
  `_column_is_varchar` guard in step 2 correctly skips the redundant
  ALTER TYPE for the already-UUID FK columns; step 1 (drop) and
  step 3 (recreate) now cover the full FK graph so the `users.id` PK
  swap goes through on Postgres. Pushed to `origin/main`
  immediately.

#### Phase 3 — Implementation wave (J-wave, three parallel agents)

- **J1** (security bundle, `869c77f`):
  - S-1: replaced raw email in audit metadata with `email_hash`
    (SHA-256 of lowercased email, first 32 hex chars) across the 3
    emit sites in `auth_service.py`. New helper `_hash_email()`.
  - S-3: `POST /auth/2fa/setup` now has `@limiter.limit("3/hour")`
    and emits `event="user.2fa_setup_started"` audit row.
    `start_2fa_setup` signature gained keyword-only
    `ip/ua/background/db_factory` args (all defaulting to `None`
    so existing callers keep working).
  - S-4: `_audit` invariant `assert` replaced with explicit `if /
    raise RuntimeError(...)`.
  - S-5: `middleware/service_token.py` switched bearer compare to
    `hmac.compare_digest`.
  - 8 new tests across `test_auth_service.py`, `test_2fa_routes.py`,
    `test_service_token_middleware.py`.
- **J2** (rate limits, `de96f6c`):
  - Added `@limiter.limit("30/minute")` to `/auth/logout`,
    `GET /auth/sessions`, `DELETE /auth/sessions/{session_id}`.
    Reordered `Request` to first position on two handlers to match
    file convention.
  - 3 new tests in `test_auth_routes.py` reusing the existing
    `unique_ip_headers` fixture + autouse `_reset_rate_limiter`.
  - Awareness note: custom `RateLimitExceeded` handler in `main.py`
    returns a JSON body with German `"Zu viele Anfragen"` and **no
    `Retry-After` / `X-RateLimit-*` headers** — one-line follow-up
    if clients should back off intelligently.
- **J3** (test gaps + 0018 harness fix, `102e592`):
  - 9 new tests for `session_store` covering `save`, `get_or_raise`,
    `get_authorized` (owner / non-owner / anonymous demo session
    branches). Confirmed Fernet ciphertext at Redis layer.
  - 6 new tests for `audit_service.query` (filter by user / event /
    combined; pagination; ordering; limit clamping). Confirmed
    `audit_service.query` has **no time-range filter** — if needed
    that's a separate service extension.
  - 0018 test `_apply_0018` switched from `eng.connect()` to
    `eng.begin()` so DDL would actually persist on a hypothetical
    Postgres test path.
  - Doc inline correction: `get_authorized` takes `user_id: str |
    None`, not a `user` object (contradicts I2's phrasing).

### Files changed

#### `bf04e8b` — Critical 0017 fix

- `backend/alembic/versions/0017_users_id_uuid_cluster.py` — added
  `soaprecord` and `therapyplanrecord` to `_FK_SPECS` with explanatory
  comment about the `_column_is_varchar` guard handling
  already-UUID columns.

#### `102e592` — J3 test coverage + 0018 fix

- `backend/tests/test_session_store.py` — +9 tests.
- `backend/tests/test_audit_service.py` — +6 tests.
- `backend/tests/test_migration_0018.py` — `_apply_0018` transaction
  fix.

#### `869c77f` — J1 security bundle

- `backend/services/auth_service.py` — `_hash_email` helper, 3 audit
  emits switched from `email` to `email_hash`, `assert → raise` in
  `_audit`, `start_2fa_setup` signature extended + audit emit.
- `backend/routers/auth.py` — 2FA setup route: limiter +
  background_tasks + db_factory wiring (this route only).
- `backend/middleware/service_token.py` — `hmac.compare_digest`.
- `backend/tests/test_auth_service.py` — +5 tests.
- `backend/tests/test_2fa_routes.py` — +2 tests.
- `backend/tests/test_service_token_middleware.py` — +1 test.

#### `de96f6c` — J2 rate limits

- `backend/routers/auth.py` — `@limiter.limit("30/minute")` +
  `Request` position fix on `logout` and `delete_session`.
- `backend/tests/test_auth_routes.py` — +3 tests.

### What is NOT done yet

- **Drop redundant single-column `ix_*_user_id` indexes** — needs
  live Neon EXPLAIN. Not agent-safe.
- **I3 deferred:** S-6 (preview-env XFF trust audit), S-7 (access
  token revocation on password change), S-8 (`get_optional_user`
  lock/verify checks — informational), P-1 (sessions pagination),
  P-3 (bulk-update consolidation in change_password / enable_2fa),
  P-5 (reports list COUNT optimization).
- **I2 deferred:** more direct service unit tests for `auth_service`
  2FA methods (J1 added audit-emit + rate-limit assertions but
  not the full happy-path unit suite); `patient_service` +
  `totp_service` `raises=0` error-path gap.
- **Rate-limit 429 headers** — bare JSON, no `Retry-After`.
- **Vercel preview deploy** — pre-existing failure, out of scope.
- **M-6** — anamnesis completion logic. Blocked on owner-WIP.

### Risks / Attention

- The `_audit` change from `AssertionError` → `RuntimeError` is the
  only "wider blast radius" change in J1: any test or external tool
  that catches the specific `AssertionError` for the partial-wiring
  invariant will need updating. Grep confirmed no test does — but
  worth a final check if a future agent reports a confusing pytest
  failure here.
- The email PII change broke `metadata_json["email"]` for the 3
  affected event types. External alerting / dashboards keyed on
  raw email will silently fail to match. Switch them to
  `metadata_json["email_hash"]` (SHA-256 lowercase, first 32 hex).
- 0017 + 0018 still have only SQLite no-op coverage on the
  Postgres-specific paths. The Critical bug in 0017 (caught by I1)
  proves this pattern can hide real defects. **A Postgres
  testcontainer in CI is the structural fix and should be on the
  roadmap.**

### Next concrete action

Push the J-wave + this docs commit. Then either pick up an I3 deferred
item (S-6 preview-XFF audit is the highest-value next security item),
or wait for the owner-WIP block to clear so M-6 becomes actionable.

### Ideal next prompt

> Check `docs/ai/CURRENT.md` and `TASKS.md`. The post-H-wave audit
> cycle is closed. Decide between (a) picking up I3 deferred items
> (S-6/S-7 or P-1/P-3/P-5), (b) adding more direct service-unit
> tests for `auth_service.start_2fa_setup`/`disable_2fa` per I2,
> or (c) waiting for the M-6 owner-WIP block to clear.

---

## Session Summary

**Agent:** Claude Code
**Date:** 2026-05-31 (evening — H-wave)
**Role(s):** Coordinator + Implementer + Scribe (three parallel sub-agents H1/H2/F2)

### What was done

- **H1**: landed `0017_users_id_uuid_cluster` migration (`a557a4f`).
  Coordinated drop/ALTER/recreate of the `users.id` reference cluster:
  PK + 6 declared FKs from `user_sessions.user_id`,
  `email_tokens.user_id`, `audit_log.user_id`, `patients.user_id`,
  `reports.user_id`, `consent_records.recorded_by`. Postgres-only via
  dialect gate; SQLite no-op (GUID TypeDecorator already stores
  CHAR(36)). FK names discovered via `inspector.get_foreign_keys()` to
  stay idempotent against environments where 0002 left
  server-default names. New finding worth recording in the audit:
  **0002 creates 3 FKs inline at table-creation without explicit
  names** — Postgres gives them `*_fkey` defaults. 0017 renames them
  to the canonical `fk_<table>_<col>_users` convention during the
  recreate; nothing in the codebase pins on the old names (grep
  confirmed).
- **H2**: landed `0018_patients_id_uuid_cluster` migration
  (`b24d6ee`). PK + `consent_records.patient_id`. **Design call worth
  flagging**: `reports.patient_id` was already UUID (0008), but
  Postgres refuses to `ALTER TYPE` a referenced PK column while ANY
  dependent FK exists — even when the referencing type already
  matches. 0018 therefore drops + recreates
  `fk_reports_patient_id_patients` so the PK swap can go through. The
  recreate uses the canonical name and `ON DELETE SET NULL` from 0012.
  This was not empirically tested on Postgres (test path skipped
  pending Postgres CI) — verify on first live deploy of 0018.
- **F2**: added explicit `@pytest.mark.asyncio` markers to 19 bare
  `async def test_*` functions across 3 files (`test_audit_service.py`
  1, `test_email_service.py` 3, `test_auth_service.py` 15). Added
  `import pytest` to `test_email_service.py` (the only touched file
  missing it). Pure hygiene against potential future
  `asyncio_mode = strict` migrations. No semantic change.
  Landed as `b5bca62`.
- **Mypy follow-up** (`0833506`): H2's sandboxed-versions test fixture
  used `op.Operations.context(ctx)` against the alembic.op proxy
  module; mypy couldn't statically resolve the attribute. Replaced
  with `from alembic.operations import Operations` + plain
  `Operations.context(ctx)`. One-line cleanup.
- Worktree-coordination note for future H-style waves: H2's worktree
  was forked before 0017 existed, so the test for 0018 had to use a
  sandboxed `versions/` copy (0001..0016 minus 0018) to walk the
  alembic chain without choking on the missing 0017. The sandbox is
  now functionally unnecessary (0017 is in main) but harmless; left
  in place because rewriting the test to use the real `versions/`
  dir would be a separate cleanup PR with no behavior change.
- Verified before push: `ruff check .` → All checks passed. `mypy`
  → 0 errors on H-wave files (3 pre-existing in 0010/0011 unchanged).
  `DATABASE_URL=sqlite:///./ci_check.db alembic upgrade head` →
  0001→0018 clean. `alembic check` → "No new upgrade operations
  detected". `alembic downgrade base` → full chain reverses cleanly.
  `pytest -q` → **448 passed, 9 skipped** (was 440+4 after G-wave;
  +8 SQLite passes + +5 Postgres skip-markers from H1/H2's new tests;
  F2 is semantically a no-op).

### Files changed

#### `b5bca62` — F2 asyncio markers

- `backend/tests/test_audit_service.py` — +1 `@pytest.mark.asyncio`
  on T1 (`test_log_in_background_persists_via_fresh_session`).
- `backend/tests/test_email_service.py` — +3 markers; added
  `import pytest`.
- `backend/tests/test_auth_service.py` — +15 markers across the
  register/verify/login/refresh/password suite.

#### `a557a4f` — 0017 users.id cluster

- `backend/alembic/versions/0017_users_id_uuid_cluster.py` (new) —
  drop 6 FKs (3 server-default-named from 0002, 3 canonical from
  0012), ALTER 7 columns to UUID, recreate 6 FKs with canonical names.
- `backend/tests/test_migration_0017.py` (new) — SQLite no-op pass +
  2 Postgres-skipped assertions.

#### `b24d6ee` — 0018 patients.id cluster

- `backend/alembic/versions/0018_patients_id_uuid_cluster.py` (new) —
  drop `fk_consent_records_patient_id_patients` and
  `fk_reports_patient_id_patients`, ALTER `patients.id` +
  `consent_records.patient_id` to UUID, recreate both FKs.
- `backend/tests/test_migration_0018.py` (new) — SQLite no-op pass +
  Postgres-skipped FK/type assertions. Uses sandboxed `versions/`
  copy fixture (now functionally unnecessary but harmless).

#### `0833506` — mypy: Operations import in 0018 test

- `backend/tests/test_migration_0018.py` — `from alembic import op`
  → `from alembic.operations import Operations`; one usage updated.

### What is NOT done yet

- **Drop redundant single-column `ix_*_user_id` indexes** (audit
  2026-05-29 performance). Needs live Neon EXPLAIN to confirm the
  composite indexes from 0011 are picked. Not agent-safe; owner
  decision.
- **Vercel preview deploy** — pre-existing failure, separate
  config issue, out of scope for CI green-up.
- **M-6** — anamnesis completion logic. Blocked on owner-WIP.

### Risks / Attention

- 0017 renames 3 server-default FK names on Postgres (`*_fkey` →
  `fk_<table>_<col>_users`). Grep confirmed no code pins on the old
  names; if a future agent introduces tooling that hardcodes FK names
  by reading from `pg_constraint`, those will surface here first.
- 0018's `fk_reports_patient_id_patients` drop/recreate logic is a
  documented design choice without an end-to-end Postgres test —
  see CURRENT.md "Key things the next agent should know" §2.

### Next concrete action

Push the H-wave + docs commit. Then either pick up the redundant-index
work (with the owner's blessing once they have EXPLAIN output) or wait
for the owner-WIP block to clear so M-6 becomes actionable.

### Ideal next prompt

> Check `docs/ai/CURRENT.md` and `TASKS.md`. The VARCHAR(36)→UUID
> drift class is fully closed across the 13-column audit. Decide
> between (a) helping the owner unblock M-6 once they hand over the
> anamnesis WIP, or (b) preparing the redundant `ix_*_user_id` drop
> migration after EXPLAIN evidence is in.

---

## Session Summary

**Agent:** Claude Code
**Date:** 2026-05-29 (early morning, fifth wave)
**Role(s):** Coordinator + Implementer + Scribe (three parallel sub-agents E1/E2/E3 + F1 inline)

### What was done

- Fifth parallel-agent wave dispatched in worktree isolation against
  the open follow-ups left after the D-wave:
  - **E1**: clear the 4-error `ruff I001` baseline. Discovery was
    the actual story: it wasn't a hook-id circular conflict at all,
    it was a **ruff version pin skew**. `.pre-commit-config.yaml` and
    `backend/requirements-dev.txt` both pinned `ruff 0.11.12`; the
    dev CLI ran 0.15.10. The newer ruff's isort splits
    `from alembic.config import Config` into the third-party block,
    something 0.11.12 didn't flag. Bumped both pins to `0.15.15`,
    renamed deprecated `id: ruff` → `id: ruff-check`, ran
    `ruff check --fix` on the 4 affected test files. `ruff check .`
    now reports "All checks passed!". `pre-commit run --all-files`
    also auto-fixed missing trailing newlines on 5
    `frontend/public/*.svg` files (pre-existing baseline, included
    in the same commit). Landed as **`e089942`**.
  - **E2**: land `0013_audit_log_id_uuid_type` migration — the first
    `VARCHAR(36) → UUID` type alignment from A3's audit. Mirrors
    `0008`/`0009`: dialect-gated Postgres-only `ALTER TABLE audit_log
    ALTER COLUMN id TYPE uuid USING id::uuid`. SQLite is a no-op
    (GUID TypeDecorator already stores as CHAR(36)). Chose
    `audit_log.id` as the safest first target because no other table
    has an FK pointing at it. `test_migration_0013.py` covers
    SQLite no-op + Postgres-only skip-marker. Convention note: agent
    used the short `revision = "0013"` form matching `0001..0012`,
    not the long form the brief suggested. Landed as **`0e5d302`**.
  - **E3**: read-only code review of `3d57bc1` (D1) + `44ff83b`
    (D2). Verdict: no Critical, one High (F1 — T3 logger leak),
    two Medium (F2 — `@pytest.mark.asyncio` marker drift,
    M2 — informational), four Lows (all confirmations that D2 is
    correct: emit ordering, `db.refresh(new_sess)` placement,
    UUID str-casting, post-commit timing). Approval: both safe to
    keep as landed. Risk: Low (was Medium after C3; D1/D2 closed
    enough gaps that the audit BG-tasks chain is now well-tested).
  - **F1 (inline applied from E3 review)**: T3's bare
    `audit_logger.disabled = False` + `propagate = True`
    module-level mutation would leak into later tests in the
    session, silently re-enabling a logger alembic intentionally
    disabled. Swapped for `monkeypatch.setattr` so pytest restores
    the originals at teardown. Test already accepts `monkeypatch`,
    so zero new fixture wiring. Landed as **`16aad7e`**.
- Pre-push gotcha surfaced: the hook stashes unstaged changes
  before running pytest, then re-applies them. The framework
  interprets the unstash as "the hook modified files" and aborts
  the push. Workaround: commit unstaged changes before invoking
  `git push`. Recorded for future agents.
- One transient pytest error during pre-push run on
  `test_phonological_validation.py::test_valid_pairs_still_accepted`
  (SQLAlchemy FK e3q8) did NOT reproduce in two subsequent
  full-suite runs locally — classified as flaky test-collection
  ordering, not a regression from this batch. Confirmed: the test
  passes both in isolation (`pytest tests/test_phonological_validation.py
  -v` → 3/3) and in the full suite (`pytest -q` → 430 passed, 1
  skipped).
- Verified before push: **430 passed, 1 skipped** (was 427
  baseline; +3 from E2's new `test_migration_0013` cases, 1 skipped
  for the Postgres-only marker). `ruff check .` → **All checks
  passed!** (baseline 0 ruff errors). `mypy` clean on touched
  files (3 pre-existing errors in `alembic/versions/0010`/`0011`
  remain). `DATABASE_URL=sqlite:///./ci_check.db alembic upgrade
  head && alembic check` → "No new upgrade operations detected"
  (now traverses 0010→0011→0012→0013).

### Files changed

#### `e089942` — ruff 0.15.15 bump + I001 cleared

- `.pre-commit-config.yaml` — `rev: v0.11.12` → `v0.15.15`,
  `id: ruff` → `id: ruff-check`.
- `backend/requirements-dev.txt` — `ruff==0.11.12` → `ruff==0.15.15`.
- `backend/tests/test_alembic_migrations.py`,
  `backend/tests/test_migration_0005.py`,
  `backend/tests/test_migration_0006.py`,
  `backend/tests/test_migration_0012.py` — `ruff check --fix`
  reordered imports.
- `frontend/public/file.svg`, `globe.svg`, `next.svg`,
  `vercel.svg`, `window.svg` — trailing newlines added by
  `pre-commit run --all-files` end-of-file-fixer.

#### `0e5d302` — 0013_audit_log_id_uuid_type

- `backend/alembic/versions/0013_audit_log_id_uuid_type.py` (new)
  — Postgres-only conditional `ALTER COLUMN id TYPE uuid USING
  id::uuid`; downgrade is the reverse.
- `backend/tests/test_migration_0013.py` (new) — SQLite no-op
  pass + 1 Postgres-only test marked `@pytest.mark.skipif`.
- `docs/ai/AUDIT_2026-05-29_schema.md` — annotation under the
  "Type encoding drift" section noting `audit_log.id` is now
  converted as `0013`.

#### `16aad7e` — F1 logger-isolation fix in T3

- `backend/tests/test_audit_service.py` — swap module-level
  `audit_logger.disabled = False` / `propagate = True` for
  `monkeypatch.setattr` so pytest auto-restores at teardown.
  Docstring updated to explain the intent.

### What is NOT done yet

- **12 of the 13 `VARCHAR(36) → UUID` columns are still
  unconverted.** Each requires either independent ALTER (if the
  column has no incoming FKs, like `audit_log.id` was) or
  coordinated drop-FKs / ALTER / recreate-FKs. The largest cluster
  is `users.id` (referenced by ~7 tables); convert those last.
- **`alembic/env.py` `compare_type=False` still globally
  suppresses type drift.** Flipping it to `True` and addressing
  each `_MIGRATION_ONLY_TYPES` filter entry is a separate cleanup
  that follows after all 13 conversions land.
- **F2 — explicit `@pytest.mark.asyncio` on T1.** Low priority;
  config-drift insurance.
- **Drop redundant single-column `ix_*_user_id` indexes** after
  Postgres EXPLAIN. Needs live-Neon EXPLAIN; out of scope for
  agents without Neon access.

### Risks / Attention

- **Pre-push hook false-fails on unstaged changes** (see "Pre-push
  gotcha" above). If a future round commits + pushes immediately
  without committing docs first, the hook will abort. Workflow
  rule for future agents: commit docs BEFORE pushing.
- **`0013_audit_log_id_uuid_type` is Postgres-only on Neon.** On
  upgrade, the column is rewritten — Postgres locks the table
  during ALTER COLUMN TYPE. `audit_log` may be large in
  production. Run during low-traffic window.
- **E2 chose the short revision form** (`"0013"` not the long
  form). Subsequent migrations should follow the same convention
  to keep the chain consistent.
- **Worktree-vs-pre-commit verification gap (carried from D3)**.
  E1 hit and worked around it by running `pre-commit run
  --all-files` in the worktree. Future agents touching hooks /
  config should explicitly include this step.
- Owner WIP files (`anamnesis_engine`, `phonological_analyzer`,
  `anamnesis_catalog`, `test_phonological_analyzer`) — untouched
  by all of E1/E2/E3/F1.

### Next concrete action

Pick from `TASKS.md` "Next" / "Open follow-ups". Highest-value
items:
  (i) Extend the `VARCHAR(36) → UUID` alignment to the next batch
      of safe columns. Candidates with no incoming FKs:
      `email_tokens.id`, `user_sessions.id`, `consent_records.id`.
      Each can be its own migration mirroring `0013` exactly. The
      `users.id` cluster requires coordinated FK drops/recreates
      and should be the last to land.
  (ii) F2: add `@pytest.mark.asyncio` decorator to T1 in
      `test_audit_service.py` for explicit-marker insurance
      against `asyncio_mode = "auto"` config drift. One-line
      change.

Everything else open is LOW-severity.

### Ideal next prompt

```text
Read docs/ai/HANDOFF.md (latest "Session Summary"), then
docs/ai/AUDIT_2026-05-29_schema.md.

Current situation: main is at 16aad7e (after the upcoming docs commit
pushes), 0 ahead of origin/main. E2 landed 0013 as the proof-of-pattern
for the VARCHAR(36) → UUID alignment; 12 columns remain.

Your task: pick the next safe-to-convert column (no incoming FKs from
other tables — candidates are email_tokens.id, user_sessions.id,
consent_records.id) and write 0014_*_id_uuid_type.py mirroring 0013
exactly. Add a corresponding test_migration_0014.py. Verify with
`DATABASE_URL=sqlite:///./ci_check.db alembic upgrade head && alembic
check` plus full pytest. After that, update docs/ai state files BEFORE
pushing (the pre-push hook false-fails on unstaged changes).
```

---

## Previous session — 2026-05-29 (overnight) — D1/D2/D3 batch

**Agent:** Claude Code
**Date:** 2026-05-29 (overnight)
**Role(s):** Coordinator + Implementer + Scribe (three parallel sub-agents D1/D2/D3)

### What was done

- Fourth parallel-agent wave dispatched in worktree isolation against
  the C3-review follow-ups + a small infrastructural cleanup:
  - **D1**: write T1 + T2 + T3 end-to-end tests for the
    BackgroundTasks-deferred audit path. T1 drives
    `audit.log_in_background` directly with a real `BackgroundTasks`
    and a fresh-session factory, asserts no row before `await
    background()`, then asserts the row landed via a third independent
    session — catches a captured-outer-session regression in
    `get_db_factory`. T2 hits `POST /admin/users/{id}/lock` and queries
    `GET /admin/audit?event=admin.user_locked` — TestClient runs BG
    tasks before returning so the row must be visible. T3
    monkeypatches `Session.commit` to raise `OperationalError`, drives
    the queued task manually, asserts no exception escapes the worker,
    `logger.exception` is called with `audit_service.background_log_failed`,
    and `exc_info[0] is OperationalError`. D1 verified T3 by removing
    the `except Exception:` clause temporarily and watching T3 fail.
    Caught a subtle issue: `alembic.ini`'s `fileConfig` sets
    `disable_existing_loggers=True`, which disables
    `services.audit_service` when alembic tests load it earlier in the
    suite — T3 re-enables the logger explicitly before the assertion.
    Landed as **`3d57bc1`**.
  - **D2**: wire an audit row into `AuthService.refresh()` happy path
    (M4 from the C3 review). Event `user.token_refreshed`; metadata
    `{"old_session_id": ..., "new_session_id": ...}` mirroring the
    pattern from `logout`. Useful discovery: the `refresh` route
    handler in `routers/auth.py` was already wired with
    `background_tasks` + `db_factory` from `6c18482`, even though it
    didn't emit then — only the svc-side emit was missing. The M2
    assert (`(background is None) == (db_factory is None)`) confirms
    the route's full wiring. The reuse-detection branch already emits
    `session.refresh_reuse_detected`; left untouched.
    Landed as **`44ff83b`**.
  - **D3**: clear the 4 `ruff I001` baseline errors in the alembic
    migration test files. **Failed** — pre-commit's `ruff (legacy
    alias)` hook auto-fixed D3's sort BACK to the layout the project's
    `ruff check` rejects. This is the exact circular conflict noted in
    `9c27c7e`'s commit message and is reproducible against current
    main. D3's worktree run was misleading because it doesn't go
    through pre-commit. Real fix needs `.pre-commit-config.yaml`
    adjustment (replace the legacy alias with `ruff check --fix` so it
    respects the same config) OR a `pyproject.toml` isort tweak —
    both out of scope for D3's "test-files-only" mandate. No code
    commit; conflict promoted to a TASKS follow-up item.
- Verified before push: backend `python3 -m pytest -q` → **427
  passed** (423 baseline + 3 from D1 + 1 from D2). Ruff baseline stays
  at 4 errors (D3 didn't land). Mypy clean on touched files (3
  pre-existing errors in `alembic/versions/0010`/`0011` remain).
- `DATABASE_URL="sqlite:///./ci_check.db" alembic upgrade head &&
  alembic check` → "No new upgrade operations detected."

### Files changed

#### `3d57bc1` — T1+T2+T3 audit BG-task tests

- `backend/tests/test_audit_service.py` — +150 lines: T1
  (`test_log_in_background_persists_via_fresh_session`) + T3
  (`test_log_in_background_swallows_db_failure_and_logs`), plus the
  alembic-disabled-logger workaround in T3.
- `backend/tests/test_admin_routes.py` — +43 lines: T2
  (`test_admin_lock_writes_audit_row_via_background_task`).

#### `44ff83b` — refresh happy-path audit row (M4)

- `backend/services/auth_service.py` — `refresh()` captures
  `new_sess` as a named local, calls `db.refresh(new_sess)` so the PK
  is populated post-commit, then `self._audit(db, background,
  db_factory, ..., event="user.token_refreshed", metadata={...})`.
- `backend/tests/test_auth_service.py` — new
  `test_refresh_happy_path_emits_audit_row` drives `svc.refresh(...)`
  directly, captures rotated session id pre-call, asserts a single
  new `AuditLog` row with the right user_id / ip / user_agent /
  metadata.

#### D3 (no commit — conflict promoted to follow-up)

- D3's `ruff check --fix` produced a sort the project's `ruff check`
  accepts; pre-commit's `ruff (legacy alias)` reverts it. The 4
  `I001` errors in `tests/test_alembic_migrations.py`,
  `test_migration_0005.py`, `test_migration_0006.py`,
  `test_migration_0012.py` remain. New TASKS item tracks the
  required hook config fix.

### What is NOT done yet

- **The 4-error ruff baseline persists** because pre-commit and `ruff
  check` disagree on `I001`. Real fix needs `.pre-commit-config.yaml`
  edit; tracked in `TASKS.md`.
- **`VARCHAR(36)` → `UUID` type alignment** across 13 legacy-id
  columns. Suppressed via `compare_type=False` in
  `backend/alembic/env.py`. Real fix mirrors 0008/0009 dialect-gated
  pattern; non-trivial because of coordinated FK type changes.
- **Drop redundant single-column `ix_*_user_id` indexes** after
  Postgres EXPLAIN confirms 0011 composites are picked. Needs
  live-Neon EXPLAIN.
- **`alembic check` only runs against SQLite in CI.** For Neon parity
  an occasional manual `DATABASE_URL=$NEON_URL alembic check
  --autogenerate` is still useful — Postgres-specific drift
  (partial indexes, jsonb defaults) is invisible to the SQLite guard.

### Risks / Attention

- **The audit ecosystem is now well-tested** — T1 covers the
  service-direct path, T2 covers the route-through-TestClient path,
  T3 covers DB-failure resilience. Production posture for the audit
  BG-tasks refactor (6c18482) is now Low-risk (was Medium per C3).
- **D3's worktree pattern revealed a verification gap.** Worktree-mode
  agents run `ruff check` directly, not via pre-commit. For any future
  hook-touching cleanup, the agent should run `pre-commit run
  --all-files` to validate, not just direct tool invocations.
- **M4 covers the happy path only.** The reuse-detection branch
  already emits `session.refresh_reuse_detected`. If a future refresh
  failure mode is added (e.g. expired refresh token), confirm an
  audit event is emitted before declaring complete.
- Owner WIP from earlier sessions (`anamnesis_engine` /
  `phonological_analyzer` / `anamnesis_catalog` /
  `test_phonological_analyzer`) — none of D1/D2/D3 touched these files.

### Next concrete action

Pick from `TASKS.md` "Next" or "Open follow-ups". Highest-value items:
  (i) Fix the `.pre-commit-config.yaml` ruff-vs-pre-commit I001
      conflict so the baseline can actually clear. One-file change,
      bounded scope.
  (ii) `VARCHAR(36)` → `UUID` type alignment as a 0013_* migration
       (Postgres-only, mirroring 0008/0009 conditional pattern). The
       FK coordination makes this non-trivial — pick a small subset
       (e.g. just `audit_log.id` + `audit_log.user_id` first) rather
       than all 13 columns at once.

Everything else open is LOW-severity.

### Ideal next prompt

```text
Read docs/ai/HANDOFF.md (latest "Session Summary"), then
docs/ai/TASKS.md "Open follow-ups".

Current situation: main is at 44ff83b (after the upcoming docs commit
pushes), 0 ahead of origin/main. The audit BackgroundTasks refactor
(6c18482) is now end-to-end tested (T1/T2/T3 in 3d57bc1) and the
refresh audit gap (M4) is closed (44ff83b). The 4-error ruff I001
baseline persists because pre-commit and ruff check disagree.

Your task: fix the .pre-commit-config.yaml ruff hook so the 4 I001
errors can be cleared without triggering the circular auto-fix
conflict. Either replace the "ruff (legacy alias)" hook entry with a
modern `ruff check --fix` entry that respects pyproject.toml, OR
adjust pyproject.toml's isort config to satisfy both. Verify by
running pre-commit run --all-files locally before and after, and
confirm ruff check . is clean.

After that, update docs/ai state files.
```

---

## Previous session — 2026-05-29 (late evening) — C1/C2/C3 batch

**Agent:** Claude Code
**Date:** 2026-05-29 (late evening)
**Role(s):** Coordinator + Implementer + Scribe (three parallel sub-agents C1/C2/C3)

### What was done

- Third parallel-agent wave dispatched in worktree isolation against the
  follow-ups surfaced by the evening (B1/B2/B3) batch:
  - **C1**: extend `audit_service.log_in_background` wiring to the
    "remaining routers" called out in the prior handoff. **Null result.**
    A comprehensive grep (`self.audit.log(`, `audit_service.log(`,
    `audit.log(`, `AuditLog(`, `AuditService` injection sites) shows
    every audit-emitting site was already converted in `6c18482`. The
    routers I listed as remaining (`reports.py`, `sessions.py`,
    `soap.py`, `exports.py`, `analysis.py`, `therapy_plans.py`,
    `suggestions.py`, `legacy.py`, `health.py`) have **zero** audit
    references — they never emitted audit events. C1 produced no diff;
    HANDOFF's "next concrete action" had anticipated work that doesn't
    exist.
  - **C2**: resolve the `ix_patients_pseudonym` drift (declared
    `index=True` on the model, never created by any migration, silenced
    via `_MIGRATION_ONLY_INDEXES` since `6e31983`). C2 audited the query
    call sites and chose Path 2 (drop the declaration) over Path 1
    (write `0013_patients_pseudonym_index.py`). Evidence:
    `routers/patients.py:113` searches with `ILIKE '%q%'` (leading
    wildcard, no B-tree can serve — would need `gin_trgm_ops`); the
    query is always co-anded with `user_id` + `deleted_at IS NULL`,
    which `idx_patients_user_active` from `0011` already covers.
    `routers/reports.py:57` only projects `pseudonym` on a JOIN over
    `Patient.id` (PK), never uses it as a WHERE predicate. So
    `index=True` was dead intent. Landed as **`90c51e3`** — drops the
    declaration, removes the entry from
    `_MIGRATION_ONLY_INDEXES`, adds
    `test_patient_pseudonym_has_no_standalone_index` as a regression
    guard, annotates `AUDIT_2026-05-29_schema.md` with the resolution.
  - **C3**: read-only code review of `6c18482` (the B1 BackgroundTasks
    audit refactor whose final summary was lost to a socket error).
    C3 produced a structured review: **no Critical issues**, three
    High (concurrency / session-lifecycle / `dependency_overrides`
    resolution — all judged safe-as-landed), one Medium that I applied
    inline (`M2` — partial-wiring silent fallback), three missing tests
    (T1/T2/T3 — `log_in_background` end-to-end, admin-route audit row
    landing, DB-failure fail-open) and one pre-existing gap (`M4` —
    `AuthService.refresh` happy path has no audit row). Approval status:
    "safe to keep as landed + follow-up needed". Risk: Medium.
- Applied C3's M2 inline as **`222c708`**: `AuthService._audit` now
  `assert (background is None) == (db_factory is None)` so partial
  wiring fails loud instead of silently degrading to the sync commit
  path we just removed.
- Verified before push: backend `python3 -m pytest -q` → **423 passed**
  (422 baseline + 1 new from C2's `test_patient_pseudonym_has_no_standalone_index`).
  `mypy` clean on touched files (3 pre-existing errors in
  `alembic/versions/0010`/`0011` remain). Ruff baseline is now **4
  errors** (was 3) — the 4th is `tests/test_migration_0012.py` which
  matches the existing pattern in
  `test_alembic_migrations.py`/`test_migration_0005.py`/`test_migration_0006.py`
  (not a regression from C2; documented baseline shift after `6e31983`).
- `DATABASE_URL="sqlite:///./ci_check.db" alembic upgrade head &&
  alembic check` → "No new upgrade operations detected." After C2 the
  guard is now actively enforcing the `ix_patients_pseudonym` absence
  (rather than silently filtering it).

### Files changed

#### `90c51e3` — `ix_patients_pseudonym` drift resolution

- `backend/models/patient.py` — `pseudonym: str = Field(index=True)` →
  `pseudonym: str = Field()` with an 8-line comment documenting the
  access-path analysis pointing at `idx_patients_user_active`.
- `backend/alembic/env.py` — removed `"ix_patients_pseudonym"` from
  `_MIGRATION_ONLY_INDEXES`; trimmed the comment that referenced the
  deferred `0013_*`.
- `backend/tests/test_patient_model.py` — new
  `test_patient_pseudonym_has_no_standalone_index` asserts no
  single-column index over `pseudonym` exists in
  `SQLModel.metadata.tables["patients"].indexes`.
- `docs/ai/AUDIT_2026-05-29_schema.md` — "Resolved by model-declaration
  drop (2026-05-29)" annotation under the proposed `0013_*` sketch.

#### `222c708` — partial-wiring assert in `AuthService._audit`

- `backend/services/auth_service.py` — `assert (background is None) ==
  (db_factory is None), …` at the top of `_audit`. Docstring updated to
  call out the loud-failure intent.

#### C1 / C3 (no commits)

- C1 produced no diff (null result). C3 produced a review report
  delivered inline; the actionable findings are tracked in `TASKS.md`
  "From 2026-05-29 evening code review".

### What is NOT done yet

- **T1 / T2 / T3 missing tests** for the BackgroundTasks audit path.
  Tracked in `TASKS.md`. Not blocking, but the C3 review explicitly
  rated this Medium-risk because the design is sound but
  end-to-end-untested.
- **M4 — `AuthService.refresh` happy path has no audit row.**
  Pre-existing omission flagged by C3. Compliance gap if token rotation
  is security-relevant.
- **`VARCHAR(36)` → `UUID` type alignment** (the other suppression in
  `env.py`'s `compare_type=False`) still open. Mirrors 0008/0009 dialect
  pattern. Low severity, cosmetic until autogenerate is on.
- **Drop redundant single-column `ix_*_user_id` indexes** after Postgres
  EXPLAIN confirms 0011 composites are picked. Needs live-Neon EXPLAIN.
- **Ruff baseline is now 4 errors**, all `I001` import-sort in alembic
  migration tests (one new in `test_migration_0012.py` from `6e31983`).
  Auto-fixable via `ruff check --fix`; left as-is because the pattern
  is repo-wide and a holistic ruff cleanup is its own task.

### Risks / Attention

- **C2 changed the contract of `Patient.pseudonym`** — the model used
  to declare an index, now doesn't. Live Neon never had the index
  (drift was passive), so no behavior change in prod. Local dev
  (`create_all`) will stop creating the index on fresh DBs; that
  matches the new declaration. The test regression-guards the
  intent.
- **C2's call-site audit was code-only.** If there's a query path the
  agent missed (e.g. a future search endpoint that does
  `Patient.pseudonym = …` without a `user_id` predicate), the index
  drop would cost. A live Postgres EXPLAIN of the search query was not
  performed.
- **M2's `assert` runs in production** — Python `-O` would strip it,
  but the project does not run with `-O`. If a partial wiring slips
  through review, the production worker will raise `AssertionError`
  instead of silently degrading. That is the intended posture.
- Owner WIP from earlier sessions (`anamnesis_engine` /
  `phonological_analyzer` / `anamnesis_catalog` /
  `test_phonological_analyzer`) — none of C1/C2/C3 touched these files.

### Next concrete action

Pick from `TASKS.md` "Next". The two highest-value remaining items are:
  (i) Write T1/T2/T3 from the C3 review (BackgroundTasks audit end-to-end
      coverage). Bounded, agent-safe, would close the C3 "Medium risk"
      rating.
  (ii) Fix M4 — wire an audit row into `AuthService.refresh` happy path.
       One method change; matches the existing `_audit` pattern.

Everything else open is LOW-severity.

### Ideal next prompt

```text
Read docs/ai/HANDOFF.md (latest "Session Summary"), then
docs/ai/TASKS.md "From 2026-05-29 evening code review".

Current situation: main is at 222c708, 0 ahead of origin/main. The
audit-BackgroundTasks refactor (6c18482) was reviewed by C3 and judged
safe-as-landed with one assert guard now applied (222c708). What
remains from that review is T1/T2/T3 (missing end-to-end tests) and M4
(refresh has no audit row).

Your task: write T1 + T2 + T3 as concrete pytest cases. T1 calls
audit.log_in_background with a real BackgroundTasks(), invokes the
queued task manually, asserts the AuditLog row was inserted in a fresh
session. T2 extends test_admin_routes.py to query GET /admin/audit
after the lock action and confirm the admin.user_locked row landed.
T3 mocks the DB factory to raise on commit and asserts
_persist_with_fresh_session swallows the exception, calls
logger.exception, and does NOT crash the worker.

After that, update docs/ai state files.
```

---

## Previous session — 2026-05-29 (evening) — B1/B2/B3 batch

**Agent:** Claude Code
**Date:** 2026-05-29 (evening)
**Role(s):** Coordinator + Implementer + Scribe (three parallel sub-agents B1/B2/B3)

### What was done

- Dispatched a second wave of three parallel sub-agents in worktree
  isolation against the remaining agent-safe items from `TASKS.md` "Next"
  plus the schema-audit follow-ups produced by A3 earlier this afternoon:
  - **B1**: defer `audit_service.log()` writes to FastAPI `BackgroundTasks`.
    New `audit_service.log_in_background(background, db_factory, …)`
    schedules `_persist_with_fresh_session` after the response is sent;
    new `database.get_db_factory(request)` resolves
    `dependency_overrides[get_db]` at request time and hands back a
    context-manager factory so the background task opens its own session
    against the same engine (including test overrides). `AuthService`
    methods gained optional `(background, db_factory)` kwargs and an
    internal `_audit()` router that picks the deferred path when both are
    provided, else falls back to the sync `log()` (preserved for unit
    tests). Routes in `routers/auth.py`, `routers/auth_admin.py`,
    `routers/patients.py` wire the two new deps. Landed as **`6c18482`**.
  - **B2**: write `backend/alembic/versions/0012_align_declared_fks.py` +
    add the `alembic check` CI guard from A3's audit. The migration emits
    the 7 declared-but-missing FKs (`reports.user_id`,
    `reports.patient_id`, `soaprecord.user_id`, `patients.user_id`,
    `consent_records.patient_id`, `consent_records.recorded_by`,
    `therapyplanrecord.user_id`) idempotently via
    `inspector.get_foreign_keys()` guards — no-op on Neon for the
    hotfixed `therapyplanrecord.user_id`. `backend/alembic/env.py` gained
    a missing `import models.patient`, `compare_type=False` (suppresses
    GUID/VARCHAR reflection noise; type alignment deferred to a future
    0013), and an `include_object` filter excluding the migration-only
    composite indexes from 0011 plus the deferred `ix_patients_pseudonym`.
    `.github/workflows/ci.yml` got a new step that runs
    `alembic upgrade head && alembic check` after pytest, against a
    `sqlite:///./ci_check.db`. New `test_migration_0012.py` covers
    upgrade, idempotency-when-FK-preexists, and downgrade-removes.
    Landed as **`6e31983`**.
  - **B3**: fix `test_no_api_key_references` so worktree dispatch stops
    false-failing the full suite. The latent bug was iterating absolute
    `path.parts` against the exclusion set — any ancestor directory name
    (like `.claude` in the CC worktree path) coincidentally short-circuits
    the scan. Switched to `path.relative_to(root).parts` so exclusions
    only match repo-relative segments; added `.claude` + `worktrees` to
    the set. Landed as **`33c542e`**.
- Verified before push: backend `python3 -m pytest -q` → **422 passed**
  (419 baseline + 3 new from `test_migration_0012`). One ruff regression
  caught during integration (`RUF100` from a `# noqa: BLE001` that B1
  added but the project's ruff config doesn't enable BLE001) — removed in
  the B1 commit before staging. `mypy` clean on touched files (3
  pre-existing errors in `alembic/versions/0010`/`0011` remain).
- Local end-to-end of the new CI step:
  `DATABASE_URL="sqlite:///./ci_check.db" alembic upgrade head && alembic check`
  → "No new upgrade operations detected." The guard is live and passing.

### Files changed

#### `6c18482` — audit logging deferred to BackgroundTasks

- `backend/database.py` — new `get_db_factory` + `DBSessionFactory`
  type alias. Captures the currently-active `get_db` (including test
  overrides) so background tasks can open a fresh `Session` after the
  request-scoped one closes.
- `backend/services/audit_service.py` — new `log_in_background` +
  `_persist_with_fresh_session` (logs on exception, doesn't raise — no
  response left to fail).
- `backend/services/auth_service.py` — new internal `_audit` router; all
  `self.audit.log(…)` call sites rewrapped to take optional `background`
  + `db_factory`.
- `backend/routers/auth.py` — handlers gain `background_tasks:
  BackgroundTasks` + `db_factory: DBSessionFactory = Depends(get_db_factory)`
  and pass them into the svc layer.
- `backend/routers/auth_admin.py`, `backend/routers/patients.py` — same
  wiring pattern at admin / patient-CRUD audit emit sites.

#### `6e31983` — `0012_align_declared_fks` + alembic check CI guard

- `backend/alembic/versions/0012_align_declared_fks.py` (new) — 7
  conditional `create_foreign_key` calls + matching `downgrade`.
- `backend/alembic/env.py` — `import models.patient`, `compare_type=False`,
  `include_object` filter (with `_MIGRATION_ONLY_INDEXES` set listing each
  excluded index name and pointing at this audit).
- `backend/tests/test_migration_0012.py` (new) — 3 cases: all FKs land
  on a fresh upgrade, idempotent re-run leaves the FK set identical,
  downgrade removes only what 0012 added.
- `.github/workflows/ci.yml` — new step `Verify alembic migrations match
  SQLModel metadata` in the `backend-test` job (after pytest), uses
  `DATABASE_URL: sqlite:///./ci_check.db`.
- `docs/ai/AUDIT_2026-05-29_schema.md` — one-line "Applied as
  `0012_align_declared_fks.py`" annotation under the migration sketch.

#### `33c542e` — `test_no_api_key_references` scoped exclusions

- `backend/tests/test_no_api_key_references.py` — switch to
  `relative_to(root).parts`; add `.claude` + `worktrees` to the
  exclusion set.

### What is NOT done yet

- **`ix_patients_pseudonym` index** — still declared `index=True` on the
  model but not created by any migration. B2 suppressed it via the
  `include_object` filter so `alembic check` stays green; either land a
  0013 that creates it on Neon, or drop the `index=True` declaration if
  the slower lookup is fine.
- **`VARCHAR(36)` → `UUID` type alignment** across 13 legacy-id columns.
  Suppressed via `compare_type=False`. Real alignment should follow the
  0008/0009 dialect-gated `ALTER TYPE` pattern.
- **Drop redundant single-column `ix_*_user_id` indexes** after Postgres
  EXPLAIN confirms the 0011 composites are picked. Same item as the prior
  session; still needs a live-Neon EXPLAIN before the drop.
- **`audit_service.log_in_background` not yet wired** into the other
  routers that emit audit events (`reports.py`, `sessions.py`, etc.).
  B1's wave covered auth + auth_admin + patients; the remaining
  `audit.log()` call sites in other routers still take the sync path.
  Follow-up task: extend the BackgroundTasks wiring to those routes.

### Risks / Attention

- **B1 introduced a public-API breaking change on `AuthService`** — the
  email-emitting service methods now take optional `(background,
  db_factory)`. Backwards-compatible at the call site (both default to
  `None` → sync path), but anything that mocks the method signature
  needs updating. Existing tests pass via `TestClient` running
  `BackgroundTasks` synchronously after the response.
- **B2's `include_object` filter is a deliberate deferral**. If someone
  later adds a real index named the same as one of the entries in
  `_MIGRATION_ONLY_INDEXES` and expects autogenerate to flag it, the
  filter will silently swallow it. The filter is documented at the
  call site; revisit when the deferred 0013 lands.
- **`alembic check` only runs against SQLite in CI.** The guard catches
  metadata drift (column / FK / table presence) but not Postgres-specific
  divergence (e.g. partial indexes, jsonb defaults). For Neon parity, an
  occasional manual `DATABASE_URL=$NEON_URL alembic check --autogenerate`
  is still worthwhile.
- Owner WIP from earlier sessions (`anamnesis_engine` /
  `phonological_analyzer` / `anamnesis_catalog` /
  `test_phonological_analyzer`) — none of B1/B2/B3 touched these files.

### Next concrete action

Wire `audit_service.log_in_background(…)` into the remaining routers that
emit audit events (`backend/routers/reports.py`,
`backend/routers/sessions.py`, etc. — grep `self.audit.log(` or
`audit_service.log(` for the call sites) so the BackgroundTasks deferral
covers every request path. After that, the remaining open items in
`TASKS.md` "Next" are all LOW-severity (`ix_patients_pseudonym`,
`VARCHAR(36)→UUID`, dropping redundant single-column indexes).

### Ideal next prompt

```text
Read docs/ai/HANDOFF.md (latest "Session Summary"), then
docs/ai/TASKS.md "Next".

Current situation: main is at 33c542e, 0 ahead of origin/main. Five
commits landed today PM/evening (c0980ab, 0467587, 6c18482, 6e31983,
33c542e). 422/422 backend tests, alembic check CI guard live and
passing. The B1 BackgroundTasks plumbing only covers auth /
auth_admin / patients — the other routers still take the sync audit
path.

Your task: extend the audit-BackgroundTasks wiring from routers/auth.py
to routers/reports.py, routers/sessions.py, routers/soap.py, etc. (grep
'audit_service.log(' or 'self.audit.log(' for the full list). For each
route that emits an audit event, add 'background_tasks: BackgroundTasks'
+ 'db_factory: DBSessionFactory = Depends(get_db_factory)' and route
the emit through the svc-layer or audit_service.log_in_background
directly. After that, update docs/ai state files.
```

---

## Previous session — 2026-05-29 (PM) — A1/A2/A3 batch

**Agent:** Claude Code
**Date:** 2026-05-29 (PM)
**Role(s):** Coordinator + Implementer + Scribe (three parallel sub-agents)

### What was done

- Dispatched three parallel sub-agents in worktree isolation against three
  open follow-ups from `TASKS.md` "Next" + the schema-drift trap surfaced in
  the earlier 2026-05-29 hotfix:
  - **A1**: `get_optional_user` JWT optimization. Sub-agent introduced an
    `AuthIdentity` (`id`, `role`, `sid`) `frozen=True, slots=True` dataclass
    built straight from the JWT payload that `JWTAuthMiddleware` drops onto
    `request.state.user`. `get_optional_user` no longer takes
    `Depends(get_db)` and no longer does a `SELECT … FROM users` on every
    authenticated session-router request. The 9 endpoints in
    `backend/routers/sessions.py` only ever read `user.id`, so this is
    behavior-preserving. `get_current_user` chains on the optional dep, still
    returns the full `User` (DB-backed) for routers that read more than id
    (auth/admin/patients/reports/soap/exports/therapy_plans/analysis/
    suggestions/legacy). Override compatibility preserved via
    `isinstance(identity, User)` so existing test fixtures that
    `dependency_overrides[get_optional_user] = lambda: fake_user_object`
    keep working. Landed as **`c0980ab`**.
  - **A2**: auth email path async end-to-end. Sub-agent flipped three auth
    handlers (`register`, `reset_request`, `resend`) to `async def`, made the
    three corresponding `AuthService` methods async, dropped
    `EmailService._run_send` (the `asyncio.run` bridge that would refuse to
    run from inside a live event loop), and turned `send_verify_email` /
    `send_password_reset` into coroutines that `await self._send`.
    `FakeEmailService.send_*` mirrored to async so prod/fake stay
    swap-compatible. The other 13 auth handlers stayed sync (no email side
    effect, no async dep, no event-loop benefit — FastAPI runs sync routes
    in the threadpool anyway). Tests updated to `async def` + `await`;
    pytest-asyncio is already in auto mode. Landed as **`0467587`**.
  - **A3**: static schema-vs-migrations audit. Read-only pass over
    `backend/models/*.py` vs. `backend/alembic/versions/0001..0011`. No
    missing-column drift found — `0010` closed that bug class. Highest
    remaining risk is **missing FK constraints on Neon for 6 declared FKs**
    plus the manually-hotfixed `therapyplanrecord.user_id` FK that exists on
    Neon but not in alembic (so a fresh prod env from migrations would not
    recreate it). Report persisted to `docs/ai/AUDIT_2026-05-29_schema.md`
    with a sketched `0012_align_declared_fks.py` migration using the
    conditional `inspector.get_foreign_keys` pattern (no-op on Neon for the
    therapyplanrecord FK, additive everywhere else). A3 also recommends
    `alembic check` as a CI guard so the next column-vs-FK split is caught
    at PR time.
- Verified before push: backend `python -m pytest -q` → **419 passed**, full
  suite. `ruff check` clean on touched files (3 pre-existing import-sort
  errors in alembic migration tests remain — unchanged from baseline at
  `96f3fa6`). `mypy` clean on touched files (3 pre-existing errors in
  `alembic/versions/0010`/`0011` remain).
- Pre-push hook ran `backend·pytest + frontend·eslint + frontend·vitest`,
  all green. Push: `96f3fa6..0467587 main → main`.

### Files changed

#### `c0980ab` — get_optional_user JWT optimization

- `backend/dependencies.py` — new `AuthIdentity` frozen-slots dataclass +
  `_identity_from_request` helper; rewritten `get_optional_user`
  (no `Depends(get_db)`); rewritten `get_current_user` chaining on
  `get_optional_user` and accepting `AuthIdentity | User` for override
  transparency.
- `backend/routers/sessions.py` — type-annotation swap `User | None` →
  `AuthIdentity | None` across 9 endpoints + `_uid` helper; dropped unused
  `from models.auth import User` import.

#### `0467587` — auth email path async end-to-end

- `backend/routers/auth.py` — `register`, `reset_request`, `resend` flipped
  to `async def`; each `await`s the corresponding svc method.
- `backend/services/auth_service.py` — `register`,
  `request_password_reset`, `resend_verification` flipped to `async def`;
  each `await`s `self.email.send_*(…)` directly.
- `backend/services/email_service.py` — `_run_send` sync bridge removed;
  `send_verify_email` and `send_password_reset` now `async`, `await
  self._send`. `FakeEmailService.send_*` mirrored to `async`.
- `backend/tests/test_auth_service.py` — affected test functions flipped to
  `async def`; helper `_make_verified_user` made async; calls to
  `svc.register` / `svc.request_password_reset` `await`ed.
- `backend/tests/test_email_service.py` — affected test functions flipped to
  `async def`; new assertions that `EmailService.send_*` and
  `FakeEmailService.send_*` are coroutine functions (locks in the async-seam
  contract).

#### A3 (no code commit — audit only)

- `docs/ai/AUDIT_2026-05-29_schema.md` — schema audit report + proposed
  `0012_align_declared_fks.py` sketch + proposed `alembic check` CI step.

### What is NOT done yet

- **`0012_align_declared_fks` not landed.** A3 produced the sketch but
  intentionally did not write it; the FK additions change production behavior
  on DELETE and want explicit owner approval before applying. Lives in
  `AUDIT_2026-05-29_schema.md`. Owner decision.
- **`alembic check` CI step not added.** Recommended in A3. Single block to
  insert into `.github/workflows/ci.yml`; sketched in the audit file.
- **Type-encoding drift (`VARCHAR(36)` vs. `UUID`)** across 13 columns is
  unfixed — A3 classified as LOW (SQLAlchemy's implicit casts make INSERTs
  work). Cosmetic until autogenerate is turned on.
- **Other open perf items from the 2026-05-29 audit:** `audit_service.log()`
  → `BackgroundTasks` migration, and dropping the now-redundant
  single-column indexes after EXPLAIN confirms the composite from 0011 is
  picked. Both still in `TASKS.md` "Next".
- **`test_no_api_key_references` is fragile in worktree mode.** It scans the
  whole repo for `\bAPI_KEY\b` but the exclusion list misses
  `.claude/worktrees/`. A future agent dispatch with worktree isolation will
  trip it again until cleanup. One-line fix: add `"worktrees"` to the
  exclusion tuple at `backend/tests/test_no_api_key_references.py:17`. Not
  fixed in this session — out of scope of A1/A2/A3.

### Risks / Attention

- **A2 changed `EmailService.send_*` from sync to async** — any third-party
  caller of those public methods (none found in repo) would break. Internal
  callers (`AuthService`, tests) were updated in the same commit.
- **A1 changed the type returned by `get_optional_user`** from `User | None`
  to `AuthIdentity | None`. Any caller outside `routers/sessions.py` that
  imported it would break — none found, but flagged for future audits.
- **A3 surfaced a dev/prod schema split.** Local dev (`create_all`) emits
  the declared FKs; live Neon does not have them (except the one manual
  hotfix on therapyplanrecord). A foreign-key cascade test passing locally
  is not proof Neon cascades on DELETE.
- Owner WIP from earlier sessions (`anamnesis_engine` /
  `phonological_analyzer` / `anamnesis_catalog` /
  `test_phonological_analyzer`) — none of A1/A2/A3 touched these files.

### Next concrete action

Decide on the `0012_align_declared_fks` migration sketched in
`docs/ai/AUDIT_2026-05-29_schema.md`. Two parts:
  (i) Land the migration as alembic 0012 so a fresh prod env from migrations
      alone would reproduce Neon's state (additive on every other Neon
      table).
  (ii) Add the `alembic check` CI step from the audit file so the next
       column-vs-FK split fails at PR time.

After that, the remaining open perf items in `TASKS.md` "Next" are
agent-safe.

### Ideal next prompt

```text
Read docs/ai/HANDOFF.md (latest "Session Summary"), then
docs/ai/AUDIT_2026-05-29_schema.md.

Current situation: main is at 0467587, 0 ahead of origin/main. Two perf
commits landed today (c0980ab get_optional_user JWT opt, 0467587 auth email
async). Schema audit report persisted but no schema-changing migration yet
written.

Your task is to land the alembic 0012_align_declared_fks migration sketched
in AUDIT_2026-05-29_schema.md (the conditional inspector pattern means it's
a no-op on Neon for therapyplanrecord and additive everywhere else), AND
add the alembic check CI step from the same file. After that, update
docs/ai/CURRENT.md / TASKS.md / HANDOFF.md and commit.
```

---

## Previous session — 2026-05-29 (earlier — schema-drift hotfix)

**Agent:** Claude Code
**Date:** 2026-05-29
**Role(s):** Debugger + Operator + Scribe

### What was done

- Diagnosed a 500 on `POST /backend-api/therapy-plans` (save endpoint at
  `backend/routers/therapy_plans.py:40-67`). Backend log showed
  `psycopg2.errors.UndefinedColumn: column "user_id" of relation
  "therapyplanrecord" does not exist`.
- Root cause: schema drift. The auth multi-user refactor added
  `TherapyPlanRecord.user_id` (NOT NULL FK → users.id) but the live
  Neon table was created earlier without that column. The project
  bootstraps schemas via `SQLModel.metadata.create_all()` in
  `backend/database.py:33`, which only creates missing tables — it
  never ALTERs existing ones. There is no `alembic/versions/`
  directory, so no migration would have caught this.
- Verified the table was empty (`SELECT count(*) → 0`), then applied
  the missing column on Neon in one transaction:

  ```sql
  ALTER TABLE therapyplanrecord
    ADD COLUMN user_id UUID NOT NULL
    REFERENCES users(id) ON DELETE CASCADE;
  CREATE INDEX IF NOT EXISTS ix_therapyplanrecord_user_id
    ON therapyplanrecord(user_id);
  ```

- Post-migration verification on Neon:
  - Column `user_id uuid NOT NULL` present.
  - Index `ix_therapyplanrecord_user_id` present.
  - FK `therapyplanrecord_user_id_fkey → users(id) ON DELETE CASCADE`
    present.

### Files changed

- (Neon only — no repo files changed for the hotfix.)
- `docs/ai/HANDOFF.md` — this entry.

### What is NOT done yet

- **No alembic migration** representing this change exists in the
  repo. Local-sqlite developers and any fresh Neon environment still
  rely on `create_all`, which now produces the correct schema for new
  tables but would NOT bring an existing out-of-date table into sync.
- A second drift incident is structurally possible for any model that
  predated multi-user. `report_record`, `patient`, `soap_record`, and
  `auth` all have `user_id`, but only `therapyplanrecord` was hit
  today. A targeted schema audit against the live DB has NOT been done.

### Risks / Attention

- **Same class of bug can recur.** Without alembic versions, every
  future column add to a pre-existing table will silently miss the
  prod table and only surface as a 500 in production traffic. Strongly
  recommend introducing `alembic init` + autogenerate before the next
  schema change. Tracking in `TASKS.md` would be sensible.
- No data was destroyed: the affected table was empty before the
  ALTER. If it had not been, a backfill from `reports.user_id` via
  `report_id` would have been required.

### Next concrete action

Retry `POST /therapy-plans` from the UI — the original 500 should now
return 201. After that, decide whether to introduce alembic so this
class of drift is structurally impossible going forward.

### Ideal next prompt

> Audit the live Neon schema vs. the SQLModel definitions for
> `report_record`, `patient`, `soap_record`, and `auth`. For each
> model column missing in the table, generate the ALTER statement.
> Do not apply — return the diff so I can review. Then propose how to
> introduce alembic without disrupting `dev.sh`.

---

## Previous session — 2026-05-28

**Agent:** Claude Code
**Date:** 2026-05-28
**Role(s):** Implementer + Reviewer + Scribe (with parallel sub-agents)

### What was done

- Dispatched three parallel sub-agents against the top three agent-safe
  items from `TASKS.md` "Next" — UI loading skeletons, PDF export quality,
  and backend test coverage for therapy-plan / SOAP / compare. Reviewed
  each sub-agent's output in parallel, fixed reviewer-flagged
  high-priority items (PDF thread safety in pass 2; three real
  therapy-plan ownership bugs in pass 3), and landed the work as three
  thematic commits pushed to `origin/main` in this order:
  - `36c29d0` — `feat(frontend): add layout-aware loading skeletons for report/SOAP/therapy-plan`
  - `6840168` — `feat(backend): improve PDF export typography, layout, and thread safety`
  - `9c27c7e` — `feat(backend): enforce ownership on therapy-plan endpoints and consolidate tests`
- Dispatched a second wave of three parallel sub-agents to address the
  reviewer-flagged pre-existing items: a Scribe to refresh docs/ai, plus
  two frontend fix agents. Both fixes landed and pushed:
  - `11ce3cd` — `fix(frontend): wire SOAPModule.generateFromReport into stale-session helper`
  - `241f7fd` — `refactor(frontend): drop unused sessionId prop from TherapyPlanModule`
- Verified the full test + lint matrix after each commit: backend
  pytest 399 passed, frontend vitest 164 passed, `ruff check` clean,
  `mypy` clean, `tsc --noEmit` clean, `eslint` clean.
- `main` is now at `241f7fd`, 0 ahead / 0 behind `origin/main` (once the
  docs commit lands).

### Files changed

#### `36c29d0` — Layout-aware loading skeletons

- `frontend/src/components/Skeleton.tsx` (new) — shared skeleton primitive,
  `role="status"` + `aria-live`, `motion-reduce:animate-none`.
- `frontend/src/features/report/components/GeneratingView.tsx` — mirrors
  the final report layout to avoid layout shift.
- `frontend/src/features/report/components/GeneratingView.test.tsx`
  (new, colocated next to component — minor convention drift flagged by
  reviewer, not fixed in this commit; lives in `components/`, not
  `__tests__/`).
- `frontend/src/features/soap/SOAPModule.tsx` — SOAP skeleton variant.
- `frontend/src/features/soap/__tests__/SOAPModule.test.tsx` — +1 vitest case.
- `frontend/src/features/therapy-plan/TherapyPlanModule.tsx` — therapy-plan
  skeleton variant.
- `frontend/src/features/therapy-plan/__tests__/TherapyPlanModule.test.tsx`
  — +1 vitest case.

#### `6840168` — PDF export typography, layout, thread safety

- `backend/services/pdf_generator.py` — restructured: typography hierarchy
  (title / section / body), running header (patient pseudonym + report
  type + `record.created_at`), "Seite X von Y" footer, A4 margins,
  KeepTogether section blocks, HR accent under headings. Replaced
  module-level `_HEADER_CTX` global with a `_PageContext` dataclass
  captured per render via a closure-based `_make_on_page_hook` factory
  (defensive against future `loop.run_in_executor` use).
  `NumberedCanvas._generated_at` captures the timestamp once so first-pass
  and overdraw-pass footers cannot disagree across the midnight UTC
  boundary. Added empty-list guard to `_build_section`.
- `backend/routers/exports.py` — 1-line change: now passes
  `record.created_at` to `generate_pdf` so the header date matches the
  report, not the PDF-generation time.
- `backend/tests/test_pdf_generator.py` — new regression test
  `test_generate_pdf_no_cross_call_state_leak` exercising the per-render
  context via `ThreadPoolExecutor` (14 → 15 pdf tests; 397 → 399 backend
  total).

#### `9c27c7e` — Therapy-plan ownership + test consolidation

- `backend/routers/therapy_plans.py` — `GET /therapy-plans` now filters
  on `user_id`; `GET /therapy-plans/{id}` and `PUT /therapy-plans/{id}`
  now enforce ownership; all three return 404 (not 403) on miss, matching
  the `reports.py` / `sessions.py` convention to avoid leaking existence.
- `backend/models/therapy_plan_record.py` — added `user_id: UUID` FK
  mirroring `SOAPRecord`.
- `backend/alembic/versions/0010_therapy_plan_user_id.py` (new) —
  create-or-alter pattern from 0005/0006: nullable column → delete
  orphans → flip NOT NULL via `batch_alter_table` (SQLite-compatible).
  **Destructive on rollout — see Risks.**
- `backend/tests/test_soap.py` (deleted) — 2 cases were exact duplicates
  of `test_soap_routes.py`, 8 unique cases absorbed.
- `backend/tests/test_therapy_plans.py` (deleted) — all 4 cases
  (`POST /sessions/{id}/therapy-plan`) absorbed into
  `test_therapy_plans_routes.py` as a new
  `TestGenerateTherapyPlanFromSession` class.
- `backend/tests/conftest.py` — `unauth_client` fixture promoted here.
- `backend/tests/test_soap_routes.py` — DB-shape assertions, 401,
  ordering, and cross-user isolation cases absorbed.
- `backend/tests/test_therapy_plans_routes.py` — `TestGenerateTherapyPlanFromSession`
  class added; three new ownership-enforcement cases:
  `test_list_does_not_leak_other_users_plans`,
  `test_get_other_users_plan_returns_404`,
  `test_update_other_users_plan_returns_404`.

#### Docs (this scribe pass, uncommitted)

- `docs/ai/CURRENT.md` — rewritten to reflect the three new commits and
  drop the now-landed stale-session follow-up references.
- `docs/ai/TASKS.md` — three "Next" items moved to "Done" with SHAs; new
  "Next" items added for the four open reviewer findings.
- `docs/ai/HANDOFF.md` — this rewrite.

#### `11ce3cd` — SOAPModule stale-session

- `frontend/src/features/soap/SOAPModule.tsx` — `generateFromReport`
  catch branches on `isStaleSessionError` before the generic fallback,
  matching the canonical `ChatView` / `TherapyPlanModule` pattern.
- `frontend/src/features/soap/__tests__/SOAPModule.test.tsx` — +1 case
  asserting `handleStaleSession` fires once on `api.soap.fromReport`
  rejecting with `ApiError(404)`, and the raw backend detail does NOT
  reach the DOM. 163 → 164.

#### `241f7fd` — TherapyPlanModule dead prop removal

- `frontend/src/features/therapy-plan/TherapyPlanModule.tsx` —
  `TherapyPlanModuleProps` interface removed, function signature now
  `export function TherapyPlanModule()`. The component manages its own
  session via `tpSessionId`, never read the prop.
- `frontend/src/app/module/[slug]/page.tsx` — `<TherapyPlanModule />`
  call site updated.
- `frontend/src/features/therapy-plan/__tests__/TherapyPlanModule.test.tsx`
  — 6 `render(<TherapyPlanModule sessionId={null} />)` calls collapsed
  to `render(<TherapyPlanModule />)`. No behavior change, 164/164.

### What is NOT done yet

- `backend/tests/test_pdf_disclaimer.py` passes a `MagicMock` canvas;
  `getattr(MagicMock, "_generated_at", None)` returns a `MagicMock`
  (truthy), so a future test asserting the branding-line text would see
  `<MagicMock>` inside the string. Today's assertion (disclaimer string
  draw) still passes. Low priority future-proofing.
- `frontend/src/features/report/components/GeneratingView.test.tsx` lives
  next to the component instead of in `frontend/src/features/report/__tests__/`.
  Reviewer-flagged convention drift; not fixed in `36c29d0`.

### Risks / Attention

- **Migration `0010_therapy_plan_user_id.py` is destructive on rollout.**
  It drops `therapyplanrecord` rows where `user_id IS NULL` before
  flipping the column to NOT NULL. Acceptable for the current
  portfolio/demo status; revisit before any production rollout where
  real users may have orphan rows from the pre-ownership era.
- **Commit `9c27c7e` message minor inaccuracy.** The message mentions a
  "trivial import-sort fix in three alembic migration tests"; that change
  was reverted by the pre-commit hook (`ruff format`) before it landed.
  `ruff check` is clean across the suite regardless. Not amended because
  the project rule is to prefer new commits over amend — flagged for
  transparency only.
- **`test_pdf_disclaimer.py` `MagicMock` edge** (see "What is NOT done
  yet"). Future-proofing only.
- **Owner WIP** in `backend/services/anamnesis_engine.py`,
  `phonological_analyzer.py`, `anamnesis_catalog.py`, and
  `backend/tests/test_phonological_analyzer.py` — do **not** stage,
  commit, or modify these. M-6 stays blocked until the owner hands them
  over.
- **NEXT_PUBLIC_API_URL trap**: don't reintroduce an absolute host value
  in the frontend-e2e CI job — see the comment block in
  `.github/workflows/ci.yml`. It is baked into the production bundle at
  `npm run build` and breaks the `**/backend-api/**` Playwright mocks.
- Vercel `experimentalServices` is beta and may change without notice.
- Vercel preview deploy still fails on every PR with a pre-existing
  deployment-config error. Out of scope unless explicitly requested.

### Next concrete action

Wait for the owner to settle the anamnesis WIP and hand over M-6. If
picking work proactively in the meantime, the next agent-safe item from
`TASKS.md` "Next" is one of: `test_pdf_disclaimer.py` MagicMock spec
tightening, or moving `GeneratingView.test.tsx` to
`frontend/src/features/report/__tests__/` for convention alignment.

### Ideal next prompt

```text
Read docs/ai/HANDOFF.md and docs/ai/CURRENT.md first, then docs/ai/PROJECT.md
if you need architectural context.

Current situation: main is at 241f7fd, even with origin/main. Five
commits landed today (36c29d0 UI skeletons, 6840168 PDF quality +
thread safety, 9c27c7e therapy-plan ownership + test consolidation,
11ce3cd SOAPModule stale-session, 241f7fd TherapyPlanModule dead-prop
cleanup). Backend pytest 399/399, frontend vitest 164/164, ruff / mypy
/ tsc / eslint all clean.

M-6 (anamnesis completion logic) remains blocked on owner WIP in
backend/services/anamnesis_engine.py + phonological_analyzer.py +
anamnesis_catalog.py — do NOT touch those files until the owner
explicitly hands them over.

Your task: <one of>
  (a) wait for the owner to hand off M-6;
  (b) pick the next agent-safe item from docs/ai/TASKS.md "Next"
      column (test_pdf_disclaimer MagicMock tightening or
      GeneratingView.test.tsx convention realignment are both small);
  (c) <my custom direction>.

After completing the task, update docs/ai/CURRENT.md, docs/ai/TASKS.md,
and docs/ai/HANDOFF.md before stopping.
```

---

## Today's PRs (chronological)

| PR | Subject | Result |
| --- | --- | --- |
| [#3](https://github.com/ucarsinan/logopaedie-report-agent/pull/3) | Security & quality audit fixes (C-1/C-2, H-1..H-4, M-1/2/3/5, L-2/3/4) | merged 2026-05-27 (`b33cf7e`) |
| [#4](https://github.com/ucarsinan/logopaedie-report-agent/pull/4) | `fix(ci): drop NEXT_PUBLIC_API_URL override in E2E job` | merged 2026-05-27 (`5a00a3e`) |
| [#5](https://github.com/ucarsinan/logopaedie-report-agent/pull/5) | `docs: sync CLAUDE.md and docs/ai/PROJECT.md with current architecture (M-4)` | merged 2026-05-28 (`e8fe12b`) |
| [#6](https://github.com/ucarsinan/logopaedie-report-agent/pull/6) | `chore(ci): opt JS actions into Node.js 24 ahead of 2026-06-02 cutover` | merged 2026-05-28 (`9119077`) |

Today's direct-to-`main` commits (no PR): `129333c`, `cbf4d72`,
`11540d1`, `fc2cab1`, `339b7a4`, `3b03124`, `c332a13`, `4a23a7c`,
`a56b1ef`, `36c29d0`, `6840168`, `9c27c7e`, `11ce3cd`, `241f7fd`.

---

## Open Items

- [ ] **M-6** — anamnesis completion logic, blocked on owner WIP.
- [ ] **Pre-commit-vs-`ruff check` I001 conflict** — D3 surfaced that
      the project's `.pre-commit-config.yaml` "ruff (legacy alias)"
      hook reverts whatever `ruff check --fix` produces, keeping the
      4-error baseline stuck. Real fix: replace the legacy alias with
      `ruff check --fix` in the hook config OR adjust pyproject.toml
      isort.
- [ ] **Type-encoding (`VARCHAR(36)` → `UUID`)** across 13 legacy-id
      columns. Suppressed via `compare_type=False`; real alignment via
      a future migration mirroring 0008/0009.
- [ ] Drop redundant single-column `ix_*_user_id` indexes after Postgres
      EXPLAIN confirms 0011 composites are picked.
- [ ] **`alembic check` only runs against SQLite in CI.** For Neon
      parity, an occasional manual `DATABASE_URL=$NEON_URL alembic check
      --autogenerate` is still useful — Postgres-specific drift (partial
      indexes, jsonb defaults) is invisible to the SQLite guard.
- [ ] Pre-existing Vercel preview deploy failure — separate deployment-config
      issue. Out of scope unless explicitly requested.

---

## Checks

| Check | Status | Notes |
| --- | --- | --- |
| `python -m pytest` (backend) | **427 passed**, locally green after `44ff83b` | full suite (423 + 3 from D1 + 1 from D2) |
| `npm test` (frontend unit) | green via pre-push hook on `44ff83b` | 43 test files |
| `alembic check` | **No new upgrade operations detected** after `44ff83b` | guard still active, no drift |
| `npx playwright test` (E2E) | last green in PR #6 CI | 32 cases / 11 specs, chromium-only |
| `npm run build` | passed | with `/backend-api` default, **not** absolute host |
| `ruff check`, `mypy`, `eslint`, `tsc` | passed locally on touched files; 3 pre-existing ruff errors in alembic migration tests + 3 pre-existing mypy errors in `alembic/versions/0010`/`0011` remain unchanged from baseline | |
| Vercel deploy | **fails** (pre-existing) | separate from CI; ignore for green-up |
