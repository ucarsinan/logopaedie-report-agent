# CURRENT.md — Current Working State

> **This file must be updated at the end of every meaningful AI session.**
> It represents the live state of the work — not a backlog, not a history.
> If it is out of date, the next agent will start from wrong assumptions.

---

## Last Updated

- **Date:** 2026-06-01 (afternoon — L-wave, partial)
- **Updated by:** Claude Code
- **Session focus:** L-wave dispatched 3 parallel agents to close
  the remaining K-wave-deferred items. **2 of 3 agents hit Anthropic
  network errors** (socket closed unexpectedly mid-run) before
  committing — L1 (S-7 access-token revocation) had only stubbed
  the `AccessTokenBlocklist` service file and not finished the
  dependency-injection wiring, so it was discarded. L2 (disable_2fa
  P-3 + X-RateLimit-* headers) finished writing its changes in the
  worktree but never committed; **the disable_2fa portion was
  salvaged inline**, while the `headers_enabled=True` + new
  `SlowAPIMiddleware` parts were dropped — they broke 85 existing
  tests with slowapi's `parameter response must be an instance of
  starlette.responses.Response` error, the agent's own
  middleware-fix attempt didn't catch every route. L3 (independent
  code review of J/K-waves, 7 commits) ran to completion and
  produced a useful structured report; **H-1 frontend type
  mismatch fix applied inline**, H-2 (`.env.example` for
  `TRUSTED_PROXY`) blocked by the env-file permission denylist —
  documented as TASKS.md follow-up.

---

## Current Goal

No agent-driven goal active. What landed this session is small but
real: `disable_2fa` now uses the same bulk `sa.update` pattern as
`change_password` and `enable_2fa` (K1 left it untouched), and the
`ReportListResponse.total` TypeScript type now correctly reflects
the nullable contract introduced by K1's `include_total` opt-in
(future-proofs the frontend before any caller adopts the opt-in).

What did NOT land but is well-scoped for next attempt:

- **S-7 access-token revocation** — Redis blocklist with per-user
  `revoked_until` cutoff key, comparing JWT `iat` claim. The L1
  agent had picked the correct approach (the simpler one from the
  brief, not jti-tracking) and stubbed the service file before the
  socket closed. Re-dispatch should reuse the same brief.
- **X-RateLimit-* response headers** — slowapi has the plumbing
  (`headers_enabled=True`) but every route handler in this project
  returns a plain dict or `Mapping`; slowapi rejects that path.
  Real fix requires routes to return `JSONResponse(content=..., ...)`
  or adopt the `SlowAPIMiddleware` carefully with response-type
  inspection. L2's middleware attempt didn't work — needs a deeper
  refactor or a slowapi version bump.

**M-6** (anamnesis completion logic) remains the outstanding audit
item and is still blocked on owner-driven WIP in
`backend/services/anamnesis_engine.py`, `phonological_analyzer.py`,
and `anamnesis_catalog.py`.

---

## Current Branch

```text
main
```

Local `main` is **2 ahead of `origin/main`** (`24ce58f` + `b39c72b`,
plus this docs commit).

Today's session commits (newest first):

- `b39c72b` — `fix(frontend): widen ReportListResponse.total to nullable for include_total opt-in`
- `24ce58f` — `fix(backend): disable_2fa bulk session revoke via sa.update (K-wave deferred)`

---

## Verification snapshot (pre-push)

- `ruff check .` → All checks passed!
- `mypy services/auth_service.py` → Success: no issues found in 1 source file
- `pytest -q` → **510 passed, 9 skipped** (was 508+9; +2 from L2's
  salvaged disable_2fa tests)
- Frontend `tsc` not separately verified — but the type change is
  a strict widening (`number` → `number | null`) with a null-guard
  added at the only consumer call site, so it should compile.

---

## L3 review findings still open

Apply when the network is more cooperative or via small inline
patches:

- **H-2** — `TRUSTED_PROXY` not in any deployment artifact
  (`.env.example` blocked by repo permission denylist for env-files;
  add manually). Without this, the first production deploy after K2
  silently buckets all Vercel-edge traffic under one IP. Operator
  must set `TRUSTED_PROXY` explicitly OR redesign rate-limit
  strategy.
- **M-1** — `_audit` partial-wiring `RuntimeError` turns into HTTP
  500 for the client (intended, fail-loud) but the audit row is
  lost. Worth a docstring note on `_audit`.
- **M-2** — `Retry-After` value is the bucket window (60s for
  `30/minute`), not time-to-next-slot. slowapi 0.1.9 API limitation;
  client wait will be conservative-correct, not optimal.
- **M-3** — `derive_age_group` silently misclassifies future or
  pre-1900 birthdates into the wrong bucket (future → "kind").
  The bucket feeds into the AI-generated clinical report. Needs
  either a clamp or an explicit `None`/raise. Owner decision —
  test currently pins the *current* contract.
- **L-1** — `deps_with_2fa` fixture vs. inline TOTP wiring: 3 K1
  tests do inline wiring instead of using K3's fixture. Cosmetic
  refactor opportunity.
- **L-2** — 3 service methods (`start_2fa_setup`, `enable_2fa`,
  `disable_2fa`) still use bare `assert self.totp is not None`.
  Same class as J1's S-4 fix on `_audit`. Strippable under
  `python -O`.

---

## Key things the next agent should know

1. **`disable_2fa` now matches the `change_password`/`enable_2fa`
   bulk pattern.** Same `_current_session_hash` semantics: preserved
   when set, all sessions revoked otherwise. Tests use
   `deps_with_2fa` fixture (K3's contribution) — the canonical
   fixture for 2FA service-unit tests.
2. **`ReportListResponse.total` is now `number | null`.** The only
   current consumer (`HistoryModule.tsx`) adds `res.total ?? 0`
   before passing to `setTotal`. Any new consumer must do the same
   if it might call `api.reports.list({ include_total: false })`.
3. **L1's S-7 attempt picked approach (b) from the brief**:
   per-user `revoked_until` Redis key with cutoff vs. JWT `iat`.
   Started writing `backend/services/access_token_blocklist.py` in
   the worktree. The pattern is correct; the network just cut out
   before the dependency-injection + tests landed. Re-dispatch
   with the same brief is the right move.
4. **L2's slowapi `headers_enabled=True` did NOT work even with
   `SlowAPIMiddleware` registered.** 85 tests failed with
   `parameter response must be an instance of
   starlette.responses.Response`. The middleware ordering attempt
   (CORS → SlowAPI → ServiceToken → JWT) didn't change the failure
   mode. A future attempt needs to either bump slowapi or
   selectively wrap routes that need the headers — broad-stroke
   enablement isn't viable.
