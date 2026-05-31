# CURRENT.md — Current Working State

> **This file must be updated at the end of every meaningful AI session.**
> It represents the live state of the work — not a backlog, not a history.
> If it is out of date, the next agent will start from wrong assumptions.

---

## Last Updated

- **Date:** 2026-05-31 (evening — H-wave)
- **Updated by:** Claude Code
- **Session focus:** H-wave closed out the remaining 9 VARCHAR(36)→UUID
  columns from A3's audit. Three parallel sub-agents (H1/H2/F2) in
  worktree isolation: H1 landed `0017_users_id_uuid_cluster` (PK + 6
  declared FKs), H2 landed `0018_patients_id_uuid_cluster` (PK +
  `consent_records.patient_id`), F2 sprinkled explicit
  `@pytest.mark.asyncio` markers across 19 bare async tests in 3 files.
  Followup mypy cleanup on 0018's sandboxed-versions helper (one
  `Operations` import fix). **Type-encoding drift class is now closed
  end-to-end.**

---

## Current Goal

No agent-driven goal active. The H-wave closed the last open follow-ups
from A3's schema audit (VARCHAR(36)→UUID across 13 columns; 9 done this
round, 4 in earlier waves) and the E3-review F2 marker drift.

**M-6** (anamnesis completion logic) remains the outstanding audit item
and is still blocked on owner-driven WIP in
`backend/services/anamnesis_engine.py`, `phonological_analyzer.py`, and
`anamnesis_catalog.py`. Treat them as untouchable until the owner
explicitly hands them over.

Remaining low-priority items in TASKS.md "Next":

- Drop redundant single-column `ix_*_user_id` indexes (needs live Neon
  EXPLAIN to confirm composite indexes from 0011 are picked — not
  agent-safe; owner decision)
- Pre-existing Vercel preview deploy failure (out of scope)

---

## Current Branch

```text
main
```

Local `main` is **4 ahead of `origin/main`** (H-wave + mypy fix). About
to push: `b5bca62` + `a557a4f` + `b24d6ee` + `0833506` + this docs
commit.

Today's H-wave commits (newest first):

- `0833506` — `fix(tests): import Operations explicitly in 0018 sandboxed-versions test`
- `b24d6ee` — `feat(backend): land 0018_patients_id_uuid_cluster migration`
- `a557a4f` — `feat(backend): land 0017_users_id_uuid_cluster migration`
- `b5bca62` — `test(backend): add explicit @pytest.mark.asyncio markers (F2)`
- `a30c7f4` — `docs(ai): record G-wave (0014/0015/0016 leaf-PK UUID migrations)`
- `aadea60` — `feat(backend): land 0016_consent_records_id_uuid_type migration`
- `559ed9f` — `feat(backend): land 0015_user_sessions_id_uuid_type migration`
- `facf364` — `feat(backend): land 0014_email_tokens_id_uuid_type migration`
- `6d0d417` — `docs(ai): record E1/E2/E3 + F1 fifth-wave batch and pre-push gotcha`

---

## Verification snapshot (pre-push)

- `ruff check .` → All checks passed!
- `mypy <H-wave files>` → Success: no issues found in 4 source files
- `DATABASE_URL=sqlite:///./ci_check.db alembic upgrade head` → 0001→0018 clean
- `alembic check` → "No new upgrade operations detected"
- `alembic downgrade base` → full chain reverses cleanly
- `pytest -q` → **448 passed, 9 skipped** (was 440+4 after G-wave; +3 H1
  SQLite + +5 H2 SQLite passes; +2 H1 Postgres + +3 H2 Postgres skips)

---

## Key things the next agent should know

1. **H1's drift finding (worth recording in `docs/ai/AUDIT_2026-05-29_schema.md`):**
   `0002_auth_tables.py` creates the 3 FKs on
   `user_sessions.user_id` / `email_tokens.user_id` / `audit_log.user_id`
   **inline at table-creation, without explicit names**. Postgres gives
   them server-default names (`*_fkey`). 0017 discovers the live names
   via `inspector.get_foreign_keys()` and **renames them to canonical
   `fk_<table>_<col>_users`** during the recreate step. Nothing in the
   codebase pins on the old auto-generated names (grep confirmed), so
   the rename is safe.

2. **H2's design choice on `fk_reports_patient_id_patients`:** Postgres
   refuses to `ALTER TYPE` a referenced PK column while ANY dependent FK
   exists, even when the referencing column's type already matches.
   `reports.patient_id` was already UUID (0008), but 0018 still drops +
   recreates `fk_reports_patient_id_patients` so Postgres lets the PK
   swap through. The recreate uses the canonical name and `ON DELETE
   SET NULL` from 0012. **This was a deliberate design call, not
   empirically tested on Postgres** (test path skipped pending Postgres
   CI) — verify on first live deploy of 0018.

3. **H2's worktree had a sandbox-versions test fixture** because it was
   forked before 0017 existed. The fixture (in
   `backend/tests/test_migration_0018.py`) copies 0001..0016 into a temp
   dir and runs the alembic chain there. Now that 0017 is merged, the
   sandbox is functionally unnecessary but harmless — it still works,
   and removing it would mean rewriting the test to use the real
   `versions/` dir. Leave as-is unless someone is in there for another
   reason.

4. **F2 added `import pytest` to `test_email_service.py`** — that was
   the only file with bare `async def test_*` that didn't already
   import pytest. The other touched files (`test_audit_service.py`,
   `test_auth_service.py`) already had it.
