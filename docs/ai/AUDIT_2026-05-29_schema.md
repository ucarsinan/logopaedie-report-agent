# Schema-vs-Migrations Audit — 2026-05-29

> Static audit produced by a parallel sub-agent on 2026-05-29 after the
> `therapyplanrecord.user_id` production 500 (see `HANDOFF.md`). Read-only
> pass over `backend/models/*.py` vs. `backend/alembic/versions/0001..0011`.
> Goal: find the next instance of the same drift class **before** it bites
> in production traffic.

## Tables audited

| Table | Model file | Migrations touching it |
|---|---|---|
| `reports` | `backend/models/report_record.py` | 0001 (create), 0005 (+user_id), 0007 (+patient_id), 0008 (patient_id type fix), 0011 (composite indexes) |
| `users` | `backend/models/auth.py` | 0002 (create), 0004 (+last_totp_step) |
| `user_sessions` | `backend/models/auth.py` | 0002 (create), 0003 (+rotated) |
| `email_tokens` | `backend/models/auth.py` | 0002 (create) |
| `audit_log` | `backend/models/auth.py` | 0002 (create) |
| `patients` | `backend/models/patient.py` | 0007 (create), 0011 (composite index) |
| `consent_records` | `backend/models/patient.py` | 0007 (create) |
| `soaprecord` | `backend/models/soap_record.py` | 0006 (create + user_id), 0009 (user_id type fix) |
| `therapyplanrecord` | `backend/models/therapy_plan_record.py` | 0010 (create + user_id), 0011 (composite index) |

## Forward drift — model has it, migrations don't ← URGENT class

**No missing columns found.** After `0010_therapy_plan_user_id` landed, every
column declared on every `table=True` model has a corresponding column added by
some migration in the 0001→0011 chain. The original bug class is closed at the
migration level.

What is still drifted are sub-column attributes — declared FKs, declared
indexes, and type encodings. These are listed under their own section below
because they will not 500 a fresh `INSERT`, but they will silently change
behavior and were created by the same `create_all`-vs-alembic split that
produced the original incident.

### `patients.pseudonym` index (declared on model, never created by a migration)

- Model: `backend/models/patient.py:22` — `pseudonym: str = Field(index=True)`
- Migration 0007 creates `ix_patients_user_id` and `ix_patients_system_id`
  (unique) but no `ix_patients_pseudonym`. `create_all` would have created it
  on a fresh DB but live Neon migrated up from 0007 will not have it.
- Not urgent — query will work, just slower. Listed here because it's the same
  drift pattern (model declares, migration doesn't replay).

Proposed migration sketch (do NOT save yet — owner decision):

```python
# backend/alembic/versions/0012_patients_pseudonym_index.py
revision = "0012_patients_pseudonym_index"
down_revision = "0011_hot_query_indexes"

def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "patients" in inspector.get_table_names():
        existing = {ix["name"] for ix in inspector.get_indexes("patients")}
        if "ix_patients_pseudonym" not in existing:
            op.create_index("ix_patients_pseudonym", "patients", ["pseudonym"])

def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "patients" not in inspector.get_table_names():
        return
    if "ix_patients_pseudonym" in {ix["name"] for ix in inspector.get_indexes("patients")}:
        op.drop_index("ix_patients_pseudonym", table_name="patients")
```

**Resolved by model-declaration drop (2026-05-29).** Audit of the live query
call sites (`routers/patients.py:113`, `routers/reports.py:57`,
`services/patient_service.py`) showed every read of `pseudonym` is either
scoped by `user_id` (so the composite `idx_patients_user_active` from 0011
covers it) or uses `ILIKE '%q%'` (a leading-wildcard search that no plain
B-tree index can serve — a trigram index would be required). The
`index=True` was dead intent. Dropped from `backend/models/patient.py`;
removed from `_MIGRATION_ONLY_INDEXES` in `backend/alembic/env.py`. Guarded
by `test_patient_pseudonym_has_no_standalone_index` in
`backend/tests/test_patient_model.py`. No 0013 migration written.

## Reverse drift — migration has it, model doesn't

None found. Every column added by 0001–0011 is still declared on its
corresponding model.

## Type / nullability / FK / index mismatches

### URGENT-ish — missing FK constraints (Neon does NOT enforce these even though models declare them)

The model declares the constraint, the migration created the column without
it, and the FK has never been added in a later migration. On Neon this means
a user delete will not cascade through these tables, and orphan rows are
possible. Local dev (`create_all`) does have the constraint because SQLModel
emits it from the model, so this is a **dev/prod schema split**.

| Table.column | Model declares | Migration created | Status on Neon |
|---|---|---|---|
| `reports.user_id` | FK → `users.id` ON DELETE CASCADE | 0005: column only, no FK | **No FK on live DB** |
| `reports.patient_id` | FK → `patients.id` ON DELETE SET NULL | 0007: column only, no FK; 0008: type fix only | **No FK on live DB** |
| `soaprecord.user_id` | FK → `users.id` ON DELETE CASCADE | 0006: column only; 0009: type fix only | **No FK on live DB** |
| `patients.user_id` | FK → `users.id` ON DELETE CASCADE | 0007: column only | **No FK on live DB** |
| `consent_records.patient_id` | FK → `patients.id` ON DELETE CASCADE | 0007: column only | **No FK on live DB** |
| `consent_records.recorded_by` | FK → `users.id` ON DELETE RESTRICT | 0007: column only | **No FK on live DB** |
| `therapyplanrecord.user_id` | FK → `users.id` ON DELETE CASCADE | 0010: column only — but the 2026-05-29 manual hotfix on Neon ADDED the FK | **Has FK on Neon, NOT in alembic** |
| `therapyplanrecord.report_id` | `foreign_key="reports.id"` (no `ondelete`) | 0010: column + FK declared inline | OK in migration; `ondelete` unspecified |

The `therapyplanrecord.user_id` row is the most insidious: a fresh environment
running migrations from scratch would NOT recreate the hotfix Neon was given.
A second `0012_*` should formalize that hotfix as alembic.

Proposed consolidating migration sketch (do NOT save yet — owner decision):
**Applied as `backend/alembic/versions/0012_align_declared_fks.py` (2026-05-29).**

```python
# backend/alembic/versions/0012_align_declared_fks.py
revision = "0012_align_declared_fks"
down_revision = "0011_hot_query_indexes"

def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    def _fks(table: str) -> set[tuple[str, str]]:
        if table not in inspector.get_table_names():
            return set()
        return {
            (tuple(fk["constrained_columns"])[0], fk["referred_table"])
            for fk in inspector.get_foreign_keys(table)
        }

    if "reports" in inspector.get_table_names():
        fks = _fks("reports")
        if ("user_id", "users") not in fks:
            with op.batch_alter_table("reports") as b:
                b.create_foreign_key(
                    "fk_reports_user_id_users", "users",
                    ["user_id"], ["id"], ondelete="CASCADE",
                )
        if ("patient_id", "patients") not in fks:
            with op.batch_alter_table("reports") as b:
                b.create_foreign_key(
                    "fk_reports_patient_id_patients", "patients",
                    ["patient_id"], ["id"], ondelete="SET NULL",
                )

    if "soaprecord" in inspector.get_table_names() and ("user_id", "users") not in _fks("soaprecord"):
        with op.batch_alter_table("soaprecord") as b:
            b.create_foreign_key(
                "fk_soaprecord_user_id_users", "users",
                ["user_id"], ["id"], ondelete="CASCADE",
            )

    if "patients" in inspector.get_table_names() and ("user_id", "users") not in _fks("patients"):
        with op.batch_alter_table("patients") as b:
            b.create_foreign_key(
                "fk_patients_user_id_users", "users",
                ["user_id"], ["id"], ondelete="CASCADE",
            )

    if "consent_records" in inspector.get_table_names():
        fks = _fks("consent_records")
        if ("patient_id", "patients") not in fks:
            with op.batch_alter_table("consent_records") as b:
                b.create_foreign_key(
                    "fk_consent_records_patient_id_patients", "patients",
                    ["patient_id"], ["id"], ondelete="CASCADE",
                )
        if ("recorded_by", "users") not in fks:
            with op.batch_alter_table("consent_records") as b:
                b.create_foreign_key(
                    "fk_consent_records_recorded_by_users", "users",
                    ["recorded_by"], ["id"], ondelete="RESTRICT",
                )

    if "therapyplanrecord" in inspector.get_table_names() and ("user_id", "users") not in _fks("therapyplanrecord"):
        with op.batch_alter_table("therapyplanrecord") as b:
            b.create_foreign_key(
                "fk_therapyplanrecord_user_id_users", "users",
                ["user_id"], ["id"], ondelete="CASCADE",
            )

def downgrade() -> None:
    # Drop only what we created; idempotent against unknown environments.
    for table, name in [
        ("therapyplanrecord", "fk_therapyplanrecord_user_id_users"),
        ("consent_records", "fk_consent_records_recorded_by_users"),
        ("consent_records", "fk_consent_records_patient_id_patients"),
        ("patients", "fk_patients_user_id_users"),
        ("soaprecord", "fk_soaprecord_user_id_users"),
        ("reports", "fk_reports_patient_id_patients"),
        ("reports", "fk_reports_user_id_users"),
    ]:
        with op.batch_alter_table(table) as b:
            try:
                b.drop_constraint(name, type_="foreignkey")
            except Exception:
                pass
```

### Type encoding drift — VARCHAR(36) in migration vs. native UUID via GUID in model (Postgres only)

The model uses the `GUID` `TypeDecorator` (UUID on Postgres, CHAR(36) on
SQLite). Migrations 0008 and 0009 only fixed two specific tables
(`reports.patient_id`, `soaprecord.user_id`). The following columns are still
VARCHAR(36) on Neon despite the model declaring UUID:

- `reports.user_id` — added VARCHAR(36) in 0005, never converted.
- `patients.id` (PK) and `patients.user_id` — created VARCHAR(36) in 0007,
  never converted.
- `consent_records.id`, `consent_records.patient_id`, `consent_records.recorded_by`
  — created VARCHAR(36) in 0007, never converted.
- `users.id`, `user_sessions.id`, `user_sessions.user_id`, `email_tokens.id`,
  `email_tokens.user_id`, `audit_log.id`, `audit_log.user_id` — all VARCHAR(36)
  in 0002, never converted.

> `audit_log.id` converted as 0013 (2026-05-29). Picked first because no other
> table has an incoming FK on `audit_log.id`, so the type swap doesn't cascade.
> The remaining 12 columns still need their own coordinated migrations.
> `email_tokens.id` converted as 0014 (2026-05-31) — same rationale: no incoming FK. 11 columns remain.
> `user_sessions.id` converted as 0015 (2026-05-31) — leaf PK, no incoming FKs (confirmed by grep against models + alembic versions). 10 remain.
> `consent_records.id` converted as 0016 (2026-05-31) — same rationale: no incoming FKs. 9 remain.
> **users.id cluster converted as 0017 (2026-05-31).** Coordinated drop/ALTER/recreate
> across PK + 6 declared FKs (`user_sessions.user_id`, `email_tokens.user_id`,
> `audit_log.user_id`, `patients.user_id`, `reports.user_id`,
> `consent_records.recorded_by`). FK names discovered via `inspector.get_foreign_keys()`
> for idempotency. **Drift caught in the process:** `0002_auth_tables.py` declared
> 3 FKs inline at table-creation **without explicit names** (`user_sessions.user_id`,
> `email_tokens.user_id`, `audit_log.user_id` — see `0002_auth_tables.py:41,56,68`),
> so Postgres assigned them server-default `<table>_<col>_fkey` names. 0017 renames
> them to the canonical `fk_<table>_<col>_users` convention during the recreate.
> Grep confirmed nothing in the codebase pins on the old names. 2 columns remain.
> **patients.id cluster converted as 0018 (2026-05-31).** Coordinated drop/ALTER/recreate
> across PK + `consent_records.patient_id`. **Design call:** `reports.patient_id`
> was already UUID (0008), but Postgres refuses to `ALTER TYPE` a referenced PK
> column while any dependent FK exists — even when the referencing column type
> already matches. 0018 therefore drops + recreates `fk_reports_patient_id_patients`
> alongside the consent FK so the PK swap can go through. Not empirically tested
> on Postgres (test path skipped pending Postgres CI) — verify on first live
> deploy. **0 columns remain — drift class fully closed end-to-end.**

This is low severity (SQLAlchemy's UUID/text implicit casts make INSERTs work)
but it is a real divergence and it's why the GUID TypeDecorator exists.
Recommend handling in a separate `0013_*` after the FK alignment lands,
mirroring the 0008/0009 conditional pattern (`if dialect == "postgresql" and
column is VARCHAR: ALTER ... USING ...::uuid`).

### Nullability / length annotation drift (low severity)

- `users.role` — model: `sa_type=String(50)`; migration: `sa.String()`
  (unlimited TEXT on PG). Cosmetic.
- `email_tokens.purpose` — same drift.
- `patients.gender`, `patients.age_group`, `patients.indikationsschluessel`,
  `patients.insurance_type`, `consent_records.consent_type` — all have
  `String(N)` length caps in the model, all created as unlimited `sa.String()`
  in migration 0007. No functional risk, but `inspect_db` and any future
  autogenerate will keep flagging them as diffs.

## Clean tables

- `users` — column set matches; only the cosmetic `role` length annotation
  drift noted above.
- `user_sessions` — column set matches; no FK/index drift; only the global
  type-encoding drift noted above.
- `email_tokens` — same status: column set matches; cosmetic `purpose` length
  drift.
- `audit_log` — column set matches; no FK/index drift beyond global type
  encoding.

No `forward drift` columns on any table. The audit closes that bug class for
now.

## Recommendation

**URGENT (production-behavior risk):** there is no longer a missing-column
drift — that bug class was closed when 0010 landed. The remaining production
risk is the **missing FK constraints**, especially `therapyplanrecord.user_id →
users.id ON DELETE CASCADE`. Today's hotfix put that FK on Neon by hand, so
prod is consistent right now, but it lives only in the Neon DB — not in
alembic — and a fresh prod environment built from migrations alone would not
recreate it. A second, identical incident is structurally possible the next
time the column-vs-FK split shows up. Fix by landing the
`0012_align_declared_fks` migration sketched above; the conditional inspector
pattern means it's a no-op on Neon (already has the therapyplanrecord FK) and
additive everywhere else.

**LOW:** the VARCHAR(36)-vs-UUID type drift across the
`users`/`user_sessions`/`email_tokens`/`audit_log`/`patients`/`consent_records`
PK/FK columns, the missing `ix_patients_pseudonym` index, and the `String(N)`
length annotations. None of these will 500 an INSERT; they are mostly noise
that will keep showing up if autogenerate is ever turned on.

**CI guard — yes, adopt `alembic check`.** It's the structural fix for "next
add-a-column-to-an-existing-table will silently drift again." It runs
autogenerate against an empty test DB seeded by the current migrations and
fails the build if the resulting metadata diff is non-empty. Slot into
`.github/workflows/ci.yml` as a new step in `backend-test` (or as its own tiny
job), right after dependencies install:

```yaml
- name: Verify alembic migrations match models
  working-directory: backend
  env:
    DATABASE_URL: sqlite:///./ci_check.db
  run: |
    alembic upgrade head
    alembic check  # fails if metadata diverges from migrations
```

That single step would have caught the 2026-05-29 incident at PR time and
would catch every future variant before it ships.
