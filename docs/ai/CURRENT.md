# CURRENT.md — Current Working State

> **This file must be updated at the end of every meaningful AI session.**
> It represents the live state of the work — not a backlog, not a history.
> If it is out of date, the next agent will start from wrong assumptions.

---

## Last Updated

- **Date:** 2026-06-02 (afternoon — N-wave)
- **Updated by:** Claude Code
- **Session focus:** N-wave continued past audit-closure with hygiene
  + review + test coverage uplift. N1 finished M2's bare-assert sweep
  on `login_2fa:770` (compound split into two if/raise blocks; full
  service-layer grep confirmed it was the only remaining match). N2
  independent review of M-wave found 4 follow-ups (H-1 bare-except
  scope, H-2 same-second iat edge, M-1 private attr access, M-3
  leap-year test fragility). H-1 attempted inline narrowing broke 51
  tests (`redis.exceptions.ConnectionError` doesn't inherit from
  built-in `ConnectionError`); reverted to `except Exception` +
  elevated log WARNING → ERROR for production monitoring visibility.
  N3 added +9 P2-tier service tests (email/password/challenge_store/
  report_comparator). Net: **533 passed, 9 skipped** (+11 to 522).

---

## Current Goal

No agent-driven goal active. The full audit-cycle is closed; N-wave
was speculative hygiene/coverage work and produced clean small wins.

Open from N2 review (small inline fixes when convenient — ~20min
batch):

- **H-2** — `is_token_revoked` boundary `<` → `<=` for same-second
  inclusive
- **M-1** — public `access_ttl_seconds` accessor on `TokenService`
- **M-3** — `date(today.year - 120, today.month, min(today.day, 28))`
  in the boundary test for Feb 29 safety

**M-6** (anamnesis completion logic) remains the outstanding audit
item and is still blocked on owner-driven WIP in
`backend/services/anamnesis_engine.py`, `phonological_analyzer.py`,
and `anamnesis_catalog.py`.

What remains in TASKS.md "Next" (all non-agent-actionable):

- Drop redundant `ix_*_user_id` indexes — needs Neon EXPLAIN.
- Vercel preview deploy — pre-existing config issue.
- `TRUSTED_PROXY` deploy-env audit — operator-side.
- X-RateLimit-* response headers — slowapi version bump.

---

## Current Branch

```text
main
```

Local `main` is **4 ahead of `origin/main`** (N-wave + this docs
commit). About to push: `c941910` + `11540a4` + `fd46f35` + this
docs commit.

Today's N-wave commits (newest first):

- `fd46f35` — `fix(backend): elevate access_token_blocklist fail-open log to ERROR (N2 H-1 partial)`
- `11540a4` — `test(backend): cover P2 service test gaps (email/password/challenge_store/report_comparator)`
- `c941910` — `refactor(backend): split login_2fa compound assert + sweep similar asserts (post-M-wave hygiene)`
- `221e67a` — `docs(ai): record M-wave (S-7 + L-1/L-2 hygiene + M-3 clinical guard)` (this morning)

---

## Verification snapshot (pre-push)

- `ruff check .` → All checks passed!
- `mypy middleware/auth.py` → Success: no issues found in 1 source file
- `pytest -q` → **533 passed, 9 skipped** (was 522+9; +2 N1 + +9 N3 = +11)
- After H-1 attempted narrow: 51 failures (network errors propagated)
- After H-1 revert + ERROR-level log: 533 passed restored

---

## Key things the next agent should know

1. **`login_2fa` invariant guards are now explicit `if/raise`.** The
   compound `assert self.totp is not None and self.challenges is not
   None` is gone; replaced by two separate `if/raise RuntimeError`
   blocks at `auth_service.py:770-783` matching the J1/M2 message
   style. Tests pin both failure modes.

2. **The full service-layer bare-assert sweep is done.** N1 grepped
   `^\s*assert ` across `backend/services/` (excluding owner-WIP) and
   found exactly 1 match (the compound login_2fa one). No category-(b)
   algorithmic asserts or debug helpers exist outside owner-WIP.

3. **`access_token_blocklist` fail-open is deliberately broad.** The
   `except Exception` in `middleware/auth.py:55` catches everything
   including programming errors. N2's H-1 recommendation to narrow
   was tried but broke 51 tests (`redis.exceptions.ConnectionError`
   is NOT a Python `ConnectionError` subclass). Reverted, but log
   level is now ERROR (not WARNING) with `exc_info=True` so
   production monitoring catches code-path regressions. The
   project's posture is **availability > regression detection**: a
   silent S-7 bypass for up to access_token_ttl (~15min) is
   preferable to a 500 storm on every authenticated request.

4. **N3 contract findings worth knowing** (none are bugs; tests
   pin the actual contract):
   - `EmailService.send_verify_email` / `send_password_reset`
     **re-raise** provider errors — they do NOT swallow + log.
     Callers own retry/log/5xx decisions.
   - `PasswordService.hash("")` succeeds — argon2id accepts empty
     string. Reject empties at the validation layer above.
   - `PasswordService.verify` never raises on malformed hash —
     returns `False` for missing hash, non-argon2 prefix, or
     `(ValueError, UnknownHashError)`.
   - `ChallengeStore` SETEX uses `nx=True` — duplicate `put` is
     silently ignored. (Not part of N3's tested scope but worth
     knowing.)

5. **3 small follow-ups from N2 review** are batched in TASKS.md
   under "From 2026-06-02 N2 review":
   - H-2: same-second iat boundary inclusive
   - M-1: public TTL accessor on TokenService
   - M-3: leap-year-safe date construction in boundary test
   Each is 1-5 lines. A future agent (or you) could batch them as
   a single cleanup commit.
