# CURRENT.md — Current Working State

> **This file must be updated at the end of every meaningful AI session.**
> It represents the live state of the work — not a backlog, not a history.
> If it is out of date, the next agent will start from wrong assumptions.

---

## Last Updated

- **Date:** 2026-06-02 (morning — M-wave)
- **Updated by:** Claude Code
- **Session focus:** M-wave (3 parallel agents) closed every remaining
  actionable L-wave / L3-review item. **M1** retried S-7 successfully
  (L1 had died on network mid-implementation last time): per-user
  Redis revocation cutoff via `iat`-claim comparison, no jti needed.
  **M2** replaced 3 bare `assert self.totp is not None` guards with
  `if/raise RuntimeError` (matches J1's S-4 pattern) and consolidated
  3 K1 tests onto K3's `deps_with_2fa` fixture. **M3** added a
  `[0, 120]` years plausibility guard to `derive_age_group` (clinical
  misclassification risk for future / pre-1906 DOBs) and documented
  the `_audit` RuntimeError → HTTP 500 and `Retry-After`
  bucket-window semantics. All three auto-merged cleanly.

---

## Current Goal

No agent-driven goal active. The full audit-cycle started by I1–I3
on 2026-06-01 is now closed end-to-end:

- I1 critical (0017 missing FK drops) — fixed `bf04e8b`
- I1 H-1 frontend type — fixed `b39c72b` (L-wave)
- I1 H-2 `.env.example` for `TRUSTED_PROXY` — still blocked by env-file
  permission denylist (manual operator addition needed)
- I1 M-1/M-2 docstring notes — added `c4890f0` (M3)
- I1 M-3 `derive_age_group` clinical guard — fixed `c4890f0` (M3)
- I1 L-1 fixture consolidation — fixed `0c1f9b0` (M2)
- I1 L-2 bare-assert hardening — fixed `0c1f9b0` (M2; one compound
  assert still in `login_2fa:755`, deferred)
- I3 S-1/S-2/S-3/S-4/S-5/S-6 — fixed in J/K waves
- I3 S-7 — fixed `7636d9f` (M1)
- I3 S-8 — accepted trade-off (informational, scope confined to
  `user.id`)
- I3 P-1/P-3/P-5 + Retry-After + headers_enabled (partial) — fixed
  in K-wave
- I2 deferred (test gaps) — closed in J3 + K3

**M-6** (anamnesis completion logic) remains the outstanding audit
item and is still blocked on owner-driven WIP in
`backend/services/anamnesis_engine.py`, `phonological_analyzer.py`,
and `anamnesis_catalog.py`. Treat as untouchable until the owner
explicitly hands them over.

What remains in TASKS.md "Next" (all non-agent-actionable):

- Drop redundant single-column `ix_*_user_id` indexes — needs Neon
  EXPLAIN, owner-decision.
- Vercel preview deploy — pre-existing config issue.
- `TRUSTED_PROXY` deploy-env audit — operator-side.
- X-RateLimit-* response headers — requires slowapi version bump or
  per-route refactor (L2's broad `headers_enabled=True` broke 85
  tests; deferred).
- `assert self.totp is not None and self.challenges is not None` on
  `login_2fa:755` — same class as M2's fix; out of M2's named
  scope.

---

## Current Branch

```text
main
```

Local `main` is **3 ahead of `origin/main`** (M-wave + this docs
commit). About to push: `7636d9f` + `0c1f9b0` + `c4890f0` + this
docs commit.

Today's M-wave commits (newest first):

- `c4890f0` — `fix(backend): derive_age_group guards pathological DOB ranges + M-1/M-2 docstring notes (L3 follow-ups)`
- `0c1f9b0` — `refactor(backend): RuntimeError for missing TOTPService + consolidate 2FA test fixture (L3 L-1+L-2)`
- `7636d9f` — `feat(backend): access-token revocation on password change (S-7)`
- `74c3cfc` — `docs(ai): record L-wave (partial — 2 agents crashed on socket close)` (yesterday)

---

## Verification snapshot (pre-push)

- `ruff check .` → All checks passed!
- `mypy <6 M-wave files>` → Success: no issues found in 6 source files
- `pytest -q` → **522 passed, 9 skipped** (was 510+9; +10 M1 + 0 M2
  refactor + +2 M3 boundary)
- All three commits auto-merged without conflict markers — agents
  stayed in disjoint code regions exactly as planned.

---

## Key things the next agent should know

1. **`AccessTokenBlocklist` (S-7) lives at
   `backend/services/access_token_blocklist.py`.** Singleton wired in
   `dependencies.py` via `@lru_cache get_access_token_blocklist()` —
   reuses the existing `redis_client.get_redis()` and reads
   `TokenService._access_ttl` directly (private access; could grow a
   public accessor later if the friction matters). API surface:
   - `revoke_all_for_user(user_id: str) -> None` — SETEX cutoff
   - `is_token_revoked(user_id: str, token_iat: int) -> bool` — GET
     cutoff, compare, fail-open on Redis errors

2. **Middleware check is in `backend/middleware/auth.py`** after the
   `payload["type"] == "access"` gate. Lazy import of
   `dependencies.get_access_token_blocklist` to avoid pulling Redis
   into module-load time. Revoked tokens fall through to the
   anonymous path (same as non-`access` types) — the middleware
   contract of never raising is preserved; downstream `get_current_user`
   produces the 401 naturally.

3. **`change_password` is the only writer to the blocklist so far.**
   S-7's scope was deliberately limited to that one path. If
   `disable_2fa` / `enable_2fa` / `confirm_password_reset` ever need
   the same semantic, the integration is a one-line
   `self._access_token_blocklist.revoke_all_for_user(...)` after the
   existing session revoke.

4. **`derive_age_group` returns `None` for OOR dates.** Range is
   `[today, today - 120 years]`. The sole caller
   (`PatientService.create_patient` at `patient_service.py:81`)
   already had an `or age_group` fallback, so no caller updates were
   needed. The new behavior is documented in the function's
   docstring; the K3 contract-pin tests were renamed from
   `*_returns_kind` / `*_returns_erwachsen` to `*_returns_none`.

5. **`assert self.totp is not None` → `if/raise RuntimeError`** in
   `start_2fa_setup`, `enable_2fa`, `disable_2fa`. Message style
   matches J1's S-4 fix on `_audit`. **One compound assert remains
   in `login_2fa:755`** (`self.totp is not None and self.challenges
   is not None`) — M2 noted it but it was out of named scope. A
   future hygiene pass should convert it (likely needs to split into
   two `if/raise`s for clearer error messages).

6. **Three K1 P-3 tests now use K3's `deps_with_2fa` fixture.**
   `test_start_2fa_setup_emits_audit_event`,
   `test_enable_2fa_bulk_revokes_other_sessions_keeps_current`,
   `test_enable_2fa_without_current_hash_revokes_all`. Dropped the
   inline `monkeypatch.setenv("SESSION_ENCRYPTION_KEY", ...)` +
   `svc.totp = TOTPService()` boilerplate.

7. **`_audit` docstring now documents that the RuntimeError → HTTP
   500.** The intentional fail-loud trade-off (request crashes, audit
   row lost) was implicit before — now explicit in the docstring.

8. **`rate_limit_exceeded_handler` comment now documents the
   `Retry-After` bucket-window semantic.** slowapi 0.1.9 exposes only
   the fixed-window length (e.g., 60s for `30/minute`), not
   time-to-next-slot. Client backoff will be conservative-correct.

9. **`backend/.env.example` still missing `TRUSTED_PROXY` entry**
   (denylisted from agent writes). Operator should add manually
   before the next production deploy or accept the safe-but-collapsed
   per-instance rate-limit bucketing.
