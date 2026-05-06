# Patient Management — Phase 1 Design Spec

**Date:** 2026-05-06
**Status:** Approved
**Scope:** Phase 1 — Patient entity + session linking + management UI
**Out of scope:** Verordnungsverwaltung (Phase 2)

---

## Context

The app currently stores patient data only as an anonymous string (`pseudonym`) inside Redis session state. There is no persistent Patient entity, no cross-session history, and no linkage between reports of the same patient. This design introduces a full Patient entity as the central anchor for real-world clinical use.

DSGVO compliance is implemented technically (encryption, soft-delete, consent tracking). Legal compliance (AVV with Vercel/Neon/Upstash/Groq, Verarbeitungsverzeichnis, Datenschutzbeauftragter) is documented as a Production Readiness Checklist — outside the scope of this implementation.

---

## Architecture Decision

**Phased approach (Option C):**
- Phase 1: Patient entity + management UI + session linking
- Phase 2: Verordnung (Heilmittelverordnung) linked to Patient

**Session start: Patient-First with Demo fallback**
- Real use: Therapeutin selects patient before starting a session
- Demo mode: session starts without patient_id (existing flow preserved)

---

## Data Model

### New table: `patients`

```python
class Patient(SQLModel, table=True):
    __tablename__ = "patients"

    id: UUID                        # PK
    system_id: str                  # PAT-2026-0042, auto-generated, unique, indexed
    pseudonym: str                  # therapist-defined, defaults to system_id
    user_id: UUID                   # FK → users.id (owning therapist)

    # Encrypted fields (Fernet, same key infrastructure as session store)
    realname_enc: bytes
    birthdate_enc: bytes
    phone_enc: bytes | None
    email_enc: bytes | None
    insurance_nr_enc: bytes | None

    # Plaintext clinical fields
    gender: str | None
    age_group: str                  # kind | jugendlich | erwachsen
    icd10_codes: list[str]          # JSON
    disorder_text: str
    indikationsschluessel: str      # SP1–SP6, ST1–ST2, etc.

    # Administrative
    insurance_type: str | None      # GKV | PKV
    insurance_name: str | None
    guardian_name: str | None       # for children

    # DSGVO
    created_at: datetime
    deleted_at: datetime | None     # soft delete
```

**system_id generation:** `PAT-{YEAR}-{SEQUENCE:04d}` — global atomic DB sequence (not per-user), generated at creation. Guarantees uniqueness across all therapists in the application.

### New table: `consent_records`

```python
class ConsentRecord(SQLModel, table=True):
    __tablename__ = "consent_records"

    id: UUID
    patient_id: UUID                # FK → patients.id CASCADE DELETE
    consent_type: str               # data_processing | ai_processing | data_sharing
    granted: bool
    granted_at: datetime
    revoked_at: datetime | None
    recorded_by: UUID               # FK → users.id
```

### Modified: `ReportRecord`

Add nullable FK:
```python
patient_id: UUID | None = Field(default=None, sa_column=Column(GUID(), ForeignKey("patients.id", ondelete="SET NULL"), nullable=True))
```

`pseudonym` field is kept for backward compatibility but populated from Patient.pseudonym at report generation time.

### Modified: Session state (Redis)

`SessionInfo` schema extended:
```python
patient_id: str | None = None       # UUID as string
is_demo: bool = False
```

---

## Encryption Strategy

Reuse the existing `cryptography.fernet.Fernet` setup from `session_store.py`.

New `EncryptionService` in `backend/services/encryption_service.py`:
```python
class EncryptionService:
    def encrypt(self, value: str) -> bytes
    def decrypt(self, value: bytes) -> str
```

Key loaded from env var `PATIENT_ENCRYPTION_KEY` (separate from session Fernet key — different purpose, different rotation schedule).

**Searchability constraint:** Encrypted fields (realname, birthdate, phone, email, insurance_nr) cannot be searched via SQL. Search runs only on `pseudonym` and `system_id` (plaintext, indexed).

---

## API Endpoints

### New router: `backend/routers/patients.py`

| Method | Path | Description |
|--------|------|-------------|
| POST | `/patients` | Create patient, auto-generate system_id |
| GET | `/patients` | List (paginated) + search `?q=` on pseudonym/system_id |
| GET | `/patients/{id}` | Stammdaten, encrypted fields decrypted in response |
| PATCH | `/patients/{id}` | Update stammdaten or pseudonym (audit logged) |
| DELETE | `/patients/{id}` | Soft-delete: sets deleted_at (DSGVO deletion request) |
| GET | `/patients/{id}/history` | All reports + SOAP notes + therapy plans, chronological |
| GET | `/patients/{id}/progress` | Auto-compare last 2 reports via existing report_comparator |
| POST | `/patients/{id}/consent` | Record consent (type + granted bool) |

**Authorization:** All endpoints require authenticated user. Patients are scoped to `user_id` — a therapist only sees their own patients.

**Audit logging:** PATCH and DELETE write to existing `audit_log` table.

### Modified endpoints

**`POST /sessions`** — body extended:
```json
{ "patient_id": "uuid-or-null" }
```
- If `patient_id` provided: session linked, pseudonym pre-populated from Patient
- If omitted: `is_demo: true` in session state, greeting message includes demo indicator

**`POST /sessions/{id}/generate`** — report generation:
- Reads `patient_id` from session state
- Writes `patient_id` to `ReportRecord`
- Populates `pseudonym` from `Patient.pseudonym` (not from chat-collected data)

**`GET /reports`** — new filter: `?patient_id=`

---

## Frontend Structure

### New feature module: `frontend/src/features/patients/`

| File | Purpose |
|------|---------|
| `PatientList.tsx` | Paginated list with search, "Neuer Patient" button |
| `PatientForm.tsx` | Create/edit form — all fields, encrypted fields handled client-side display |
| `PatientDetail.tsx` | Detail page: stammdaten + ProgressSnapshot + history |
| `PatientHistory.tsx` | Chronological list of all reports/SOAP/plans |
| `ConsentManager.tsx` | Record/revoke 3 consent types with timestamps |

### New feature module: `frontend/src/features/patient-progress/`

| File | Purpose |
|------|---------|
| `ProgressSnapshot.tsx` | Calls `/patients/{id}/progress`, renders ComparisonResult summary inline on detail page |

### Modified: `frontend/src/features/chat/`

New `PatientSelector.tsx` — modal dialog shown before session start:
- Search/select existing patient
- "Neu anlegen" → opens PatientForm in modal
- "Demo-Modus" link → skips patient selection

### Navigation

Add "Patienten" as primary nav item (first position). Existing nav items shift down.

### New routes

| Route | Component |
|-------|-----------|
| `/patients` | PatientList |
| `/patients/new` | PatientForm (create) |
| `/patients/[id]` | PatientDetail |
| `/patients/[id]/edit` | PatientForm (edit) |

---

## DSGVO Implementation

| Requirement | Implementation |
|-------------|---------------|
| Verschlüsselung besonderer Kategorien | Fernet encryption on realname, birthdate, contact, insurance_nr |
| Recht auf Löschung | `DELETE /patients/{id}` → soft-delete; hard-delete after retention period (manual or cron) |
| Zweckbindung | Consent per purpose (data_processing, ai_processing, data_sharing) |
| Transparenz | `ConsentManager.tsx` shows granted/revoked history |
| Datensparsamkeit | Search only on non-sensitive fields; encrypted fields never in query predicates |

### Production Readiness Checklist (not in scope)

- [ ] AVV mit Vercel (EU-Region erzwingen)
- [ ] AVV mit Neon PostgreSQL
- [ ] AVV mit Upstash Redis
- [ ] AVV oder EU-Alternative für Groq (kein AVV verfügbar → Mistral EU / Azure OpenAI EU)
- [ ] Verarbeitungsverzeichnis nach Art. 30 DSGVO
- [ ] Datenschutzbeauftragter ab 20 Personen mit regelmäßiger Verarbeitung
- [ ] Schriftliche Patienteneinwilligung (Papierformular + ConsentRecord verknüpfen)
- [ ] Aufbewahrungsfristen: 10 Jahre GKV-Unterlagen → Retention-Policy in DB

---

## Migration Strategy

1. Add `patients`, `consent_records` tables (new columns only)
2. Add nullable `patient_id` FK to `reports` — no data migration needed (existing reports stay unlinked)
3. Add `patient_id` + `is_demo` to `SessionInfo` Pydantic model (optional fields, backward-compatible)
4. Add `PATIENT_ENCRYPTION_KEY` to env vars

No breaking changes to existing data or API contracts.

---

## Out of Scope (Phase 2)

- Heilmittelverordnung table (`verordnung_id` FK on Session)
- Rezeptnummer, Heilmittelpositionsnummer, verordnete Einheiten
- Verordnungs-UI + workflow
