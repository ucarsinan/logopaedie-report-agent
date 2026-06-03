# CURRENT.md — Current Working State

> **This file must be updated at the end of every meaningful AI session.**
> It represents the live state of the work — not a backlog, not a history.
> If it is out of date, the next agent will start from wrong assumptions.

---

## Last Updated

- **Date:** 2026-06-03 (morning — O-wave: Vercel production fix)
- **Updated by:** Claude Code
- **Session focus:** Diagnosed and fixed Vercel production backend
  (FUNCTION_INVOCATION_FAILED). Root causes uncovered and resolved
  in sequence: (1) TRUSTED_PROXY missing → added `vercel-edge`;
  (2) RATE_LIMIT_REDIS_URL missing → added `memory://`; (3) SERVICE_TOKEN,
  JWT_SECRET, SESSION_ENCRYPTION_KEY, PATIENT_ENCRYPTION_KEY all missing
  → generated and added; (4) `email-validator` not bundled by Vercel's
  experimentalServices vendoring despite being in requirements.txt →
  replaced `EmailStr` import from pydantic with a local `Annotated[str,
  AfterValidator(_check_email)]` type in `routers/auth.py`.
  Also fixed: SESSION_ENCRYPTION_KEY missing from `_set_env` autouse
  fixture in conftest.py (caused `test_429_response_includes_retry_after_header`
  to fail with lru_cache ordering change from N3). Fixed 3 pre-existing
  mypy errors in `alembic/versions/0010`/`0011` that were causing CI failure.
  **Vercel production is now fully operational:** `/api/livez` → 200,
  `/api/health` → 401 (correctly requires SERVICE_TOKEN), frontend → 200.
  **533 passed, 9 skipped** (unchanged — all fixes were infra/config).

---

## Current Goal

No agent-driven goal active. Vercel production is now fully operational.
MVP presentation is ready for next week.

Open from N2 review (small inline fixes when convenient — ~20min batch):
- **H-2** — `is_token_revoked` boundary `<` → `<=` for same-second inclusive
- **M-1** — public `access_ttl_seconds` accessor on `TokenService`
- **M-3** — leap-year-safe date construction in `test_derive_age_group_exactly_120_years_old_returns_erwachsen`

**M-6** (anamnesis completion logic) still blocked on owner-driven WIP.

---

## Current Branch

```text
main
```

Local `main` is in sync with `origin/main` at `5298d30`.

O-wave commits (newest first, all pushed):
- `5298d30` — `fix(backend): replace EmailStr with local Annotated type to remove email-validator dependency on Vercel`
- `0d34df8` — `fix(backend): use pydantic[email] extra to ensure email-validator is bundled on Vercel` (superseded by 5298d30)
- `742048b` — `chore: trigger redeploy with complete production env vars`
- `2bfc04e` — `chore: trigger redeploy after TRUSTED_PROXY env var added`
- `95a71fb` — `fix(backend): resolve mypy type errors in alembic migrations 0010/0011`
- `1c19ff2` — `fix(backend): add SESSION_ENCRYPTION_KEY to _set_env autouse fixture`

---

## Verification snapshot

- `ruff check .` → All checks passed!
- `mypy . --ignore-missing-imports` → **0 errors** (was 3 pre-existing in 0010/0011)
- `pytest -q` → **533 passed, 9 skipped**
- Vercel production: `/api/livez` → 200, `/api/health` → 401 (correct), frontend → 200

---

## Key things the next agent should know

1. **Vercel production env vars are all set** (added 2026-06-03):
   - `TRUSTED_PROXY=vercel-edge` — satisfies boot guard; rate limiter
     falls back to socket IP (Vercel edge IP = shared bucket, acceptable for MVP)
   - `RATE_LIMIT_REDIS_URL=memory://` — Vercel's experimentalServices
     bundler does NOT include `redis` package at runtime; in-memory
     fallback is intentional for this deployment
   - `SERVICE_TOKEN`, `JWT_SECRET`, `SESSION_ENCRYPTION_KEY`,
     `PATIENT_ENCRYPTION_KEY` — all newly generated random values

2. **`EmailStr` is no longer from pydantic.** `routers/auth.py` defines
   a local `EmailStr = Annotated[str, AfterValidator(_check_email)]` with
   a simple regex. Reason: Vercel's experimentalServices vendoring does NOT
   bundle `email_validator` even when listed in requirements.txt or
   specified as `pydantic[email]` extra. The local type is functionally
   equivalent for input validation.

3. **`mypy` is now fully clean** (0 errors on all 72 source files).
   The alembic 0010/0011 errors are fixed: 0011's set comprehensions
   filter `None` explicitly; 0010's `Column` type uses `TypeEngine[Any]`.

4. **`SESSION_ENCRYPTION_KEY` added to `_set_env` autouse fixture** in
   `conftest.py`. Root cause: `get_totp_service()` is `@lru_cache(maxsize=1)`
   — its first call initializes the singleton. With N3's test additions
   changing collection order, `test_429_response_includes_retry_after_header`
   was the first to trigger it before any other test set the env var.

5. **All N-wave key facts still apply** (see previous HANDOFF entry).
