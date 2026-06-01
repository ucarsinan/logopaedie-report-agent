# CURRENT.md — Current Working State

> **This file must be updated at the end of every meaningful AI session.**
> It represents the live state of the work — not a backlog, not a history.
> If it is out of date, the next agent will start from wrong assumptions.

---

## Last Updated

- **Date:** 2026-06-01 (mid-morning — K-wave)
- **Updated by:** Claude Code
- **Session focus:** K-wave (3 parallel sub-agents) cleared the
  remaining I3-deferred items and I2 deferred test gaps. K1: perf
  trio (`GET /auth/sessions` pagination + `change_password`/
  `enable_2fa` bulk-update consolidation + `GET /reports` COUNT
  opt-in). K2: security hygiene (`TRUSTED_PROXY` strict XFF gate +
  `Retry-After` header on 429). K3: test-coverage uplift (+18
  tests covering 2FA service paths, patient_service error branches,
  totp_service error branches). One merge conflict in
  `test_auth_service.py` between K1 (P-3 sibling-revoke tests) and
  K3 (2FA service tests) resolved by keeping both sets; one K1 test
  bug (`TOTP_ENCRYPTION_KEY` should be `SESSION_ENCRYPTION_KEY`)
  fixed inline before commit landed.

---

## Current Goal

No agent-driven goal active. The K-wave closed:

- **I3-deferred**: S-6 (XFF gate), P-1 (sessions pagination),
  P-3 (bulk-update consolidation), P-5 (reports COUNT opt-in),
  and the rate-limit 429 header gap.
- **I2-deferred**: `auth_service.start_2fa_setup`/`disable_2fa`/
  `login_2fa` service-unit tests, `patient_service` error-path
  coverage, `totp_service` error-path coverage.

What remains in TASKS.md "Next":

- **I3 S-7** (informational) — access-token revoke on password
  change via Redis blocklist. Owner-decision.
- **I3 S-8** (informational) — `get_optional_user` lock/verify
  checks. Documented trade-off; safe while consumers only read
  `user.id`.
- Drop redundant single-column `ix_*_user_id` indexes — needs
  live Neon EXPLAIN.
- Pre-existing Vercel preview deploy failure (out of scope).
- **M-6** (anamnesis completion logic) — blocked on owner-WIP.

K1 noticed but did NOT touch: `disable_2fa` has the same per-row
loop pattern as `enable_2fa`/`change_password`. Worth a small
follow-up (1-line change + 1 test) if anyone wants pattern
consistency.

K2 surfaced a deploy concern (now in HANDOFF.md): **production
deploys must set `TRUSTED_PROXY` to the actual proxy IP**, otherwise
XFF is ignored and per-IP rate limits will collapse all traffic to
the single Vercel edge IP. Vercel's edge IPs rotate, so this needs
operator attention.

---

## Current Branch

```text
main
```

Local `main` is **4 ahead of `origin/main`** (K-wave + this docs
commit). About to push: `1b22548` + `77da09a` + `63ce9e0` + this docs
commit.

Today's K-wave commits (newest first):

- `63ce9e0` — `fix(backend): XFF gated on TRUSTED_PROXY + 429 Retry-After header (I3 S-6 + headers)`
- `77da09a` — `perf(backend): sessions pagination + bulk session revoke + reports COUNT opt (I3 P-1/P-3/P-5)`
- `1b22548` — `test(backend): cover 2FA service paths + patient/totp error branches (I2 deferred)`
- `8a00903` — `docs(ai): record I/J-wave post-H-wave audit cycle and Critical 0017 fix`

---

## Verification snapshot (pre-push)

- `ruff check .` → All checks passed!
- `mypy <9 K-wave files>` → Success: no issues found in 9 source files
- `DATABASE_URL=sqlite:///./ci_check.db alembic upgrade head` → 0001→0018 clean (unchanged)
- `pytest -q` → **508 passed, 9 skipped** (was 474+9; +34 across K1/K2/K3)

---

## Key things the next agent should know

1. **`GET /auth/sessions` accepts `limit` (default 50, max 200) and
   `offset` (default 0)** as Pydantic v2 `Query` parameters. Old
   callers (no params) get up to 50 rows — was previously unbounded.
   Frontend uses `useSessions()` which doesn't paginate yet but the
   server contract is now bounded by default.
2. **`GET /reports` has `include_total: bool = True` opt-in.** Default
   behavior unchanged (returns `total: int`). Callers can pass
   `include_total=false` for cheaper pagination on page 2+ — response
   `total` becomes `null` in that case. Frontend `ReportListResponse`
   type may want to relax `total` to `int | null` if it adopts the
   opt-in path.
3. **`AuthService.change_password` and `enable_2fa` now use a single
   bulk `sa.update(UserSession).where(...).values(revoked_at=...)`**
   instead of a Python for-loop with per-row `db.add()`. Same
   pattern as `refresh()` and matches the existing `_atomic()`
   helper. K1 deliberately left `disable_2fa` untouched — it has
   the same loop pattern, follow-up opportunity.
4. **`TRUSTED_PROXY` semantics changed (K2 / S-6) — breaking config
   change for production:** `client_ip_key` now ignores
   `X-Forwarded-For` UNLESS `TRUSTED_PROXY` env var is set AND
   matches the inbound socket IP. Previously gated on
   `_is_production()`. **Without setting `TRUSTED_PROXY`, all
   traffic from Vercel's edge proxy will be bucketed under a
   single IP**, collapsing per-IP rate limits. Vercel's edge IPs
   rotate, so operators must either (a) determine the actual
   internal proxy IP between Vercel edge and the function and set
   `TRUSTED_PROXY` to that, or (b) accept the more conservative
   per-instance bucketing.
5. **`conftest.py` pins `TRUSTED_PROXY="testclient"`** so Starlette
   `TestClient` requests continue to honor the `unique_ip_headers`
   fixture for per-test rate-limit isolation. If you write a new
   test that uses a different test client, account for this.
6. **429 responses now carry `Retry-After`** computed from
   `exc.limit.limit.get_expiry()` (slowapi 0.1.9 — no direct
   `retry_after` attribute, but the limit's expiry window is
   reachable; wrapped in `contextlib.suppress` with 60s fallback).
   Optional `X-RateLimit-*` headers were not added — slowapi has
   the plumbing (`headers_enabled=True`) but the project's
   `_build_limiter` doesn't enable it.
7. **2FA service tests live in `test_auth_service.py`** (K3 / I2
   deferred), not in `test_2fa_routes.py`. The new fixture
   `deps_with_2fa` wires a real `TOTPService` + in-memory
   `ChallengeStore` + Fernet key so tests can drive
   `start_2fa_setup` / `enable_2fa` / `disable_2fa` / `login_2fa`
   directly. Route-level integration tests remain in
   `test_2fa_routes.py`.
8. **K3's contract findings worth knowing:**
   - `update_patient` does NOT enforce ownership at the service
     level — the router does via `_get_active_or_404`. A direct
     service call bypasses authorization.
   - `derive_age_group` does NOT validate sane DOB ranges — future
     dates become negative years and silently fall into the `<13
     → "kind"` bucket; pre-1900 dates fall into `"erwachsen"`.
     No exception, no clamping. Documented in tests as the
     actual contract.
   - `login_2fa` replay protection runs through `last_totp_step`
     (already covered at route level; K3 added service-level
     coverage).
9. **K1 test bug discovered + fixed during integration:** K1 used
   `monkeypatch.setenv("TOTP_ENCRYPTION_KEY", ...)` but the actual
   env var name is `SESSION_ENCRYPTION_KEY` (per
   `services/totp_service.py:18`). Fixed inline before K1's commit
   landed.
