# HANDOFF.md — Agent-to-Agent Handoff

> **This file enables any agent to continue work without chat history.**
> It must be updated at the end of every meaningful AI session.
> The rule: if the next agent cannot understand the situation from this file alone, the handoff is incomplete.

---

## Last Updated

- **Date:** 2026-05-29 (late evening)
- **Updated by:** Claude Code
- **Handoff to:** next agent picking from `TASKS.md` "Next" — only the
  LOW-severity follow-ups remain (`VARCHAR(36)→UUID` type alignment, drop
  redundant single-column indexes after EXPLAIN) plus the
  T1/T2/T3/M4 follow-ups from the C3 review.

---

## Session Summary

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
- [ ] **T1 / T2 / T3** — missing end-to-end tests for the audit
      BackgroundTasks path; see `TASKS.md` "From 2026-05-29 evening code
      review".
- [ ] **M4** — `AuthService.refresh` happy path has no audit row.
      Pre-existing; surfaced by the C3 review.
- [ ] **Type-encoding (`VARCHAR(36)` → `UUID`)** across 13 legacy-id
      columns. Suppressed via `compare_type=False`; real alignment via
      a future migration mirroring 0008/0009.
- [ ] Drop redundant single-column `ix_*_user_id` indexes after Postgres
      EXPLAIN confirms 0011 composites are picked.
- [ ] **`alembic check` only runs against SQLite in CI.** For Neon
      parity, an occasional manual `DATABASE_URL=$NEON_URL alembic check
      --autogenerate` is still useful — Postgres-specific drift (partial
      indexes, jsonb defaults) is invisible to the SQLite guard.
- [ ] **Ruff baseline is now 4 errors** (was 3) — `I001` import-sort
      across alembic migration tests including `test_migration_0012.py`.
      Auto-fixable; left for a holistic cleanup.
- [ ] Pre-existing Vercel preview deploy failure — separate deployment-config
      issue. Out of scope unless explicitly requested.

---

## Checks

| Check | Status | Notes |
| --- | --- | --- |
| `python -m pytest` (backend) | **423 passed**, locally green after `222c708` | full suite (422 + 1 new `test_patient_pseudonym_has_no_standalone_index`) |
| `npm test` (frontend unit) | green via pre-push hook on `33c542e` | 43 test files |
| `alembic check` | **No new upgrade operations detected** after `90c51e3` | C2 removed `ix_patients_pseudonym` from the filter; guard now actively enforces it |
| `npx playwright test` (E2E) | last green in PR #6 CI | 32 cases / 11 specs, chromium-only |
| `npm run build` | passed | with `/backend-api` default, **not** absolute host |
| `ruff check`, `mypy`, `eslint`, `tsc` | passed locally on touched files; 3 pre-existing ruff errors in alembic migration tests + 3 pre-existing mypy errors in `alembic/versions/0010`/`0011` remain unchanged from baseline | |
| Vercel deploy | **fails** (pre-existing) | separate from CI; ignore for green-up |
