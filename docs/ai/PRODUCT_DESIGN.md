# Logopädie-Praxis — Produktdesign & Baustein 1 Spec

**Datum:** 2026-05-10
**Typ:** Produktvision + technische Spec (Baustein 1)
**Status:** Approved — bereit für Implementierungsplan
**Basis-Projekt:** `logopaedie-report-agent` (bleibt Portfolio-Demo, unverändet)
**Neues Projekt:** `logopaedie-praxis` (echtes Produkt, separates Repo)

---

## 1. Produktvision

Ein AI-First Praxismanagementsystem für Logopädie-Praxen in Deutschland.

**Kernpositionierung:** Einziges Praxisprogramm, das AI-gestützte Dokumentation (Berichte, SOAP, Therapiepläne) nativ integriert — kein nachträglicher AI-Aufsatz, sondern AI als primärer Workflow.

**Zielgruppe:** Kleine bis mittlere Logopädie-Praxen (1–10 Therapeuten), Deutschland, DSGVO-Umgebung.

**Differenzierung gegenüber Theorg/Clinaro:**
- AI-Bericht aus Audio-Aufnahme in <60 Sekunden
- Therapieverlaufsanalyse über alle Sessions automatisch
- Moderne Weboberfläche (kein Windows-Desktop-Client von 2005)

---

## 2. Produkt-Roadmap (alle Bausteine)

```
Phase 5: Externe Integrationen (TI, KIM, ePA)         ← optional, später
Phase 4: Abrechnung GKV/PKV                            ← via Dienstleister-API
Phase 3: Praxismanagement (Termine, Multi-User, RBAC)  ← nach Phase 1+2
Phase 2: AI-Dokumentation mit Patientenbezug           ← portiert + verknüpft
Phase 1: Fundament — DSGVO + Patientenverwaltung       ← DIESE SPEC
```

**Dependency-Regel:** Jede Phase setzt alle darunter voraus.

---

## 3. Architektur (neues Repo: `logopaedie-praxis`)

### Stack

| Schicht | Technologie | Begründung |
|---|---|---|
| Frontend | Next.js 16, React 19, Tailwind CSS v4, TypeScript | Gleicher Stack wie Demo-Projekt |
| Auth | Supabase Auth | MFA, Rollen via JWT-Claims, sofort einsatzbereit |
| Datenbank | Supabase PostgreSQL (Region: eu-central-1 Frankfurt) | DSGVO-konform, EU-Hosting |
| Mandantenisolation | PostgreSQL Row-Level Security (RLS) | Automatische Datentrennung pro Praxis |
| Datei-Storage | Supabase Storage (EU) | Audio, PDFs, Uploads — verschlüsselt |
| AI-Service | FastAPI + Groq (Whisper + Llama) | Portiert aus `logopaedie-report-agent` |
| Hosting | Vercel (Monorepo via vercel.json) | Wie bisher |
| CI | GitHub Actions | Gleiche Struktur wie Demo-Projekt |

### Repo-Struktur

```
logopaedie-praxis/
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── (auth)/
│   │   │   │   ├── login/
│   │   │   │   └── register/
│   │   │   └── (praxis)/          ← auth-geschützter Bereich
│   │   │       ├── dashboard/
│   │   │       ├── patienten/
│   │   │       │   ├── page.tsx   ← Patientenliste
│   │   │       │   ├── [id]/      ← Patientenakte
│   │   │       │   └── neu/       ← Patient anlegen
│   │   │       └── einstellungen/
│   │   ├── features/
│   │   │   ├── patients/
│   │   │   ├── auth/
│   │   │   ├── documents/         ← AI-Docs (portiert)
│   │   │   └── ...
│   │   └── lib/
│   │       ├── supabase/
│   │       │   ├── client.ts      ← Browser-Client
│   │       │   └── server.ts      ← Server-Component-Client
│   │       └── api.ts             ← FastAPI AI-Client
├── backend/                       ← FastAPI, NUR AI-Logik
│   ├── main.py
│   ├── routers/
│   │   ├── sessions.py            ← AI-Session (Groq)
│   │   ├── reports.py
│   │   └── analysis.py
│   └── services/                  ← portiert aus logopaedie-report-agent
├── supabase/
│   └── migrations/
│       ├── 001_praxen.sql
│       ├── 002_profiles.sql
│       ├── 003_patients.sql
│       ├── 004_clinical.sql
│       └── 005_audit.sql
└── vercel.json
```

### Datenfluß

```
Browser
  → Next.js Server Component
    → Supabase (Auth + DB, direkt via SDK, RLS greift automatisch)
    → FastAPI (nur für AI-Operationen: Audio → Transkript → Bericht)
      → Groq API
```

FastAPI hat **keinen** direkten Datenbankzugriff — AI-Ergebnisse werden vom Next.js Server zurück zu Supabase geschrieben.

---

## 4. Datenmodell (Baustein 1)

### Tabellen

```sql
-- Mandant: eine Logopädie-Praxis
CREATE TABLE praxen (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name        TEXT NOT NULL,
  address     TEXT,
  phone       TEXT,
  email       TEXT,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Benutzerprofil (erweitert Supabase auth.users)
CREATE TABLE profiles (
  id          UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  praxis_id   UUID NOT NULL REFERENCES praxen(id),
  role        TEXT NOT NULL CHECK (role IN ('admin', 'therapeut', 'rezeption')),
  first_name  TEXT NOT NULL,
  last_name   TEXT NOT NULL,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Patient
CREATE TABLE patients (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  praxis_id           UUID NOT NULL REFERENCES praxen(id),

  -- Stammdaten
  first_name          TEXT NOT NULL,
  last_name           TEXT NOT NULL,
  date_of_birth       DATE NOT NULL,
  gender              TEXT CHECK (gender IN ('m', 'w', 'd')),

  -- Kontakt
  address             TEXT,
  phone               TEXT,
  email               TEXT,

  -- Krankenversicherung
  insurance_type      TEXT NOT NULL CHECK (insurance_type IN ('GKV', 'PKV', 'Selbstzahler')),
  insurance_name      TEXT,    -- Name der Krankenkasse (GKV) oder Versicherung (PKV)
  insurance_number    TEXT,    -- Versichertennummer

  -- Status
  status              TEXT NOT NULL DEFAULT 'aktiv'
                        CHECK (status IN ('aktiv', 'pausiert', 'abgeschlossen')),

  -- DSGVO
  gdpr_consent        BOOLEAN NOT NULL DEFAULT FALSE,
  gdpr_consent_date   TIMESTAMPTZ,

  -- Metadaten
  created_at          TIMESTAMPTZ DEFAULT NOW(),
  updated_at          TIMESTAMPTZ DEFAULT NOW(),
  created_by          UUID REFERENCES profiles(id),

  -- Soft-Delete (DSGVO: Anonymisierung statt hartem Löschen)
  deleted_at          TIMESTAMPTZ,
  deleted_by          UUID REFERENCES profiles(id)
);

-- ICD-10 Diagnosen
CREATE TABLE diagnoses (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  patient_id    UUID NOT NULL REFERENCES patients(id),
  praxis_id     UUID NOT NULL REFERENCES praxen(id),
  icd10_code    TEXT NOT NULL,    -- z.B. "R47.0" (Dysarthrie)
  description   TEXT NOT NULL,
  is_primary    BOOLEAN DEFAULT FALSE,
  diagnosed_at  DATE NOT NULL,
  created_by    UUID REFERENCES profiles(id),
  created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- Therapieziele
CREATE TABLE therapy_goals (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  patient_id    UUID NOT NULL REFERENCES patients(id),
  praxis_id     UUID NOT NULL REFERENCES praxen(id),
  title         TEXT NOT NULL,
  description   TEXT,
  target_date   DATE,
  status        TEXT NOT NULL DEFAULT 'offen'
                  CHECK (status IN ('offen', 'in_bearbeitung', 'erreicht', 'aufgegeben')),
  created_by    UUID REFERENCES profiles(id),
  created_at    TIMESTAMPTZ DEFAULT NOW(),
  updated_at    TIMESTAMPTZ DEFAULT NOW()
);

-- Klinische Dokumente (alle Arten)
CREATE TABLE patient_documents (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  patient_id    UUID NOT NULL REFERENCES patients(id),
  praxis_id     UUID NOT NULL REFERENCES praxen(id),
  type          TEXT NOT NULL CHECK (
                  type IN ('bericht', 'soap_note', 'therapieplan',
                           'phonologie', 'upload', 'audio')
                ),
  title         TEXT NOT NULL,
  content       JSONB,       -- strukturierter Inhalt (Report-JSON, etc.)
  file_path     TEXT,        -- Supabase Storage Pfad für Binärdateien
  created_at    TIMESTAMPTZ DEFAULT NOW(),
  created_by    UUID REFERENCES profiles(id),
  deleted_at    TIMESTAMPTZ
);

-- DSGVO-Einwilligungen
CREATE TABLE consent_records (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  patient_id    UUID NOT NULL REFERENCES patients(id),
  praxis_id     UUID NOT NULL REFERENCES praxen(id),
  consent_type  TEXT NOT NULL,
                -- 'behandlung' | 'datenspeicherung' | 'weitergabe' | 'fotos'
  granted_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  revoked_at    TIMESTAMPTZ,
  revoked_by    UUID REFERENCES profiles(id),
  notes         TEXT
);

-- Audit-Log (§30 DSGVO — lückenlos, append-only)
CREATE TABLE audit_logs (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  praxis_id     UUID NOT NULL,
  user_id       UUID NOT NULL,
  patient_id    UUID,           -- NULL für praxis-weite Aktionen
  action        TEXT NOT NULL,
                -- 'read_patient' | 'update_patient' | 'create_document'
                -- | 'delete_document' | 'export_data' | 'revoke_consent' | ...
  table_name    TEXT,
  record_id     UUID,
  old_values    JSONB,
  new_values    JSONB,
  ip_address    INET,
  created_at    TIMESTAMPTZ DEFAULT NOW()
);
-- Audit-Log darf NICHT gelöscht oder geändert werden:
-- REVOKE UPDATE, DELETE ON audit_logs FROM authenticated;
```

### Row-Level Security (RLS)

```sql
-- Alle patientenbezogenen Tabellen: nur eigene Praxis sichtbar
ALTER TABLE patients ENABLE ROW LEVEL SECURITY;
CREATE POLICY "praxis_isolation" ON patients
  USING (
    praxis_id = (
      SELECT praxis_id FROM profiles WHERE id = auth.uid()
    )
  );
-- Gleiche Policy für: diagnoses, therapy_goals, patient_documents,
-- consent_records, audit_logs
```

### Rollenrechte (RBAC via RLS + Check)

| Aktion | admin | therapeut | rezeption |
|---|---|---|---|
| Patient lesen | ✅ | ✅ | ✅ |
| Patient erstellen/bearbeiten | ✅ | ✅ | ✅ |
| Patient löschen (Soft) | ✅ | ❌ | ❌ |
| Dokument erstellen | ✅ | ✅ | ❌ |
| Dokument lesen | ✅ | ✅ | ❌ |
| Einwilligungen verwalten | ✅ | ✅ | ✅ |
| Benutzer verwalten | ✅ | ❌ | ❌ |
| Audit-Log lesen | ✅ | ❌ | ❌ |

---

## 5. DSGVO-Mechanismen

| Anforderung | Implementierung |
|---|---|
| Einwilligung | `consent_records` Tabelle, Widerruf mit Timestamp |
| Recht auf Löschung | `deleted_at` setzen + Name anonymisieren → "Gelöschter Patient [ID]" |
| Audit-Trail | `audit_logs` via DB-Trigger auf alle CRUD-Operationen |
| Verschlüsselung Transit | TLS (Supabase Standard) |
| Verschlüsselung Ruhe | AES-256 (Supabase Standard, EU-Rechenzentrum) |
| EU-Hosting | Supabase eu-central-1 (Frankfurt) — in Projekt-Settings erzwingen |
| DPA | Supabase DSGVO-Auftragsverarbeitungsvertrag abschließen (Self-Service) |
| Datenparsimonie | Kein Tracking, keine Analytics-Cookies, kein US-CDN für Patientendaten |
| Verarbeitungsverzeichnis | Export-Funktion aus `audit_logs` generieren |

**Anonymisierungs-Prozedur bei Löschung:**
```sql
UPDATE patients SET
  first_name = 'Gelöschter',
  last_name  = 'Patient',
  date_of_birth = '1900-01-01',
  address = NULL, phone = NULL, email = NULL,
  insurance_number = NULL,
  gdpr_consent = FALSE,
  deleted_at = NOW(),
  deleted_by = auth.uid()
WHERE id = $patient_id AND praxis_id = (SELECT praxis_id FROM profiles WHERE id = auth.uid());
-- Dokumente/Diagnosen/Ziele bleiben (anonymisiert durch fehlende PII im parent)
```

---

## 6. Frontend-Screens (Baustein 1 Scope)

| Route | Screen | Kerninhalte |
|---|---|---|
| `/login` | Login | Email/Passwort, MFA, "Passwort vergessen" |
| `/register` | Praxis-Registrierung | Praxisname, Admin-Account anlegen |
| `/dashboard` | Dashboard | Patientenanzahl, letzte Aktivitäten |
| `/patienten` | Patientenliste | Suche, Filter (Status/Versicherung), Tabelle |
| `/patienten/neu` | Patient anlegen | Formular: Stammdaten + Versicherung + DSGVO-Einwilligung |
| `/patienten/[id]` | Patientenakte | Tabs: Stammdaten · Diagnosen · Ziele · Dokumente · Einwilligungen |
| `/einstellungen` | Einstellungen | Praxis-Daten, Benutzer verwalten, Datenschutz |

---

## 7. API-Design (Next.js Route Handlers + Supabase direkt)

**Prinzip:** Supabase-Operationen laufen direkt aus Server Components via Supabase SDK (kein eigener REST-Layer für CRUD). FastAPI nur für AI-Operationen.

```
Supabase SDK (direkt):
  GET    /patienten          → supabase.from('patients').select(...)
  POST   /patienten          → supabase.from('patients').insert(...)
  PATCH  /patienten/[id]     → supabase.from('patients').update(...)
  DELETE /patienten/[id]     → anonymize() procedure

FastAPI (AI-Operationen — portiert):
  POST   /api/sessions                    → Session erstellen
  POST   /api/sessions/[id]/audio         → Audio → Transkript
  POST   /api/sessions/[id]/generate      → Bericht generieren
  POST   /api/sessions/[id]/soap          → SOAP Notes
  POST   /api/sessions/[id]/therapy-plan  → Therapieplan
```

Nach AI-Generierung: Next.js Server Action schreibt Ergebnis als `patient_documents`-Eintrag in Supabase.

---

## 8. Aufwandschätzung Baustein 1

| Aufgabe | Wochen |
|---|---|
| Supabase-Projekt aufsetzen (EU-Region, DPA, RLS) | 0.5 |
| DB-Schema + Migrations schreiben | 1.0 |
| Auth-Flow (Login, Register, Rollen) | 1.0 |
| Patientenliste + Patientenakte UI | 1.5 |
| DSGVO-Mechanismen (Consent, Soft-Delete, Audit-Trigger) | 1.0 |
| FastAPI AI-Service portieren + mit Supabase verknüpfen | 1.0 |
| Tests + CI | 0.5 |
| **Gesamt** | **~6.5 Wochen solo** |

---

## 9. Offene Entscheidungen (vor Implementierungsstart klären)

- [x] **Repo-Name:** `logopaedie-praxis` — bestätigt
- [ ] **Supabase-Projekt:** neu anlegen, Region eu-central-1 erzwingen (Account vorhanden)
- [ ] **Vercel-Projekt:** neues Projekt, gleiches Account
- [ ] **DSGVO-DPA:** Supabase DPA abschließen vor erstem echten Patientendatum
- [x] **ICD-10-Quelle:** Freitexteingabe mit Regex-Validierung (`/^[A-Z]\d{2}(\.\d{1,2})?$/`) in v1. Autocomplete-Katalog (ICD-10-GM, 16.000 Codes) kommt in Baustein 2.
- [x] **Sprache UI:** Nur Deutsch (v1) — bestätigt durch Zielmarkt Deutschland

---

## 10. Was explizit NICHT in Baustein 1 ist

- Terminplanung (Baustein 3)
- GKV/PKV-Abrechnung (Baustein 4)
- Multi-Therapeut-Kalender (Baustein 3)
- TI/ePA-Anbindung (Baustein 5)
- Mobile App
- Offline-Modus
