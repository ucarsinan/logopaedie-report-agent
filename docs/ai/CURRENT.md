# CURRENT.md — Current Working State

> **This file must be updated at the end of every meaningful AI session.**
> It represents the live state of the work — not a backlog, not a history.
> If it is out of date, the next agent will start from wrong assumptions.

---

## Last Updated

- **Date:** 2026-06-01 (morning — J-wave + H-wave critical follow-up)
- **Updated by:** Claude Code
- **Session focus:** Three read-only audit agents (I1 code review, I2
  test-coverage audit, I3 security/perf sweep) ran against the H-wave
  and surfaced a **Critical bug in 0017** (missing
  `soaprecord.user_id` + `therapyplanrecord.user_id` FK drops — first
  Postgres deploy would have failed). Fix pushed as `bf04e8b`. Then
  three parallel implementation agents (J1/J2/J3) addressed the
  bundled high/medium findings: J1 security hardening (PII hash, 2FA
  setup audit/rate-limit, `assert`→`raise`, `hmac.compare_digest`),
  J2 three new rate limits on `/auth/logout` + `/auth/sessions`,
  J3 closed test gaps for `session_store` + `audit_service.query` and
  fixed the latent `_apply_0018` transaction harness bug.

---

## Current Goal

No agent-driven goal active. The post-H-wave audit cycle closed
out the major Critical/High/Medium findings. What's left is
deferrable LOW-severity hygiene + items requiring owner judgment.

**M-6** (anamnesis completion logic) remains the outstanding audit
item and is still blocked on owner-driven WIP in
`backend/services/anamnesis_engine.py`, `phonological_analyzer.py`,
and `anamnesis_catalog.py`. Treat them as untouchable until the owner
explicitly hands them over.

Remaining items in TASKS.md "Next":

- Drop redundant single-column `ix_*_user_id` indexes (needs live
  Neon EXPLAIN — not agent-safe; owner decision)
- I3 leftovers: S-6 (XFF trust in preview deploys — needs deploy-env
  audit), S-7/S-8 (informational, post-feature considerations),
  P-1 (sessions pagination), P-3 (bulk-update consolidation in
  `change_password`/`enable_2fa`), P-5 (reports list COUNT cost)
- I2 leftovers: `auth_service.start_2fa_setup` + `disable_2fa` could
  benefit from more direct service-level unit tests (J1 added
  audit-emit + rate-limit assertions, but not the full happy-path
  unit suite I2 recommended). Also `patient_service` + `totp_service`
  have `raises=0` — error-path coverage gap.
- Pre-existing Vercel preview deploy failure (out of scope)

---

## Current Branch

```text
main
```

Local `main` is **4 ahead of `origin/main`** (J-wave + this docs
commit). About to push: `102e592` + `869c77f` + `de96f6c` + this docs
commit.

Today's J-wave commits (newest first):

- `de96f6c` — `feat(backend): rate-limit logout + sessions list/delete (S-2)`
- `869c77f` — `fix(backend): security bundle (PII hash + 2FA setup audit/rate + token compare + assert→raise)`
- `102e592` — `test(backend): cover session_store + audit_service.query + fix 0018 test transaction`
- `bf04e8b` — `fix(backend): drop soaprecord+therapyplanrecord FKs in 0017 cluster` (Critical post-H-wave)
- `5e8dd2c` — `docs(ai): record H-wave (0017+0018 cluster UUID migrations, F2 markers, mypy fix)`

---

## Verification snapshot (pre-push)

- `ruff check .` → All checks passed!
- `mypy services/auth_service.py services/audit_service.py services/session_store.py middleware/service_token.py routers/auth.py`
  → Success: no issues found in 5 source files
- `DATABASE_URL=sqlite:///./ci_check.db alembic upgrade head` → 0001→0018 clean
- `alembic check` → "No new upgrade operations detected"
- `pytest -q` → **474 passed, 9 skipped** (was 448+9; +26 across J1/J2/J3)

---

## Key things the next agent should know

1. **AuditLog metadata schema changed (J1 / S-1):** the three audit
   events `user.register_attempt`, `password.reset_requested`,
   `user.resend_verification` no longer carry the raw email in
   `metadata_json`. Replaced with `email_hash` (SHA-256 of
   lowercased email, first 32 hex chars, via
   `services.auth_service._hash_email`). Any external tooling /
   queries that filter by raw email will break — switch to email_hash.
2. **`AuthService.start_2fa_setup` signature changed (J1 / S-3):**
   from `(db, user)` to `(db, user, *, ip=None, ua=None, background=None, db_factory=None)`.
   All new args are keyword-only defaulting to `None`, so existing
   direct callers keep working (emit then takes the sync audit path).
   Wire `background_tasks` + `db_factory` if you want the audit row
   to land via BackgroundTasks.
3. **`AuthService._audit` partial-wiring now raises `RuntimeError`,
   not `AssertionError`** (J1 / S-4). Survives `python -O`. Any test
   catching `AssertionError` for this specific invariant would need
   updating (none currently do, verified).
4. **`/auth/2fa/setup` is now `3/hour` rate-limited** (J1 / S-3). If
   you're writing 2FA-flow integration tests, account for this — use
   `unique_ip_headers` fixture or pin the in-memory limiter.
5. **Three new rate limits `30/minute`** on `/auth/logout`,
   `GET /auth/sessions`, `DELETE /auth/sessions/{session_id}` (J2 /
   S-2). All other `/auth/*` routes were already limited.
6. **0018 test harness now uses `eng.begin()`** instead of
   `eng.connect()` (J3 / I1 Medium [3]). Cosmetic on SQLite
   (migration body is no-op there), but structurally correct for the
   skipped Postgres path.
7. **`audit_service.query` has NO time-range filter** (J3 finding).
   Signature is `query(db, *, event=None, user_id=None, limit=50, offset=0)`.
   If the admin UI needs date filtering, that's a separate service
   extension.
8. **`session_store.get_authorized(session_id, user_id)`** takes a
   `user_id: str | None`, **not a `user` object** (J3 finding —
   matches actual impl, contradicts the I2 audit phrasing).
   Anonymous demo sessions (`user_id is None` on the row) are
   reachable both by `None` and by any authenticated `user_id` —
   intentional, both paths now have test coverage.
9. **0017 Critical fix (`bf04e8b`):** the cluster migration was
   missing `soaprecord` and `therapyplanrecord` from `_FK_SPECS`.
   The `_column_is_varchar` guard in step 2 correctly skips the
   redundant ALTER TYPE for their already-UUID columns; only the
   drop (step 1) + recreate (step 3) was needed to let Postgres
   swap the `users.id` PK type underneath. Pattern matches H2's
   design call on `fk_reports_patient_id_patients`. SQLite is no-op
   so CI never saw the bug; first Postgres deploy would have raised
   "cannot alter type of a column used in a foreign key constraint".
10. **Rate-limit 429 response shape** (J2 awareness note): the
    project's custom `RateLimitExceeded` handler in
    `backend/main.py:162-167` returns a bare `JSONResponse` with
    German body `"Zu viele Anfragen"` and **no `Retry-After` /
    `X-RateLimit-*` headers**. If you want clients to back off
    intelligently, that's a one-line follow-up.
