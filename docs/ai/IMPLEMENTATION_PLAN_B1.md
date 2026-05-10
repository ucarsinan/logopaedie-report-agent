# Logopädie-Praxis Baustein 1 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Neues Repo `logopaedie-praxis` aufsetzen mit DSGVO-konformer Patientenverwaltung auf Basis von Next.js 16 + Supabase (eu-central-1) + FastAPI (AI only).

**Architecture:** Next.js Server Components querien Supabase direkt via SDK (RLS erzwingt Mandantenisolation automatisch). FastAPI läuft als reiner AI-Service (Groq) ohne DB-Zugriff. Alle AI-Ergebnisse werden via Next.js Server Actions nach Supabase geschrieben.

**Tech Stack:** Next.js 16 · React 19 · Tailwind CSS v4 · TypeScript · Supabase (Auth + PostgreSQL + Storage) · FastAPI · Groq API · Vitest · GitHub Actions

---

## Voraussetzungen (manuell, vor Task 1)

- [ ] Supabase-Projekt anlegen: Dashboard → New Project → Region **eu-central-1 (Frankfurt)** → Name: `logopaedie-praxis`
- [ ] Notiere: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`
- [ ] Supabase CLI installieren: `brew install supabase/tap/supabase`
- [ ] GitHub-Repo anlegen: `logopaedie-praxis` (private)

---

## Datei-Übersicht (alle Tasks)

```
logopaedie-praxis/
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── (auth)/
│   │   │   │   ├── login/page.tsx
│   │   │   │   └── register/page.tsx
│   │   │   ├── (praxis)/
│   │   │   │   ├── layout.tsx              ← auth guard
│   │   │   │   ├── dashboard/page.tsx
│   │   │   │   ├── patienten/
│   │   │   │   │   ├── page.tsx
│   │   │   │   │   ├── neu/page.tsx
│   │   │   │   │   └── [id]/
│   │   │   │   │       ├── page.tsx
│   │   │   │   │       └── diagnoses/      ← route group
│   │   │   │   └── einstellungen/page.tsx
│   │   │   └── layout.tsx
│   │   ├── features/
│   │   │   ├── patients/
│   │   │   │   ├── PatientList.tsx
│   │   │   │   ├── PatientForm.tsx
│   │   │   │   ├── PatientAkte.tsx
│   │   │   │   ├── DiagnoseForm.tsx
│   │   │   │   ├── TherapyGoalForm.tsx
│   │   │   │   ├── ConsentPanel.tsx
│   │   │   │   └── actions.ts              ← alle Server Actions
│   │   │   └── auth/
│   │   │       ├── LoginForm.tsx
│   │   │       ├── RegisterForm.tsx
│   │   │       └── actions.ts
│   │   ├── lib/
│   │   │   ├── supabase/
│   │   │   │   ├── client.ts
│   │   │   │   └── server.ts
│   │   │   ├── types/
│   │   │   │   └── database.ts
│   │   │   └── validation.ts               ← ICD-10, Zod schemas
│   │   └── components/
│   │       ├── layout/
│   │       │   ├── Sidebar.tsx
│   │       │   └── Header.tsx
│   │       └── ui/                         ← shadcn/ui
│   ├── middleware.ts
│   ├── next.config.ts
│   ├── package.json
│   └── vitest.config.ts
├── backend/
│   ├── main.py
│   ├── routers/
│   │   ├── sessions.py
│   │   ├── reports.py
│   │   └── analysis.py
│   ├── services/
│   │   ├── groq_service.py
│   │   ├── report_service.py
│   │   └── audio_service.py
│   ├── models/schemas.py
│   ├── requirements.txt
│   └── tests/
├── supabase/
│   └── migrations/
│       ├── 20260510000001_praxen_profiles.sql
│       ├── 20260510000002_patients.sql
│       ├── 20260510000003_clinical.sql
│       ├── 20260510000004_audit_consent.sql
│       └── 20260510000005_rls_triggers.sql
├── .github/workflows/ci.yml
├── .env.example
├── dev.sh
├── vercel.json
└── CLAUDE.md
```

---

## Task 1: Repo-Setup + Next.js Scaffold

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/next.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/vitest.config.ts`
- Create: `.env.example`
- Create: `dev.sh`
- Create: `CLAUDE.md`

- [ ] **Step 1: Repo initialisieren**

```bash
mkdir logopaedie-praxis && cd logopaedie-praxis
git init
git remote add origin git@github.com:<USERNAME>/logopaedie-praxis.git
```

- [ ] **Step 2: Next.js Projekt scaffolden**

```bash
cd frontend
npx create-next-app@latest . \
  --typescript \
  --tailwind \
  --eslint \
  --app \
  --src-dir \
  --no-turbopack \
  --import-alias "@/*"
```

Beantworte alle Prompts mit den obigen Flags (kein Turbopack, `src/` Verzeichnis, `@/*` Import-Alias).

- [ ] **Step 3: Supabase + Zod installieren**

```bash
npm install @supabase/supabase-js @supabase/ssr zod
npm install -D vitest @vitejs/plugin-react @testing-library/react @testing-library/jest-dom jsdom
```

- [ ] **Step 4: `frontend/next.config.ts` schreiben**

```typescript
import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  experimental: {
    serverActions: { bodySizeLimit: '2mb' },
  },
}

export default nextConfig
```

- [ ] **Step 5: `frontend/vitest.config.ts` schreiben**

```typescript
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    globals: true,
  },
  resolve: {
    alias: { '@': resolve(__dirname, './src') },
  },
})
```

- [ ] **Step 6: `frontend/src/test/setup.ts` schreiben**

```typescript
import '@testing-library/jest-dom'
```

- [ ] **Step 7: `.env.example` schreiben**

```bash
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
GROQ_API_KEY=your-groq-key
NEXT_PUBLIC_API_URL=http://localhost:8001
```

- [ ] **Step 8: `.env.local` aus `.env.example` erstellen und Werte eintragen**

```bash
cp .env.example frontend/.env.local
# Werte aus Supabase Dashboard eintragen
```

- [ ] **Step 9: `dev.sh` schreiben**

```bash
#!/bin/bash
set -e
echo "Starting logopaedie-praxis dev environment..."
(cd backend && uvicorn main:app --reload --port 8001) &
BACKEND_PID=$!
(cd frontend && npm run dev) &
FRONTEND_PID=$!
trap "kill $BACKEND_PID $FRONTEND_PID" EXIT
wait
```

```bash
chmod +x dev.sh
```

- [ ] **Step 10: `CLAUDE.md` schreiben**

```markdown
# logopaedie-praxis — Claude Context

## Was dieses Projekt ist
AI-First Praxismanagementsystem für Logopädie-Praxen (Deutschland). Echtes Produkt, abgezweigt von `logopaedie-report-agent` (Portfolio-Demo).

## Stack
- Frontend: Next.js 16, React 19, Tailwind v4, TypeScript
- Auth + DB: Supabase (eu-central-1 Frankfurt, DSGVO)
- AI: FastAPI + Groq (Whisper + Llama)
- Hosting: Vercel

## Entwicklung
./dev.sh          — beide Services parallel
cd frontend && npm test    — Vitest
cd backend && python -m pytest

## Ports
Backend: :8001 | Frontend: :3000

## Kritisch
- Supabase Region MUSS eu-central-1 sein (DSGVO)
- FastAPI hat KEINEN direkten DB-Zugriff
- Audit-Log darf nicht gelöscht/geändert werden
```

- [ ] **Step 11: `.gitignore` erstellen**

```bash
cat > .gitignore << 'EOF'
.env.local
.env.*.local
node_modules/
.next/
__pycache__/
*.pyc
.venv/
dist/
.vercel/
docs/superpowers/
EOF
```

- [ ] **Step 12: Commit**

```bash
git add -A
git commit -m "chore: initial repo scaffold (Next.js 16 + Supabase stack)"
```

---

## Task 2: Supabase Client Setup

**Files:**
- Create: `frontend/src/lib/supabase/client.ts`
- Create: `frontend/src/lib/supabase/server.ts`
- Create: `frontend/src/lib/types/database.ts`
- Create: `frontend/src/test/supabase.mock.ts`

- [ ] **Step 1: `frontend/src/lib/supabase/client.ts` schreiben**

```typescript
import { createBrowserClient } from '@supabase/ssr'
import type { Database } from '@/lib/types/database'

export function createClient() {
  return createBrowserClient<Database>(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
  )
}
```

- [ ] **Step 2: `frontend/src/lib/supabase/server.ts` schreiben**

```typescript
import { createServerClient } from '@supabase/ssr'
import { cookies } from 'next/headers'
import type { Database } from '@/lib/types/database'

export async function createClient() {
  const cookieStore = await cookies()
  return createServerClient<Database>(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() { return cookieStore.getAll() },
        setAll(cookiesToSet) {
          try {
            cookiesToSet.forEach(({ name, value, options }) =>
              cookieStore.set(name, value, options)
            )
          } catch {}
        },
      },
    },
  )
}
```

- [ ] **Step 3: `frontend/src/lib/types/database.ts` schreiben**

```typescript
export type Json = string | number | boolean | null | { [key: string]: Json } | Json[]

export type PatientStatus = 'aktiv' | 'pausiert' | 'abgeschlossen'
export type InsuranceType = 'GKV' | 'PKV' | 'Selbstzahler'
export type Gender = 'm' | 'w' | 'd'
export type UserRole = 'admin' | 'therapeut' | 'rezeption'
export type GoalStatus = 'offen' | 'in_bearbeitung' | 'erreicht' | 'aufgegeben'
export type DocumentType = 'bericht' | 'soap_note' | 'therapieplan' | 'phonologie' | 'upload' | 'audio'

export interface Database {
  public: {
    Tables: {
      praxen: {
        Row: { id: string; name: string; address: string | null; phone: string | null; email: string | null; created_at: string }
        Insert: { name: string; address?: string | null; phone?: string | null; email?: string | null }
        Update: Partial<Database['public']['Tables']['praxen']['Insert']>
      }
      profiles: {
        Row: { id: string; praxis_id: string; role: UserRole; first_name: string; last_name: string; created_at: string }
        Insert: { id: string; praxis_id: string; role: UserRole; first_name: string; last_name: string }
        Update: { role?: UserRole; first_name?: string; last_name?: string }
      }
      patients: {
        Row: {
          id: string; praxis_id: string
          first_name: string; last_name: string; date_of_birth: string; gender: Gender | null
          address: string | null; phone: string | null; email: string | null
          insurance_type: InsuranceType; insurance_name: string | null; insurance_number: string | null
          status: PatientStatus; gdpr_consent: boolean; gdpr_consent_date: string | null
          created_at: string; updated_at: string; created_by: string | null
          deleted_at: string | null; deleted_by: string | null
        }
        Insert: Omit<Database['public']['Tables']['patients']['Row'], 'id' | 'created_at' | 'updated_at' | 'deleted_at' | 'deleted_by'>
        Update: Partial<Omit<Database['public']['Tables']['patients']['Row'], 'id' | 'praxis_id' | 'created_at'>>
      }
      diagnoses: {
        Row: { id: string; patient_id: string; praxis_id: string; icd10_code: string; description: string; is_primary: boolean; diagnosed_at: string; created_by: string | null; created_at: string }
        Insert: Omit<Database['public']['Tables']['diagnoses']['Row'], 'id' | 'created_at'>
        Update: { description?: string; is_primary?: boolean; diagnosed_at?: string }
      }
      therapy_goals: {
        Row: { id: string; patient_id: string; praxis_id: string; title: string; description: string | null; target_date: string | null; status: GoalStatus; created_by: string | null; created_at: string; updated_at: string }
        Insert: Omit<Database['public']['Tables']['therapy_goals']['Row'], 'id' | 'created_at' | 'updated_at'>
        Update: { title?: string; description?: string | null; target_date?: string | null; status?: GoalStatus }
      }
      patient_documents: {
        Row: { id: string; patient_id: string; praxis_id: string; type: DocumentType; title: string; content: Json | null; file_path: string | null; created_at: string; created_by: string | null; deleted_at: string | null }
        Insert: Omit<Database['public']['Tables']['patient_documents']['Row'], 'id' | 'created_at' | 'deleted_at'>
        Update: { deleted_at?: string }
      }
      consent_records: {
        Row: { id: string; patient_id: string; praxis_id: string; consent_type: string; granted_at: string; revoked_at: string | null; revoked_by: string | null; notes: string | null }
        Insert: Omit<Database['public']['Tables']['consent_records']['Row'], 'id' | 'granted_at'>
        Update: { revoked_at?: string; revoked_by?: string }
      }
      audit_logs: {
        Row: { id: string; praxis_id: string; user_id: string; patient_id: string | null; action: string; table_name: string | null; record_id: string | null; old_values: Json | null; new_values: Json | null; ip_address: string | null; created_at: string }
        Insert: Omit<Database['public']['Tables']['audit_logs']['Row'], 'id' | 'created_at'>
        Update: never
      }
    }
  }
}
```

- [ ] **Step 4: `frontend/src/test/supabase.mock.ts` schreiben** (wird in allen Tests genutzt)

```typescript
import { vi } from 'vitest'

export const mockSupabase = {
  from: vi.fn().mockReturnThis(),
  select: vi.fn().mockReturnThis(),
  insert: vi.fn().mockReturnThis(),
  update: vi.fn().mockReturnThis(),
  eq: vi.fn().mockReturnThis(),
  is: vi.fn().mockReturnThis(),
  order: vi.fn().mockReturnThis(),
  single: vi.fn(),
  auth: {
    getUser: vi.fn(),
    signInWithPassword: vi.fn(),
    signOut: vi.fn(),
  },
}

vi.mock('@/lib/supabase/server', () => ({
  createClient: vi.fn(() => mockSupabase),
}))
```

- [ ] **Step 5: Test schreiben — Supabase client gibt korrekten Typ zurück**

Datei: `frontend/src/lib/supabase/__tests__/client.test.ts`

```typescript
import { describe, it, expect, vi } from 'vitest'

vi.mock('@supabase/ssr', () => ({
  createBrowserClient: vi.fn(() => ({ from: vi.fn() })),
}))

import { createClient } from '../client'

describe('supabase browser client', () => {
  it('creates a client with env vars', () => {
    process.env.NEXT_PUBLIC_SUPABASE_URL = 'https://test.supabase.co'
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = 'test-key'
    const client = createClient()
    expect(client).toBeDefined()
    expect(typeof client.from).toBe('function')
  })
})
```

- [ ] **Step 6: Test ausführen**

```bash
cd frontend && npm test src/lib/supabase/__tests__/client.test.ts
```
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add frontend/src/lib/ frontend/src/test/
git commit -m "feat: add Supabase client setup and database types"
```

---

## Task 3: Datenbank-Migrations (Schema)

**Files:**
- Create: `supabase/migrations/20260510000001_praxen_profiles.sql`
- Create: `supabase/migrations/20260510000002_patients.sql`
- Create: `supabase/migrations/20260510000003_clinical.sql`
- Create: `supabase/migrations/20260510000004_audit_consent.sql`

- [ ] **Step 1: Supabase CLI mit Remote-Projekt verbinden**

```bash
supabase login
supabase link --project-ref <PROJECT_REF>
# PROJECT_REF = Teil der Supabase URL: https://<PROJECT_REF>.supabase.co
```

- [ ] **Step 2: Migration 1 — praxen + profiles**

`supabase/migrations/20260510000001_praxen_profiles.sql`:

```sql
CREATE TABLE IF NOT EXISTS praxen (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name       TEXT NOT NULL,
  address    TEXT,
  phone      TEXT,
  email      TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS profiles (
  id         UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  praxis_id  UUID NOT NULL REFERENCES praxen(id) ON DELETE CASCADE,
  role       TEXT NOT NULL CHECK (role IN ('admin', 'therapeut', 'rezeption')),
  first_name TEXT NOT NULL,
  last_name  TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS profiles_praxis_id_idx ON profiles(praxis_id);
```

- [ ] **Step 3: Migration 2 — patients**

`supabase/migrations/20260510000002_patients.sql`:

```sql
CREATE TABLE IF NOT EXISTS patients (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  praxis_id        UUID NOT NULL REFERENCES praxen(id) ON DELETE CASCADE,

  first_name       TEXT NOT NULL,
  last_name        TEXT NOT NULL,
  date_of_birth    DATE NOT NULL,
  gender           TEXT CHECK (gender IN ('m', 'w', 'd')),

  address          TEXT,
  phone            TEXT,
  email            TEXT,

  insurance_type   TEXT NOT NULL CHECK (insurance_type IN ('GKV', 'PKV', 'Selbstzahler')),
  insurance_name   TEXT,
  insurance_number TEXT,

  status           TEXT NOT NULL DEFAULT 'aktiv'
                     CHECK (status IN ('aktiv', 'pausiert', 'abgeschlossen')),

  gdpr_consent      BOOLEAN NOT NULL DEFAULT FALSE,
  gdpr_consent_date TIMESTAMPTZ,

  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_by       UUID REFERENCES profiles(id) ON DELETE SET NULL,

  deleted_at       TIMESTAMPTZ,
  deleted_by       UUID REFERENCES profiles(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS patients_praxis_id_idx ON patients(praxis_id);
CREATE INDEX IF NOT EXISTS patients_status_idx    ON patients(praxis_id, status) WHERE deleted_at IS NULL;

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER patients_updated_at
  BEFORE UPDATE ON patients
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();
```

- [ ] **Step 4: Migration 3 — clinical (diagnoses, therapy_goals, patient_documents)**

`supabase/migrations/20260510000003_clinical.sql`:

```sql
CREATE TABLE IF NOT EXISTS diagnoses (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  patient_id   UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
  praxis_id    UUID NOT NULL REFERENCES praxen(id) ON DELETE CASCADE,
  icd10_code   TEXT NOT NULL,
  description  TEXT NOT NULL,
  is_primary   BOOLEAN NOT NULL DEFAULT FALSE,
  diagnosed_at DATE NOT NULL,
  created_by   UUID REFERENCES profiles(id) ON DELETE SET NULL,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS diagnoses_patient_id_idx ON diagnoses(patient_id);

CREATE TABLE IF NOT EXISTS therapy_goals (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  patient_id   UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
  praxis_id    UUID NOT NULL REFERENCES praxen(id) ON DELETE CASCADE,
  title        TEXT NOT NULL,
  description  TEXT,
  target_date  DATE,
  status       TEXT NOT NULL DEFAULT 'offen'
                 CHECK (status IN ('offen', 'in_bearbeitung', 'erreicht', 'aufgegeben')),
  created_by   UUID REFERENCES profiles(id) ON DELETE SET NULL,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS therapy_goals_patient_id_idx ON therapy_goals(patient_id);

CREATE TRIGGER therapy_goals_updated_at
  BEFORE UPDATE ON therapy_goals
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TABLE IF NOT EXISTS patient_documents (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  patient_id   UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
  praxis_id    UUID NOT NULL REFERENCES praxen(id) ON DELETE CASCADE,
  type         TEXT NOT NULL CHECK (
                 type IN ('bericht', 'soap_note', 'therapieplan', 'phonologie', 'upload', 'audio')
               ),
  title        TEXT NOT NULL,
  content      JSONB,
  file_path    TEXT,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_by   UUID REFERENCES profiles(id) ON DELETE SET NULL,
  deleted_at   TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS patient_documents_patient_id_idx ON patient_documents(patient_id) WHERE deleted_at IS NULL;
```

- [ ] **Step 5: Migration 4 — audit + consent**

`supabase/migrations/20260510000004_audit_consent.sql`:

```sql
CREATE TABLE IF NOT EXISTS consent_records (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  patient_id   UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
  praxis_id    UUID NOT NULL REFERENCES praxen(id) ON DELETE CASCADE,
  consent_type TEXT NOT NULL CHECK (
                 consent_type IN ('behandlung', 'datenspeicherung', 'weitergabe', 'fotos')
               ),
  granted_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  revoked_at   TIMESTAMPTZ,
  revoked_by   UUID REFERENCES profiles(id) ON DELETE SET NULL,
  notes        TEXT
);

CREATE INDEX IF NOT EXISTS consent_records_patient_id_idx ON consent_records(patient_id);

CREATE TABLE IF NOT EXISTS audit_logs (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  praxis_id   UUID NOT NULL,
  user_id     UUID NOT NULL,
  patient_id  UUID,
  action      TEXT NOT NULL,
  table_name  TEXT,
  record_id   UUID,
  old_values  JSONB,
  new_values  JSONB,
  ip_address  INET,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS audit_logs_patient_id_idx  ON audit_logs(patient_id);
CREATE INDEX IF NOT EXISTS audit_logs_praxis_id_idx   ON audit_logs(praxis_id);
CREATE INDEX IF NOT EXISTS audit_logs_created_at_idx  ON audit_logs(created_at DESC);

-- Audit-Log ist append-only: kein UPDATE/DELETE erlaubt
REVOKE UPDATE, DELETE ON audit_logs FROM authenticated;
```

- [ ] **Step 6: Migrations deployen**

```bash
supabase db push
```
Expected: "Applying migration 20260510000001... Done" × 4

- [ ] **Step 7: Im Supabase Dashboard prüfen**

Table Editor → alle 8 Tabellen sollten sichtbar sein: `praxen`, `profiles`, `patients`, `diagnoses`, `therapy_goals`, `patient_documents`, `consent_records`, `audit_logs`.

- [ ] **Step 8: Commit**

```bash
git add supabase/
git commit -m "feat(db): add all schema migrations (B1: praxen, patients, clinical, audit)"
```

---

## Task 4: RLS Policies + Audit-Trigger

**Files:**
- Create: `supabase/migrations/20260510000005_rls_triggers.sql`

- [ ] **Step 1: Migration 5 schreiben**

`supabase/migrations/20260510000005_rls_triggers.sql`:

```sql
-- ============================================
-- RLS: Mandantenisolation (alle Tabellen)
-- ============================================

-- Helper: praxis_id des eingeloggten Users
CREATE OR REPLACE FUNCTION my_praxis_id()
RETURNS UUID LANGUAGE sql STABLE AS $$
  SELECT praxis_id FROM profiles WHERE id = auth.uid()
$$;

-- Helper: Rolle des eingeloggten Users
CREATE OR REPLACE FUNCTION my_role()
RETURNS TEXT LANGUAGE sql STABLE AS $$
  SELECT role FROM profiles WHERE id = auth.uid()
$$;

-- patients
ALTER TABLE patients ENABLE ROW LEVEL SECURITY;
CREATE POLICY "patients_praxis_isolation" ON patients
  USING (praxis_id = my_praxis_id());
CREATE POLICY "patients_no_deleted" ON patients
  AS RESTRICTIVE USING (deleted_at IS NULL);
CREATE POLICY "patients_delete_admin_only" ON patients
  FOR UPDATE USING (my_role() = 'admin' OR new.deleted_at IS NULL);

-- diagnoses
ALTER TABLE diagnoses ENABLE ROW LEVEL SECURITY;
CREATE POLICY "diagnoses_praxis_isolation" ON diagnoses
  USING (praxis_id = my_praxis_id());

-- therapy_goals
ALTER TABLE therapy_goals ENABLE ROW LEVEL SECURITY;
CREATE POLICY "therapy_goals_praxis_isolation" ON therapy_goals
  USING (praxis_id = my_praxis_id());

-- patient_documents: Rezeption darf NICHT lesen
ALTER TABLE patient_documents ENABLE ROW LEVEL SECURITY;
CREATE POLICY "documents_praxis_isolation" ON patient_documents
  USING (praxis_id = my_praxis_id());
CREATE POLICY "documents_no_rezeption" ON patient_documents
  AS RESTRICTIVE USING (my_role() IN ('admin', 'therapeut'));

-- consent_records
ALTER TABLE consent_records ENABLE ROW LEVEL SECURITY;
CREATE POLICY "consent_praxis_isolation" ON consent_records
  USING (praxis_id = my_praxis_id());

-- audit_logs: nur Admin darf lesen; alle dürfen inserieren (via Server Action)
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "audit_read_admin_only" ON audit_logs
  FOR SELECT USING (praxis_id = my_praxis_id() AND my_role() = 'admin');
CREATE POLICY "audit_insert_own_praxis" ON audit_logs
  FOR INSERT WITH CHECK (praxis_id = my_praxis_id());

-- profiles: Benutzer sieht nur Kollegen aus derselben Praxis
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "profiles_praxis_isolation" ON profiles
  USING (praxis_id = my_praxis_id());

-- ============================================
-- Audit-Trigger: Automatisches Logging
-- ============================================

CREATE OR REPLACE FUNCTION audit_patient_changes()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    INSERT INTO audit_logs (praxis_id, user_id, patient_id, action, table_name, record_id, new_values)
    VALUES (NEW.praxis_id, auth.uid(), NEW.id, 'create_patient', TG_TABLE_NAME, NEW.id, to_jsonb(NEW));
  ELSIF TG_OP = 'UPDATE' THEN
    INSERT INTO audit_logs (praxis_id, user_id, patient_id, action, table_name, record_id, old_values, new_values)
    VALUES (NEW.praxis_id, auth.uid(), NEW.id, 'update_patient', TG_TABLE_NAME, NEW.id, to_jsonb(OLD), to_jsonb(NEW));
  END IF;
  RETURN NEW;
END;
$$;

CREATE TRIGGER patients_audit
  AFTER INSERT OR UPDATE ON patients
  FOR EACH ROW EXECUTE FUNCTION audit_patient_changes();

CREATE OR REPLACE FUNCTION audit_document_changes()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    INSERT INTO audit_logs (praxis_id, user_id, patient_id, action, table_name, record_id, new_values)
    VALUES (NEW.praxis_id, auth.uid(), NEW.patient_id, 'create_document', TG_TABLE_NAME, NEW.id, to_jsonb(NEW));
  ELSIF TG_OP = 'UPDATE' AND NEW.deleted_at IS NOT NULL AND OLD.deleted_at IS NULL THEN
    INSERT INTO audit_logs (praxis_id, user_id, patient_id, action, table_name, record_id)
    VALUES (NEW.praxis_id, auth.uid(), NEW.patient_id, 'delete_document', TG_TABLE_NAME, NEW.id);
  END IF;
  RETURN NEW;
END;
$$;

CREATE TRIGGER documents_audit
  AFTER INSERT OR UPDATE ON patient_documents
  FOR EACH ROW EXECUTE FUNCTION audit_document_changes();
```

- [ ] **Step 2: Migration deployen**

```bash
supabase db push
```

- [ ] **Step 3: RLS im Supabase Dashboard verifizieren**

Authentication → Policies → Tabelle `patients` sollte 3 Policies zeigen.

- [ ] **Step 4: Commit**

```bash
git add supabase/migrations/20260510000005_rls_triggers.sql
git commit -m "feat(db): add RLS policies and audit triggers"
```

---

## Task 5: Next.js Auth Middleware

**Files:**
- Create: `frontend/middleware.ts`
- Create: `frontend/src/app/(praxis)/layout.tsx`

- [ ] **Step 1: `frontend/middleware.ts` schreiben**

```typescript
import { createServerClient } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'

export async function middleware(request: NextRequest) {
  let supabaseResponse = NextResponse.next({ request })

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() { return request.cookies.getAll() },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value))
          supabaseResponse = NextResponse.next({ request })
          cookiesToSet.forEach(({ name, value, options }) =>
            supabaseResponse.cookies.set(name, value, options)
          )
        },
      },
    },
  )

  const { data: { user } } = await supabase.auth.getUser()
  const { pathname } = request.nextUrl

  const isAuthRoute = pathname.startsWith('/login') || pathname.startsWith('/register')
  const isProtected = !isAuthRoute && !pathname.startsWith('/_next') && !pathname.startsWith('/api')

  if (isProtected && !user) {
    return NextResponse.redirect(new URL('/login', request.url))
  }

  if (isAuthRoute && user) {
    return NextResponse.redirect(new URL('/dashboard', request.url))
  }

  return supabaseResponse
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
}
```

- [ ] **Step 2: `frontend/src/app/(praxis)/layout.tsx` schreiben**

```typescript
import { createClient } from '@/lib/supabase/server'
import { redirect } from 'next/navigation'
import { Sidebar } from '@/components/layout/Sidebar'
import { Header } from '@/components/layout/Header'

export default async function PraxisLayout({ children }: { children: React.ReactNode }) {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()

  if (!user) redirect('/login')

  const { data: profile } = await supabase
    .from('profiles')
    .select('*, praxen(name)')
    .eq('id', user.id)
    .single()

  if (!profile) redirect('/login')

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar role={profile.role} />
      <div className="flex flex-col flex-1 overflow-hidden">
        <Header
          userName={`${profile.first_name} ${profile.last_name}`}
          praxisName={(profile.praxen as { name: string })?.name ?? ''}
        />
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Test schreiben — Middleware leitet unauthentifizierten User um**

`frontend/src/test/middleware.test.ts`:

```typescript
import { describe, it, expect, vi } from 'vitest'

const mockGetUser = vi.fn()
vi.mock('@supabase/ssr', () => ({
  createServerClient: vi.fn(() => ({
    auth: { getUser: mockGetUser },
    cookies: {},
  })),
}))

import { middleware } from '../../../middleware'
import { NextRequest } from 'next/server'

function makeRequest(path: string) {
  return new NextRequest(new URL(`http://localhost${path}`))
}

describe('middleware', () => {
  it('redirects unauthenticated user from /dashboard to /login', async () => {
    mockGetUser.mockResolvedValue({ data: { user: null } })
    const response = await middleware(makeRequest('/dashboard'))
    expect(response.headers.get('location')).toContain('/login')
  })

  it('redirects authenticated user from /login to /dashboard', async () => {
    mockGetUser.mockResolvedValue({ data: { user: { id: 'u1' } } })
    const response = await middleware(makeRequest('/login'))
    expect(response.headers.get('location')).toContain('/dashboard')
  })
})
```

- [ ] **Step 4: Test ausführen**

```bash
cd frontend && npm test src/test/middleware.test.ts
```
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add frontend/middleware.ts frontend/src/app/\(praxis\)/layout.tsx frontend/src/test/
git commit -m "feat(auth): add Next.js middleware and protected layout"
```

---

## Task 6: Login + Register Seiten

**Files:**
- Create: `frontend/src/features/auth/LoginForm.tsx`
- Create: `frontend/src/features/auth/RegisterForm.tsx`
- Create: `frontend/src/features/auth/actions.ts`
- Create: `frontend/src/app/(auth)/login/page.tsx`
- Create: `frontend/src/app/(auth)/register/page.tsx`

- [ ] **Step 1: `frontend/src/features/auth/actions.ts` schreiben**

```typescript
'use server'

import { createClient } from '@/lib/supabase/server'
import { redirect } from 'next/navigation'
import { z } from 'zod'

const LoginSchema = z.object({
  email: z.string().email('Ungültige E-Mail'),
  password: z.string().min(8, 'Mindestens 8 Zeichen'),
})

const RegisterSchema = z.object({
  praxisName: z.string().min(2, 'Praxisname mindestens 2 Zeichen'),
  firstName: z.string().min(1, 'Vorname erforderlich'),
  lastName: z.string().min(1, 'Nachname erforderlich'),
  email: z.string().email('Ungültige E-Mail'),
  password: z.string().min(8, 'Mindestens 8 Zeichen'),
})

export type ActionResult = { error?: string }

export async function loginAction(formData: FormData): Promise<ActionResult> {
  const parsed = LoginSchema.safeParse({
    email: formData.get('email'),
    password: formData.get('password'),
  })
  if (!parsed.success) return { error: parsed.error.errors[0].message }

  const supabase = await createClient()
  const { error } = await supabase.auth.signInWithPassword(parsed.data)
  if (error) return { error: 'E-Mail oder Passwort falsch' }

  redirect('/dashboard')
}

export async function registerAction(formData: FormData): Promise<ActionResult> {
  const parsed = RegisterSchema.safeParse({
    praxisName: formData.get('praxisName'),
    firstName: formData.get('firstName'),
    lastName: formData.get('lastName'),
    email: formData.get('email'),
    password: formData.get('password'),
  })
  if (!parsed.success) return { error: parsed.error.errors[0].message }

  const supabase = await createClient()

  // 1. Praxis anlegen (service role nötig für initialen Insert ohne RLS)
  const { data: praxis, error: praxisError } = await supabase
    .from('praxen')
    .insert({ name: parsed.data.praxisName })
    .select()
    .single()
  if (praxisError || !praxis) return { error: 'Praxis konnte nicht angelegt werden' }

  // 2. Auth-User anlegen
  const { data: authData, error: signUpError } = await supabase.auth.signUp({
    email: parsed.data.email,
    password: parsed.data.password,
  })
  if (signUpError || !authData.user) return { error: 'Registrierung fehlgeschlagen' }

  // 3. Profil anlegen
  const { error: profileError } = await supabase
    .from('profiles')
    .insert({
      id: authData.user.id,
      praxis_id: praxis.id,
      role: 'admin',
      first_name: parsed.data.firstName,
      last_name: parsed.data.lastName,
    })
  if (profileError) return { error: 'Profil konnte nicht angelegt werden' }

  redirect('/dashboard')
}

export async function logoutAction() {
  const supabase = await createClient()
  await supabase.auth.signOut()
  redirect('/login')
}
```

- [ ] **Step 2: `frontend/src/features/auth/LoginForm.tsx` schreiben**

```typescript
'use client'

import { useActionState } from 'react'
import { loginAction } from './actions'

export function LoginForm() {
  const [state, action, isPending] = useActionState(loginAction, {})

  return (
    <form action={action} className="space-y-4">
      {state.error && (
        <p className="text-sm text-red-600 bg-red-50 p-3 rounded-md">{state.error}</p>
      )}
      <div>
        <label htmlFor="email" className="block text-sm font-medium text-gray-700">E-Mail</label>
        <input
          id="email" name="email" type="email" required autoComplete="email"
          className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
        />
      </div>
      <div>
        <label htmlFor="password" className="block text-sm font-medium text-gray-700">Passwort</label>
        <input
          id="password" name="password" type="password" required autoComplete="current-password"
          className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
        />
      </div>
      <button
        type="submit" disabled={isPending}
        className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
      >
        {isPending ? 'Anmelden…' : 'Anmelden'}
      </button>
    </form>
  )
}
```

- [ ] **Step 3: `frontend/src/app/(auth)/login/page.tsx` schreiben**

```typescript
import { LoginForm } from '@/features/auth/LoginForm'
import Link from 'next/link'

export default function LoginPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full bg-white rounded-lg shadow p-8 space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Logopädie-Praxis</h1>
          <p className="mt-1 text-sm text-gray-600">Anmelden</p>
        </div>
        <LoginForm />
        <p className="text-center text-sm text-gray-600">
          Noch kein Account?{' '}
          <Link href="/register" className="text-blue-600 hover:underline">Praxis registrieren</Link>
        </p>
      </div>
    </div>
  )
}
```

- [ ] **Step 4: `frontend/src/features/auth/RegisterForm.tsx` schreiben**

```typescript
'use client'

import { useActionState } from 'react'
import { registerAction } from './actions'

export function RegisterForm() {
  const [state, action, isPending] = useActionState(registerAction, {})

  return (
    <form action={action} className="space-y-4">
      {state.error && (
        <p className="text-sm text-red-600 bg-red-50 p-3 rounded-md">{state.error}</p>
      )}
      <div>
        <label htmlFor="praxisName" className="block text-sm font-medium text-gray-700">Praxisname</label>
        <input id="praxisName" name="praxisName" type="text" required
          className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm sm:text-sm" />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label htmlFor="firstName" className="block text-sm font-medium text-gray-700">Vorname</label>
          <input id="firstName" name="firstName" type="text" required
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm sm:text-sm" />
        </div>
        <div>
          <label htmlFor="lastName" className="block text-sm font-medium text-gray-700">Nachname</label>
          <input id="lastName" name="lastName" type="text" required
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm sm:text-sm" />
        </div>
      </div>
      <div>
        <label htmlFor="email" className="block text-sm font-medium text-gray-700">E-Mail</label>
        <input id="email" name="email" type="email" required
          className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm sm:text-sm" />
      </div>
      <div>
        <label htmlFor="password" className="block text-sm font-medium text-gray-700">Passwort (min. 8 Zeichen)</label>
        <input id="password" name="password" type="password" required minLength={8}
          className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm sm:text-sm" />
      </div>
      <button type="submit" disabled={isPending}
        className="w-full py-2 px-4 rounded-md text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50">
        {isPending ? 'Registrierung…' : 'Praxis registrieren'}
      </button>
    </form>
  )
}
```

- [ ] **Step 5: `frontend/src/app/(auth)/register/page.tsx` schreiben**

```typescript
import { RegisterForm } from '@/features/auth/RegisterForm'
import Link from 'next/link'

export default function RegisterPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full bg-white rounded-lg shadow p-8 space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Neue Praxis registrieren</h1>
          <p className="mt-1 text-sm text-gray-600">Erstellt Admin-Account + Praxis in einem Schritt.</p>
        </div>
        <RegisterForm />
        <p className="text-center text-sm text-gray-600">
          Bereits registriert?{' '}
          <Link href="/login" className="text-blue-600 hover:underline">Anmelden</Link>
        </p>
      </div>
    </div>
  )
}
```

- [ ] **Step 6: Test schreiben — loginAction validiert E-Mail**

`frontend/src/features/auth/__tests__/actions.test.ts`:

```typescript
import { describe, it, expect, vi } from 'vitest'

vi.mock('next/navigation', () => ({ redirect: vi.fn() }))
vi.mock('@/lib/supabase/server', () => ({
  createClient: vi.fn(() => ({
    auth: {
      signInWithPassword: vi.fn().mockResolvedValue({ error: null }),
    },
  })),
}))

import { loginAction } from '../actions'

describe('loginAction', () => {
  it('returns error for invalid email', async () => {
    const formData = new FormData()
    formData.set('email', 'not-an-email')
    formData.set('password', 'password123')
    const result = await loginAction(formData)
    expect(result.error).toBe('Ungültige E-Mail')
  })

  it('returns error for short password', async () => {
    const formData = new FormData()
    formData.set('email', 'test@example.com')
    formData.set('password', 'short')
    const result = await loginAction(formData)
    expect(result.error).toBe('Mindestens 8 Zeichen')
  })
})
```

- [ ] **Step 7: Test ausführen**

```bash
cd frontend && npm test src/features/auth/__tests__/actions.test.ts
```
Expected: PASS (2 tests)

- [ ] **Step 8: Commit**

```bash
git add frontend/src/features/auth/ frontend/src/app/\(auth\)/
git commit -m "feat(auth): add login, register pages and server actions"
```

---

## Task 7: Layout-Komponenten (Sidebar + Header)

**Files:**
- Create: `frontend/src/components/layout/Sidebar.tsx`
- Create: `frontend/src/components/layout/Header.tsx`

- [ ] **Step 1: `frontend/src/components/layout/Sidebar.tsx` schreiben**

```typescript
'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import type { UserRole } from '@/lib/types/database'

interface NavItem {
  href: string
  label: string
  roles: UserRole[]
}

const navItems: NavItem[] = [
  { href: '/dashboard',    label: 'Dashboard',    roles: ['admin', 'therapeut', 'rezeption'] },
  { href: '/patienten',    label: 'Patienten',    roles: ['admin', 'therapeut', 'rezeption'] },
  { href: '/einstellungen',label: 'Einstellungen',roles: ['admin'] },
]

export function Sidebar({ role }: { role: UserRole }) {
  const pathname = usePathname()

  return (
    <aside className="w-56 bg-white border-r border-gray-200 flex flex-col">
      <div className="p-4 border-b border-gray-200">
        <span className="text-sm font-semibold text-blue-600 uppercase tracking-wide">
          Logopädie-Praxis
        </span>
      </div>
      <nav className="flex-1 p-3 space-y-1">
        {navItems
          .filter(item => item.roles.includes(role))
          .map(item => (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center px-3 py-2 text-sm rounded-md transition-colors ${
                pathname.startsWith(item.href)
                  ? 'bg-blue-50 text-blue-700 font-medium'
                  : 'text-gray-700 hover:bg-gray-100'
              }`}
            >
              {item.label}
            </Link>
          ))}
      </nav>
    </aside>
  )
}
```

- [ ] **Step 2: `frontend/src/components/layout/Header.tsx` schreiben**

```typescript
import { logoutAction } from '@/features/auth/actions'

interface HeaderProps {
  userName: string
  praxisName: string
}

export function Header({ userName, praxisName }: HeaderProps) {
  return (
    <header className="h-14 bg-white border-b border-gray-200 flex items-center justify-between px-6">
      <span className="text-sm text-gray-600">{praxisName}</span>
      <div className="flex items-center gap-4">
        <span className="text-sm text-gray-700">{userName}</span>
        <form action={logoutAction}>
          <button type="submit"
            className="text-sm text-gray-500 hover:text-gray-700 hover:underline">
            Abmelden
          </button>
        </form>
      </div>
    </header>
  )
}
```

- [ ] **Step 3: Test — Sidebar zeigt nur rollengerechte Items**

`frontend/src/components/layout/__tests__/Sidebar.test.tsx`:

```typescript
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Sidebar } from '../Sidebar'

vi.mock('next/navigation', () => ({ usePathname: vi.fn(() => '/dashboard') }))

describe('Sidebar', () => {
  it('shows Einstellungen only for admin', () => {
    const { rerender } = render(<Sidebar role="admin" />)
    expect(screen.getByText('Einstellungen')).toBeInTheDocument()

    rerender(<Sidebar role="therapeut" />)
    expect(screen.queryByText('Einstellungen')).not.toBeInTheDocument()
  })

  it('shows Patienten for all roles', () => {
    render(<Sidebar role="rezeption" />)
    expect(screen.getByText('Patienten')).toBeInTheDocument()
  })
})
```

- [ ] **Step 4: Test ausführen**

```bash
cd frontend && npm test src/components/layout/__tests__/Sidebar.test.tsx
```
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/
git commit -m "feat(ui): add Sidebar and Header layout components"
```

---

## Task 8: Validierung

**Files:**
- Create: `frontend/src/lib/validation.ts`
- Test: `frontend/src/lib/__tests__/validation.test.ts`

- [ ] **Step 1: Test schreiben**

```typescript
import { describe, it, expect } from 'vitest'
import { validateIcd10, patientSchema } from '../validation'

describe('validateIcd10', () => {
  it('accepts valid ICD-10 codes', () => {
    expect(validateIcd10('R47')).toBe(true)
    expect(validateIcd10('R47.0')).toBe(true)
    expect(validateIcd10('F80.0')).toBe(true)
    expect(validateIcd10('G47.31')).toBe(true)
  })

  it('rejects invalid codes', () => {
    expect(validateIcd10('r47')).toBe(false)   // lowercase
    expect(validateIcd10('47.0')).toBe(false)  // no letter
    expect(validateIcd10('R4')).toBe(false)    // only 1 digit
    expect(validateIcd10('RABC')).toBe(false)  // letters instead of digits
  })
})

describe('patientSchema', () => {
  it('requires first_name and last_name', () => {
    const result = patientSchema.safeParse({ first_name: '', last_name: 'Test', date_of_birth: '1990-01-01', insurance_type: 'GKV' })
    expect(result.success).toBe(false)
  })

  it('validates date_of_birth format', () => {
    const result = patientSchema.safeParse({ first_name: 'Max', last_name: 'Muster', date_of_birth: 'not-a-date', insurance_type: 'GKV' })
    expect(result.success).toBe(false)
  })

  it('accepts valid patient data', () => {
    const result = patientSchema.safeParse({
      first_name: 'Max', last_name: 'Muster',
      date_of_birth: '1990-01-15', insurance_type: 'GKV',
      gdpr_consent: true,
    })
    expect(result.success).toBe(true)
  })
})
```

- [ ] **Step 2: Test ausführen — erwarte FAIL**

```bash
cd frontend && npm test src/lib/__tests__/validation.test.ts
```
Expected: FAIL — "Cannot find module '../validation'"

- [ ] **Step 3: `frontend/src/lib/validation.ts` schreiben**

```typescript
import { z } from 'zod'

const ICD10_REGEX = /^[A-Z]\d{2}(\.\d{1,2})?$/

export function validateIcd10(code: string): boolean {
  return ICD10_REGEX.test(code)
}

export const patientSchema = z.object({
  first_name:       z.string().min(1, 'Vorname erforderlich'),
  last_name:        z.string().min(1, 'Nachname erforderlich'),
  date_of_birth:    z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'Datum im Format JJJJ-MM-TT'),
  gender:           z.enum(['m', 'w', 'd']).optional(),
  address:          z.string().optional(),
  phone:            z.string().optional(),
  email:            z.string().email('Ungültige E-Mail').optional().or(z.literal('')),
  insurance_type:   z.enum(['GKV', 'PKV', 'Selbstzahler']),
  insurance_name:   z.string().optional(),
  insurance_number: z.string().optional(),
  gdpr_consent:     z.boolean().default(false),
})

export type PatientFormData = z.infer<typeof patientSchema>

export const diagnoseSchema = z.object({
  icd10_code:   z.string().regex(ICD10_REGEX, 'ICD-10 Format: Z00-Z99 oder Z00.0'),
  description:  z.string().min(3, 'Beschreibung erforderlich'),
  is_primary:   z.boolean().default(false),
  diagnosed_at: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'Datum im Format JJJJ-MM-TT'),
})

export type DiagnoseFormData = z.infer<typeof diagnoseSchema>

export const therapyGoalSchema = z.object({
  title:       z.string().min(3, 'Titel mindestens 3 Zeichen'),
  description: z.string().optional(),
  target_date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/).optional().or(z.literal('')),
  status:      z.enum(['offen', 'in_bearbeitung', 'erreicht', 'aufgegeben']).default('offen'),
})

export type TherapyGoalFormData = z.infer<typeof therapyGoalSchema>
```

- [ ] **Step 4: Tests ausführen**

```bash
cd frontend && npm test src/lib/__tests__/validation.test.ts
```
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/validation.ts frontend/src/lib/__tests__/
git commit -m "feat(validation): add ICD-10 and patient/diagnosis/goal Zod schemas"
```

---

## Task 9: Patient Server Actions

**Files:**
- Create: `frontend/src/features/patients/actions.ts`
- Test: `frontend/src/features/patients/__tests__/actions.test.ts`

- [ ] **Step 1: Test schreiben**

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('next/navigation', () => ({ redirect: vi.fn(), revalidatePath: vi.fn() }))
vi.mock('next/cache', () => ({ revalidatePath: vi.fn() }))

const mockFrom = vi.fn()
const mockInsert = vi.fn()
const mockUpdate = vi.fn()
const mockSelect = vi.fn()
const mockSingle = vi.fn()
const mockEq = vi.fn()
const mockGetUser = vi.fn()

const mockSupabase = {
  auth: { getUser: mockGetUser },
  from: mockFrom,
}

vi.mock('@/lib/supabase/server', () => ({
  createClient: vi.fn(() => mockSupabase),
}))

import { createPatientAction, anonymizePatientAction } from '../actions'

beforeEach(() => {
  vi.clearAllMocks()
  mockGetUser.mockResolvedValue({ data: { user: { id: 'user-1' } } })
  mockFrom.mockReturnValue({
    select: mockSelect.mockReturnThis(),
    insert: mockInsert.mockReturnThis(),
    update: mockUpdate.mockReturnThis(),
    eq: mockEq.mockReturnThis(),
    single: mockSingle,
  })
})

describe('createPatientAction', () => {
  it('returns error when gdpr_consent is false', async () => {
    const fd = new FormData()
    fd.set('first_name', 'Max'); fd.set('last_name', 'Muster')
    fd.set('date_of_birth', '1990-01-01'); fd.set('insurance_type', 'GKV')
    // gdpr_consent not set = false
    const result = await createPatientAction(fd)
    expect(result?.error).toContain('DSGVO')
  })

  it('returns error for invalid email', async () => {
    const fd = new FormData()
    fd.set('first_name', 'Max'); fd.set('last_name', 'Muster')
    fd.set('date_of_birth', '1990-01-01'); fd.set('insurance_type', 'GKV')
    fd.set('gdpr_consent', 'true'); fd.set('email', 'not-an-email')
    const result = await createPatientAction(fd)
    expect(result?.error).toBeDefined()
  })
})
```

- [ ] **Step 2: Test ausführen — erwarte FAIL**

```bash
cd frontend && npm test src/features/patients/__tests__/actions.test.ts
```
Expected: FAIL

- [ ] **Step 3: `frontend/src/features/patients/actions.ts` schreiben**

```typescript
'use server'

import { createClient } from '@/lib/supabase/server'
import { revalidatePath } from 'next/cache'
import { redirect } from 'next/navigation'
import { patientSchema, diagnoseSchema, therapyGoalSchema } from '@/lib/validation'
import { z } from 'zod'

export type ActionResult = { error?: string } | undefined

export async function createPatientAction(formData: FormData): Promise<ActionResult> {
  const gdprConsent = formData.get('gdpr_consent') === 'true'
  if (!gdprConsent) return { error: 'DSGVO-Einwilligung ist erforderlich' }

  const parsed = patientSchema.safeParse({
    first_name:       formData.get('first_name'),
    last_name:        formData.get('last_name'),
    date_of_birth:    formData.get('date_of_birth'),
    gender:           formData.get('gender') || undefined,
    address:          formData.get('address') || undefined,
    phone:            formData.get('phone') || undefined,
    email:            formData.get('email') || undefined,
    insurance_type:   formData.get('insurance_type'),
    insurance_name:   formData.get('insurance_name') || undefined,
    insurance_number: formData.get('insurance_number') || undefined,
    gdpr_consent:     true,
  })
  if (!parsed.success) return { error: parsed.error.errors[0].message }

  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return { error: 'Nicht angemeldet' }

  const { data: profile } = await supabase
    .from('profiles').select('praxis_id').eq('id', user.id).single()
  if (!profile) return { error: 'Profil nicht gefunden' }

  const { data: patient, error } = await supabase
    .from('patients')
    .insert({
      ...parsed.data,
      praxis_id: profile.praxis_id,
      gdpr_consent: true,
      gdpr_consent_date: new Date().toISOString(),
      created_by: user.id,
    })
    .select()
    .single()

  if (error || !patient) return { error: 'Patient konnte nicht angelegt werden' }

  await supabase.from('consent_records').insert([
    { patient_id: patient.id, praxis_id: profile.praxis_id, consent_type: 'behandlung' },
    { patient_id: patient.id, praxis_id: profile.praxis_id, consent_type: 'datenspeicherung' },
  ])

  revalidatePath('/patienten')
  redirect(`/patienten/${patient.id}`)
}

export async function updatePatientAction(
  patientId: string,
  formData: FormData,
): Promise<ActionResult> {
  const parsed = patientSchema.partial().safeParse({
    first_name:       formData.get('first_name'),
    last_name:        formData.get('last_name'),
    date_of_birth:    formData.get('date_of_birth'),
    gender:           formData.get('gender') || undefined,
    address:          formData.get('address') || undefined,
    phone:            formData.get('phone') || undefined,
    email:            formData.get('email') || undefined,
    insurance_type:   formData.get('insurance_type'),
    insurance_name:   formData.get('insurance_name') || undefined,
    insurance_number: formData.get('insurance_number') || undefined,
  })
  if (!parsed.success) return { error: parsed.error.errors[0].message }

  const supabase = await createClient()
  const { error } = await supabase
    .from('patients').update(parsed.data).eq('id', patientId)
  if (error) return { error: 'Aktualisierung fehlgeschlagen' }

  revalidatePath(`/patienten/${patientId}`)
}

export async function anonymizePatientAction(patientId: string): Promise<ActionResult> {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return { error: 'Nicht angemeldet' }

  const { error } = await supabase
    .from('patients')
    .update({
      first_name: 'Gelöschter',
      last_name: 'Patient',
      date_of_birth: '1900-01-01',
      address: null, phone: null, email: null,
      insurance_number: null,
      gdpr_consent: false,
      deleted_at: new Date().toISOString(),
      deleted_by: user.id,
    })
    .eq('id', patientId)

  if (error) return { error: 'Löschen fehlgeschlagen' }

  revalidatePath('/patienten')
  redirect('/patienten')
}

export async function addDiagnoseAction(
  patientId: string,
  praxisId: string,
  formData: FormData,
): Promise<ActionResult> {
  const parsed = diagnoseSchema.safeParse({
    icd10_code:   formData.get('icd10_code'),
    description:  formData.get('description'),
    is_primary:   formData.get('is_primary') === 'true',
    diagnosed_at: formData.get('diagnosed_at'),
  })
  if (!parsed.success) return { error: parsed.error.errors[0].message }

  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return { error: 'Nicht angemeldet' }

  const { error } = await supabase.from('diagnoses').insert({
    ...parsed.data,
    patient_id: patientId,
    praxis_id: praxisId,
    created_by: user.id,
  })

  if (error) return { error: 'Diagnose konnte nicht gespeichert werden' }
  revalidatePath(`/patienten/${patientId}`)
}

export async function addTherapyGoalAction(
  patientId: string,
  praxisId: string,
  formData: FormData,
): Promise<ActionResult> {
  const parsed = therapyGoalSchema.safeParse({
    title:       formData.get('title'),
    description: formData.get('description') || undefined,
    target_date: formData.get('target_date') || undefined,
    status:      formData.get('status') || 'offen',
  })
  if (!parsed.success) return { error: parsed.error.errors[0].message }

  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return { error: 'Nicht angemeldet' }

  const { error } = await supabase.from('therapy_goals').insert({
    ...parsed.data,
    target_date: parsed.data.target_date || null,
    patient_id: patientId,
    praxis_id: praxisId,
    created_by: user.id,
  })

  if (error) return { error: 'Ziel konnte nicht gespeichert werden' }
  revalidatePath(`/patienten/${patientId}`)
}

export async function updateGoalStatusAction(
  goalId: string,
  patientId: string,
  status: string,
): Promise<ActionResult> {
  const parsed = z.enum(['offen', 'in_bearbeitung', 'erreicht', 'aufgegeben']).safeParse(status)
  if (!parsed.success) return { error: 'Ungültiger Status' }

  const supabase = await createClient()
  const { error } = await supabase
    .from('therapy_goals').update({ status: parsed.data }).eq('id', goalId)
  if (error) return { error: 'Status konnte nicht aktualisiert werden' }

  revalidatePath(`/patienten/${patientId}`)
}
```

- [ ] **Step 4: Tests ausführen**

```bash
cd frontend && npm test src/features/patients/__tests__/actions.test.ts
```
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/patients/actions.ts frontend/src/features/patients/__tests__/
git commit -m "feat(patients): add server actions (create, update, anonymize, diagnoses, goals)"
```

---

## Task 10: Patientenliste

**Files:**
- Create: `frontend/src/features/patients/PatientList.tsx`
- Create: `frontend/src/app/(praxis)/patienten/page.tsx`

- [ ] **Step 1: `frontend/src/features/patients/PatientList.tsx` schreiben**

```typescript
import Link from 'next/link'
import type { Database } from '@/lib/types/database'

type Patient = Database['public']['Tables']['patients']['Row']

interface PatientListProps {
  patients: Patient[]
}

const statusColors: Record<string, string> = {
  aktiv: 'bg-green-100 text-green-800',
  pausiert: 'bg-yellow-100 text-yellow-800',
  abgeschlossen: 'bg-gray-100 text-gray-700',
}

export function PatientList({ patients }: PatientListProps) {
  if (patients.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        <p>Noch keine Patienten angelegt.</p>
        <Link href="/patienten/neu"
          className="mt-4 inline-block text-blue-600 hover:underline text-sm">
          Ersten Patienten anlegen →
        </Link>
      </div>
    )
  }

  return (
    <div className="overflow-hidden shadow ring-1 ring-black ring-opacity-5 rounded-lg">
      <table className="min-w-full divide-y divide-gray-300">
        <thead className="bg-gray-50">
          <tr>
            <th className="py-3 pl-4 pr-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Name</th>
            <th className="px-3 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Geb.-Datum</th>
            <th className="px-3 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Versicherung</th>
            <th className="px-3 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Status</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200 bg-white">
          {patients.map(patient => (
            <tr key={patient.id} className="hover:bg-gray-50">
              <td className="py-3 pl-4 pr-3">
                <Link href={`/patienten/${patient.id}`}
                  className="font-medium text-blue-600 hover:underline">
                  {patient.last_name}, {patient.first_name}
                </Link>
              </td>
              <td className="px-3 py-3 text-sm text-gray-700">
                {new Date(patient.date_of_birth).toLocaleDateString('de-DE')}
              </td>
              <td className="px-3 py-3 text-sm text-gray-700">{patient.insurance_type}</td>
              <td className="px-3 py-3">
                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusColors[patient.status]}`}>
                  {patient.status}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
```

- [ ] **Step 2: `frontend/src/app/(praxis)/patienten/page.tsx` schreiben**

```typescript
import { createClient } from '@/lib/supabase/server'
import { PatientList } from '@/features/patients/PatientList'
import Link from 'next/link'

export default async function PatientenPage() {
  const supabase = await createClient()

  const { data: patients } = await supabase
    .from('patients')
    .select('*')
    .is('deleted_at', null)
    .order('last_name')

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-gray-900">Patienten</h1>
        <Link href="/patienten/neu"
          className="inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700">
          + Neuer Patient
        </Link>
      </div>
      <PatientList patients={patients ?? []} />
    </div>
  )
}
```

- [ ] **Step 3: Test — PatientList rendert korrekt**

`frontend/src/features/patients/__tests__/PatientList.test.tsx`:

```typescript
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { PatientList } from '../PatientList'

vi.mock('next/link', () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) =>
    <a href={href}>{children}</a>,
}))

const mockPatients = [
  {
    id: 'p1', praxis_id: 'pr1',
    first_name: 'Anna', last_name: 'Schmidt',
    date_of_birth: '1985-03-15',
    gender: 'w' as const,
    address: null, phone: null, email: null,
    insurance_type: 'GKV' as const,
    insurance_name: 'AOK', insurance_number: null,
    status: 'aktiv' as const,
    gdpr_consent: true, gdpr_consent_date: null,
    created_at: '2026-01-01', updated_at: '2026-01-01',
    created_by: null, deleted_at: null, deleted_by: null,
  },
]

describe('PatientList', () => {
  it('renders patient name as link', () => {
    render(<PatientList patients={mockPatients} />)
    expect(screen.getByText('Schmidt, Anna')).toBeInTheDocument()
  })

  it('shows empty state when no patients', () => {
    render(<PatientList patients={[]} />)
    expect(screen.getByText(/Noch keine Patienten/)).toBeInTheDocument()
  })

  it('displays insurance type', () => {
    render(<PatientList patients={mockPatients} />)
    expect(screen.getByText('GKV')).toBeInTheDocument()
  })
})
```

- [ ] **Step 4: Test ausführen**

```bash
cd frontend && npm test src/features/patients/__tests__/PatientList.test.tsx
```
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/patients/PatientList.tsx frontend/src/app/\(praxis\)/patienten/
git commit -m "feat(patients): add patient list page"
```

---

## Task 11: Patient anlegen (Formular)

**Files:**
- Create: `frontend/src/features/patients/PatientForm.tsx`
- Create: `frontend/src/app/(praxis)/patienten/neu/page.tsx`

- [ ] **Step 1: `frontend/src/features/patients/PatientForm.tsx` schreiben**

```typescript
'use client'

import { useActionState } from 'react'
import { createPatientAction } from './actions'

export function PatientForm() {
  const [state, action, isPending] = useActionState(createPatientAction, undefined)

  return (
    <form action={action} className="space-y-6 max-w-2xl">
      {state?.error && (
        <p className="text-sm text-red-600 bg-red-50 p-3 rounded-md">{state.error}</p>
      )}

      <fieldset className="space-y-4">
        <legend className="text-base font-semibold text-gray-900">Stammdaten</legend>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="first_name" className="block text-sm font-medium text-gray-700">Vorname *</label>
            <input id="first_name" name="first_name" type="text" required
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 sm:text-sm" />
          </div>
          <div>
            <label htmlFor="last_name" className="block text-sm font-medium text-gray-700">Nachname *</label>
            <input id="last_name" name="last_name" type="text" required
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 sm:text-sm" />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="date_of_birth" className="block text-sm font-medium text-gray-700">Geburtsdatum *</label>
            <input id="date_of_birth" name="date_of_birth" type="date" required
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 sm:text-sm" />
          </div>
          <div>
            <label htmlFor="gender" className="block text-sm font-medium text-gray-700">Geschlecht</label>
            <select id="gender" name="gender"
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 sm:text-sm">
              <option value="">— bitte wählen —</option>
              <option value="m">männlich</option>
              <option value="w">weiblich</option>
              <option value="d">divers</option>
            </select>
          </div>
        </div>
        <div>
          <label htmlFor="address" className="block text-sm font-medium text-gray-700">Adresse</label>
          <input id="address" name="address" type="text"
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 sm:text-sm" />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="phone" className="block text-sm font-medium text-gray-700">Telefon</label>
            <input id="phone" name="phone" type="tel"
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 sm:text-sm" />
          </div>
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700">E-Mail</label>
            <input id="email" name="email" type="email"
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 sm:text-sm" />
          </div>
        </div>
      </fieldset>

      <fieldset className="space-y-4">
        <legend className="text-base font-semibold text-gray-900">Versicherung</legend>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="insurance_type" className="block text-sm font-medium text-gray-700">Art *</label>
            <select id="insurance_type" name="insurance_type" required
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 sm:text-sm">
              <option value="GKV">GKV (gesetzlich)</option>
              <option value="PKV">PKV (privat)</option>
              <option value="Selbstzahler">Selbstzahler</option>
            </select>
          </div>
          <div>
            <label htmlFor="insurance_name" className="block text-sm font-medium text-gray-700">Krankenkasse / Versicherung</label>
            <input id="insurance_name" name="insurance_name" type="text"
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 sm:text-sm" />
          </div>
        </div>
        <div>
          <label htmlFor="insurance_number" className="block text-sm font-medium text-gray-700">Versichertennummer</label>
          <input id="insurance_number" name="insurance_number" type="text"
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 sm:text-sm" />
        </div>
      </fieldset>

      <fieldset className="space-y-3">
        <legend className="text-base font-semibold text-gray-900">DSGVO-Einwilligung</legend>
        <label className="flex items-start gap-3 cursor-pointer">
          <input type="checkbox" name="gdpr_consent" value="true" required
            className="mt-0.5 rounded border-gray-300" />
          <span className="text-sm text-gray-700">
            Der Patient willigt in die Speicherung und Verarbeitung seiner personenbezogenen Daten
            zur Durchführung der logopädischen Therapie ein. (Pflichtfeld)
          </span>
        </label>
      </fieldset>

      <div className="flex gap-3">
        <button type="submit" disabled={isPending}
          className="px-6 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50">
          {isPending ? 'Speichern…' : 'Patient anlegen'}
        </button>
        <a href="/patienten" className="px-6 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50">
          Abbrechen
        </a>
      </div>
    </form>
  )
}
```

- [ ] **Step 2: `frontend/src/app/(praxis)/patienten/neu/page.tsx` schreiben**

```typescript
import { PatientForm } from '@/features/patients/PatientForm'

export default function NeuerPatientPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">Neuen Patienten anlegen</h1>
        <p className="mt-1 text-sm text-gray-600">Alle Pflichtfelder mit * ausfüllen.</p>
      </div>
      <PatientForm />
    </div>
  )
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/features/patients/PatientForm.tsx frontend/src/app/\(praxis\)/patienten/neu/
git commit -m "feat(patients): add patient creation form with DSGVO consent"
```

---

## Task 12: Patientenakte (Detail-View mit Tabs)

**Files:**
- Create: `frontend/src/features/patients/PatientAkte.tsx`
- Create: `frontend/src/features/patients/DiagnoseForm.tsx`
- Create: `frontend/src/features/patients/TherapyGoalForm.tsx`
- Create: `frontend/src/app/(praxis)/patienten/[id]/page.tsx`

- [ ] **Step 1: `frontend/src/features/patients/DiagnoseForm.tsx` schreiben**

```typescript
'use client'

import { useActionState } from 'react'
import { addDiagnoseAction } from './actions'

export function DiagnoseForm({ patientId, praxisId }: { patientId: string; praxisId: string }) {
  const action = addDiagnoseAction.bind(null, patientId, praxisId)
  const [state, boundAction, isPending] = useActionState(action, undefined)

  return (
    <form action={boundAction} className="space-y-4 bg-white p-4 border border-gray-200 rounded-lg">
      <h3 className="font-medium text-gray-900">Diagnose hinzufügen</h3>
      {state?.error && <p className="text-sm text-red-600">{state.error}</p>}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label htmlFor="icd10_code" className="block text-sm font-medium text-gray-700">
            ICD-10 Code * <span className="text-gray-400 font-normal">(z.B. R47.0)</span>
          </label>
          <input id="icd10_code" name="icd10_code" type="text" required
            placeholder="R47.0" pattern="^[A-Z]\d{2}(\.\d{1,2})?$"
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 sm:text-sm font-mono" />
        </div>
        <div>
          <label htmlFor="diagnosed_at" className="block text-sm font-medium text-gray-700">Datum *</label>
          <input id="diagnosed_at" name="diagnosed_at" type="date" required
            defaultValue={new Date().toISOString().split('T')[0]}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 sm:text-sm" />
        </div>
      </div>
      <div>
        <label htmlFor="description" className="block text-sm font-medium text-gray-700">Beschreibung *</label>
        <input id="description" name="description" type="text" required
          className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 sm:text-sm" />
      </div>
      <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
        <input type="checkbox" name="is_primary" value="true" className="rounded border-gray-300" />
        Primärdiagnose
      </label>
      <button type="submit" disabled={isPending}
        className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50">
        {isPending ? 'Speichern…' : 'Diagnose speichern'}
      </button>
    </form>
  )
}
```

- [ ] **Step 2: `frontend/src/features/patients/TherapyGoalForm.tsx` schreiben**

```typescript
'use client'

import { useActionState } from 'react'
import { addTherapyGoalAction, updateGoalStatusAction } from './actions'
import type { Database } from '@/lib/types/database'

type Goal = Database['public']['Tables']['therapy_goals']['Row']

export function TherapyGoalForm({ patientId, praxisId }: { patientId: string; praxisId: string }) {
  const action = addTherapyGoalAction.bind(null, patientId, praxisId)
  const [state, boundAction, isPending] = useActionState(action, undefined)

  return (
    <form action={boundAction} className="space-y-4 bg-white p-4 border border-gray-200 rounded-lg">
      <h3 className="font-medium text-gray-900">Ziel hinzufügen</h3>
      {state?.error && <p className="text-sm text-red-600">{state.error}</p>}
      <div>
        <label htmlFor="goal_title" className="block text-sm font-medium text-gray-700">Titel *</label>
        <input id="goal_title" name="title" type="text" required
          className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 sm:text-sm" />
      </div>
      <div>
        <label htmlFor="goal_description" className="block text-sm font-medium text-gray-700">Beschreibung</label>
        <textarea id="goal_description" name="description" rows={2}
          className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 sm:text-sm" />
      </div>
      <div>
        <label htmlFor="target_date" className="block text-sm font-medium text-gray-700">Zieldatum</label>
        <input id="target_date" name="target_date" type="date"
          className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 sm:text-sm" />
      </div>
      <button type="submit" disabled={isPending}
        className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50">
        {isPending ? 'Speichern…' : 'Ziel speichern'}
      </button>
    </form>
  )
}

const statusLabels: Record<Goal['status'], string> = {
  offen: 'Offen',
  in_bearbeitung: 'In Bearbeitung',
  erreicht: 'Erreicht',
  aufgegeben: 'Aufgegeben',
}

const statusColors: Record<Goal['status'], string> = {
  offen: 'bg-gray-100 text-gray-700',
  in_bearbeitung: 'bg-blue-100 text-blue-800',
  erreicht: 'bg-green-100 text-green-800',
  aufgegeben: 'bg-red-100 text-red-700',
}

export function GoalCard({ goal, patientId }: { goal: Goal; patientId: string }) {
  const action = updateGoalStatusAction.bind(null, goal.id, patientId)

  return (
    <div className="bg-white p-4 border border-gray-200 rounded-lg space-y-2">
      <div className="flex items-start justify-between gap-4">
        <p className="font-medium text-gray-900">{goal.title}</p>
        <span className={`shrink-0 px-2 py-0.5 rounded-full text-xs font-medium ${statusColors[goal.status]}`}>
          {statusLabels[goal.status]}
        </span>
      </div>
      {goal.description && <p className="text-sm text-gray-600">{goal.description}</p>}
      {goal.target_date && (
        <p className="text-xs text-gray-500">
          Zieldatum: {new Date(goal.target_date).toLocaleDateString('de-DE')}
        </p>
      )}
      {goal.status !== 'erreicht' && goal.status !== 'aufgegeben' && (
        <form action={action.bind(null, 'erreicht')}>
          <button type="submit" className="text-xs text-green-700 hover:underline">
            Als erreicht markieren
          </button>
        </form>
      )}
    </div>
  )
}
```

- [ ] **Step 3: `frontend/src/app/(praxis)/patienten/[id]/page.tsx` schreiben**

```typescript
import { createClient } from '@/lib/supabase/server'
import { notFound } from 'next/navigation'
import { DiagnoseForm } from '@/features/patients/DiagnoseForm'
import { TherapyGoalForm, GoalCard } from '@/features/patients/TherapyGoalForm'
import { anonymizePatientAction } from '@/features/patients/actions'

export default async function PatientenAktePage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params
  const supabase = await createClient()

  const { data: patient } = await supabase
    .from('patients').select('*').eq('id', id).is('deleted_at', null).single()

  if (!patient) notFound()

  const [{ data: diagnoses }, { data: goals }, { data: profile }] = await Promise.all([
    supabase.from('diagnoses').select('*').eq('patient_id', id).order('diagnosed_at', { ascending: false }),
    supabase.from('therapy_goals').select('*').eq('patient_id', id).order('created_at', { ascending: false }),
    supabase.from('profiles').select('praxis_id, role').single(),
  ])

  const praxisId = profile?.praxis_id ?? ''
  const isAdmin = profile?.role === 'admin'

  const deleteAction = anonymizePatientAction.bind(null, id)

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">
            {patient.last_name}, {patient.first_name}
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            * {new Date(patient.date_of_birth).toLocaleDateString('de-DE')} · {patient.insurance_type}
            {patient.insurance_name ? ` (${patient.insurance_name})` : ''}
          </p>
        </div>
        {isAdmin && (
          <form action={deleteAction}
            onSubmit={e => !confirm('Patient wirklich anonymisieren? Dies kann nicht rückgängig gemacht werden.') && e.preventDefault()}>
            <button type="submit"
              className="text-sm text-red-600 hover:underline border border-red-200 px-3 py-1 rounded-md hover:bg-red-50">
              Patient löschen (DSGVO)
            </button>
          </form>
        )}
      </div>

      {/* Diagnosen */}
      <section className="space-y-4">
        <h2 className="text-lg font-medium text-gray-900">Diagnosen (ICD-10)</h2>
        {(diagnoses ?? []).length > 0 ? (
          <div className="overflow-hidden shadow ring-1 ring-black ring-opacity-5 rounded-lg">
            <table className="min-w-full divide-y divide-gray-300">
              <thead className="bg-gray-50">
                <tr>
                  <th className="py-2 pl-4 text-left text-xs font-semibold text-gray-500 uppercase">Code</th>
                  <th className="py-2 px-3 text-left text-xs font-semibold text-gray-500 uppercase">Beschreibung</th>
                  <th className="py-2 px-3 text-left text-xs font-semibold text-gray-500 uppercase">Datum</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white">
                {(diagnoses ?? []).map(d => (
                  <tr key={d.id}>
                    <td className="py-2 pl-4 font-mono text-sm text-gray-900">
                      {d.icd10_code} {d.is_primary && <span className="text-xs text-blue-600 ml-1">(Primär)</span>}
                    </td>
                    <td className="py-2 px-3 text-sm text-gray-700">{d.description}</td>
                    <td className="py-2 px-3 text-sm text-gray-500">
                      {new Date(d.diagnosed_at).toLocaleDateString('de-DE')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-gray-500">Noch keine Diagnosen.</p>
        )}
        <DiagnoseForm patientId={id} praxisId={praxisId} />
      </section>

      {/* Therapieziele */}
      <section className="space-y-4">
        <h2 className="text-lg font-medium text-gray-900">Therapieziele</h2>
        {(goals ?? []).length > 0 ? (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {(goals ?? []).map(g => <GoalCard key={g.id} goal={g} patientId={id} />)}
          </div>
        ) : (
          <p className="text-sm text-gray-500">Noch keine Ziele definiert.</p>
        )}
        <TherapyGoalForm patientId={id} praxisId={praxisId} />
      </section>
    </div>
  )
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/features/patients/ frontend/src/app/\(praxis\)/patienten/\[id\]/
git commit -m "feat(patients): add patient detail view with diagnoses and therapy goals"
```

---

## Task 13: Dashboard

**Files:**
- Create: `frontend/src/app/(praxis)/dashboard/page.tsx`

- [ ] **Step 1: `frontend/src/app/(praxis)/dashboard/page.tsx` schreiben**

```typescript
import { createClient } from '@/lib/supabase/server'
import Link from 'next/link'

export default async function DashboardPage() {
  const supabase = await createClient()

  const [{ count: patientCount }, { count: activeCount }] = await Promise.all([
    supabase.from('patients').select('*', { count: 'exact', head: true }).is('deleted_at', null),
    supabase.from('patients').select('*', { count: 'exact', head: true }).eq('status', 'aktiv').is('deleted_at', null),
  ])

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-gray-900">Dashboard</h1>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-sm font-medium text-gray-500">Patienten gesamt</p>
          <p className="mt-2 text-3xl font-semibold text-gray-900">{patientCount ?? 0}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-sm font-medium text-gray-500">Aktive Patienten</p>
          <p className="mt-2 text-3xl font-semibold text-green-600">{activeCount ?? 0}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6 flex flex-col justify-between">
          <p className="text-sm font-medium text-gray-500">Schnellzugriff</p>
          <Link href="/patienten/neu"
            className="mt-4 text-sm text-blue-600 hover:underline">
            + Neuen Patienten anlegen →
          </Link>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/app/\(praxis\)/dashboard/
git commit -m "feat(dashboard): add patient count stats"
```

---

## Task 14: FastAPI AI-Service mit abstrahierter Provider-Schicht (ADR-P1)

> **Warum neu statt portieren:** Groq ist US-basiert und darf gemäß ADR-P1 keine rohen
> Patientendaten empfangen (§203 StGB, DSGVO). Stattdessen wird eine `AIProvider`-Schnittstelle
> implementiert: `LocalProvider` (faster-whisper + Ollama, läuft auf der Praxis-Hardware)
> als Default, `CloudProvider` (Mistral AI EU, Paris) als opt-in via `AI_PROVIDER=cloud`.

**Files:**
- Create: `backend/main.py`
- Create: `backend/requirements.txt`
- Create: `backend/services/ai_provider.py`
- Create: `backend/services/report_service.py`
- Create: `backend/routers/sessions.py`
- Create: `backend/models/schemas.py`
- Create: `backend/tests/test_ai_provider.py`

---

### Step 1: Failing tests schreiben

Datei: `backend/tests/test_ai_provider.py`

```python
import pytest
from unittest.mock import patch, MagicMock
import os

def test_local_provider_is_default(monkeypatch):
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    from services.ai_provider import get_provider, LocalProvider
    provider = get_provider()
    assert isinstance(provider, LocalProvider)

def test_cloud_provider_selected_via_env(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "cloud")
    monkeypatch.setenv("MISTRAL_API_KEY", "test-key")
    # Reload module to pick up env change
    import importlib
    import services.ai_provider as mod
    importlib.reload(mod)
    from services.ai_provider import get_provider, CloudProvider
    provider = get_provider()
    assert isinstance(provider, CloudProvider)

def test_provider_interface_has_required_methods():
    from services.ai_provider import AIProvider
    import inspect
    methods = [m for m, _ in inspect.getmembers(AIProvider, predicate=inspect.isfunction)]
    assert "transcribe" in methods
    assert "generate" in methods

def test_local_provider_transcribe_calls_faster_whisper(monkeypatch):
    mock_model = MagicMock()
    mock_model.transcribe.return_value = (
        [MagicMock(text=" Hallo Welt")],
        MagicMock()
    )
    with patch("services.ai_provider.WhisperModel", return_value=mock_model):
        from services.ai_provider import LocalProvider
        provider = LocalProvider()
        result = provider.transcribe(b"fake-audio-bytes", "de")
        assert result == "Hallo Welt"

def test_cloud_provider_transcribe_calls_mistral(monkeypatch):
    monkeypatch.setenv("MISTRAL_API_KEY", "test-key")
    mock_client = MagicMock()
    mock_client.audio.transcriptions.create.return_value = MagicMock(text="Hallo Welt")
    with patch("services.ai_provider.Mistral", return_value=mock_client):
        from services.ai_provider import CloudProvider
        provider = CloudProvider()
        result = provider.transcribe(b"fake-audio-bytes", "de")
        assert result == "Hallo Welt"

def test_generate_raises_if_no_ollama(monkeypatch):
    import httpx
    with patch("services.ai_provider.httpx.post", side_effect=httpx.ConnectError("no ollama")):
        from services.ai_provider import LocalProvider
        provider = LocalProvider()
        with pytest.raises(RuntimeError, match="Ollama"):
            provider.generate("Schreibe einen Bericht.")
```

Tests laufen lassen (müssen alle **FAIL**):

```bash
cd backend && python -m pytest tests/test_ai_provider.py -v
```

Expected: `FAILED` für alle 6 Tests (Module nicht gefunden).

---

### Step 2: `backend/requirements.txt` schreiben

```
fastapi==0.115.0
uvicorn[standard]==0.32.0
faster-whisper==1.0.3
httpx==0.27.0
mistralai==1.2.0
python-multipart==0.0.12
pydantic==2.9.0
pytest==8.3.0
pytest-asyncio==0.24.0
```

> `faster-whisper` ersetzt `groq` für STT. Ollama läuft als lokaler HTTP-Server
> (kein Python-Package nötig — httpx reicht für die REST-API). `mistralai` für CloudProvider.

---

### Step 3: `backend/services/ai_provider.py` implementieren

```python
from __future__ import annotations
import os
import io
import httpx
from abc import ABC, abstractmethod


class AIProvider(ABC):
    @abstractmethod
    def transcribe(self, audio_bytes: bytes, language: str = "de") -> str:
        """Audio-Bytes → Transkript-Text."""

    @abstractmethod
    def generate(self, prompt: str, system: str = "") -> str:
        """Prompt → generierter Text."""


class LocalProvider(AIProvider):
    """STT: faster-whisper (lokal). NLP: Ollama + Llama (lokal, HTTP)."""

    WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")
    OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

    def __init__(self) -> None:
        from faster_whisper import WhisperModel  # lazy import
        self._whisper = WhisperModel(self.WHISPER_MODEL, device="cpu", compute_type="int8")

    def transcribe(self, audio_bytes: bytes, language: str = "de") -> str:
        segments, _ = self._whisper.transcribe(
            io.BytesIO(audio_bytes), language=language
        )
        return "".join(s.text for s in segments).strip()

    def generate(self, prompt: str, system: str = "") -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        try:
            response = httpx.post(
                f"{self.OLLAMA_URL}/api/chat",
                json={"model": self.OLLAMA_MODEL, "messages": messages, "stream": False},
                timeout=120.0,
            )
            response.raise_for_status()
            return response.json()["message"]["content"]
        except httpx.ConnectError as e:
            raise RuntimeError(
                f"Ollama nicht erreichbar unter {self.OLLAMA_URL}. "
                "Starte Ollama mit: `ollama serve`"
            ) from e


class CloudProvider(AIProvider):
    """STT + NLP: Mistral AI (Paris, EU-DSGVO-konform). Kein Patientenname in Prompts!"""

    MISTRAL_MODEL = os.getenv("MISTRAL_MODEL", "mistral-large-latest")

    def __init__(self) -> None:
        from mistralai import Mistral  # lazy import
        api_key = os.environ["MISTRAL_API_KEY"]
        self._client = Mistral(api_key=api_key)

    def transcribe(self, audio_bytes: bytes, language: str = "de") -> str:
        # Mistral nutzt aktuell Whisper-kompatibles Endpoint
        result = self._client.audio.transcriptions.create(
            model="whisper-large-v3",
            file=("audio.wav", audio_bytes),
            language=language,
        )
        return result.text

    def generate(self, prompt: str, system: str = "") -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = self._client.chat.complete(
            model=self.MISTRAL_MODEL,
            messages=messages,
        )
        return response.choices[0].message.content


def get_provider() -> AIProvider:
    """Factory: liest AI_PROVIDER env-var. Default: LocalProvider."""
    provider_name = os.getenv("AI_PROVIDER", "local").lower()
    if provider_name == "cloud":
        return CloudProvider()
    return LocalProvider()
```

---

### Step 4: `backend/main.py` schreiben

```python
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import sessions

app = FastAPI(title="Logopädie-Praxis AI Service", version="1.0.0")

origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sessions.router, prefix="/sessions", tags=["sessions"])

@app.get("/health")
def health():
    return {"status": "ok", "provider": os.getenv("AI_PROVIDER", "local")}
```

---

### Step 5: `backend/routers/sessions.py` schreiben

```python
import os
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from services.ai_provider import get_provider

router = APIRouter()

class TranscribeResponse(BaseModel):
    transcript: str

class GenerateRequest(BaseModel):
    prompt: str
    system: str = ""

class GenerateResponse(BaseModel):
    text: str

@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(file: UploadFile = File(...)):
    audio_bytes = await file.read()
    if len(audio_bytes) > 25 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Audio-Datei zu groß (max 25 MB)")
    provider = get_provider()
    transcript = provider.transcribe(audio_bytes)
    return TranscribeResponse(transcript=transcript)

@router.post("/generate", response_model=GenerateResponse)
async def generate_report(body: GenerateRequest):
    provider = get_provider()
    text = provider.generate(body.prompt, body.system)
    return GenerateResponse(text=text)
```

---

### Step 6: Tests laufen lassen (müssen alle **PASS**)

```bash
cd backend && python -m pytest tests/test_ai_provider.py -v
```

Expected: `6 passed`

---

### Step 7: Backend manuell starten und testen

```bash
cd backend && pip install -r requirements.txt
# LocalProvider (kein MISTRAL_API_KEY nötig, aber Ollama muss laufen):
uvicorn main:app --reload --port 8001
curl http://localhost:8001/health
```

Expected: `{"status": "ok", "provider": "local"}`

```bash
# CloudProvider testen:
AI_PROVIDER=cloud MISTRAL_API_KEY=... uvicorn main:app --reload --port 8001
curl http://localhost:8001/health
```

Expected: `{"status": "ok", "provider": "cloud"}`

---

### Step 8: `.env.example` aktualisieren

```bash
# backend/.env.example
AI_PROVIDER=local            # "local" (default) oder "cloud"
WHISPER_MODEL=base           # base | small | medium | large-v3 (mehr RAM)
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b     # llama3.2:3b (CPU) oder llama3.3:70b (GPU)
MISTRAL_API_KEY=             # nur wenn AI_PROVIDER=cloud
ALLOWED_ORIGINS=http://localhost:3000
```

---

### Step 9: Commit

```bash
git add backend/
git commit -m "feat(backend): implement abstracted AI provider — LocalProvider (faster-whisper + Ollama) + CloudProvider (Mistral EU)"
```

---

## Task 15: CI + Vercel Config

**Files:**
- Create: `.github/workflows/ci.yml`
- Create: `vercel.json`

- [ ] **Step 1: `.github/workflows/ci.yml` schreiben**

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  frontend-typecheck:
    name: TypeScript Check
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20', cache: 'npm', cache-dependency-path: frontend/package-lock.json }
      - run: npm ci
        working-directory: frontend
      - run: npx tsc --noEmit
        working-directory: frontend

  frontend-lint:
    name: ESLint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20', cache: 'npm', cache-dependency-path: frontend/package-lock.json }
      - run: npm ci
        working-directory: frontend
      - run: npm run lint
        working-directory: frontend

  frontend-test:
    name: Vitest
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20', cache: 'npm', cache-dependency-path: frontend/package-lock.json }
      - run: npm ci
        working-directory: frontend
      - run: npm test
        working-directory: frontend

  backend-lint:
    name: Ruff
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install ruff
      - run: ruff check .
        working-directory: backend

  backend-test:
    name: Pytest
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install -r requirements.txt
        working-directory: backend
      - run: python -m pytest
        working-directory: backend
        env:
          GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}
```

- [ ] **Step 2: `vercel.json` schreiben**

```json
{
  "version": 2,
  "builds": [
    {
      "src": "frontend/package.json",
      "use": "@vercel/next"
    }
  ],
  "routes": [
    {
      "src": "/api/ai/(.*)",
      "dest": "http://localhost:8001/$1"
    }
  ]
}
```

> **Hinweis:** Das Backend muss auf Vercel als separater Service laufen oder auf einem anderen Host (z.B. Railway, Fly.io). Vercel kann kein FastAPI hosten. Empfehlung: Backend separat auf Railway deployen, URL als `NEXT_PUBLIC_API_URL` setzen.

- [ ] **Step 3: Commit + Push**

```bash
git add .github/ vercel.json
git commit -m "chore: add CI workflow and Vercel config"
git push -u origin main
```

- [ ] **Step 4: CI-Status im GitHub prüfen**

Actions → alle 5 Jobs sollten grün werden.

---

## Self-Review

**Spec-Abdeckung:**

| Spec-Anforderung | Task |
|---|---|
| praxen, profiles Tabellen | Task 3 |
| patients Tabelle | Task 3 |
| diagnoses, therapy_goals, patient_documents | Task 3 |
| consent_records, audit_logs | Task 3 |
| RLS Policies | Task 4 |
| Audit-Trigger | Task 4 |
| Supabase Client (browser + server) | Task 2 |
| TypeScript Database-Typen | Task 2 |
| ICD-10 Regex-Validierung `/^[A-Z]\d{2}(\.\d{1,2})?$/` | Task 8 |
| Login-Page | Task 6 |
| Register (Praxis + Admin) | Task 6 |
| Auth Middleware (Redirect) | Task 5 |
| Patientenliste | Task 10 |
| Patient anlegen mit DSGVO-Consent | Task 11 |
| Patientenakte: Diagnosen | Task 12 |
| Patientenakte: Therapieziele | Task 12 |
| Soft-Delete / Anonymisierung | Task 9 + Task 12 |
| Audit-Log (insert consent_records) | Task 9 (createPatientAction) |
| FastAPI AI-Service portiert | Task 14 |
| CI | Task 15 |
| Sidebar zeigt nur rollengerechte Items | Task 7 |
| Dashboard mit Patientenanzahl | Task 13 |

**Was NICHT in diesem Plan ist (bewusst — Baustein 2+):**
- `patient_documents` CRUD-UI (AI-Dokumente)
- `consent_records` UI (Widerruf, Übersicht)
- `/einstellungen` Seite (Benutzer verwalten)
- Supabase Storage (Datei-Uploads)
- FastAPI ↔ Supabase Schreibpfad (AI-Dokumente in `patient_documents`)

**Placeholder-Scan:** Keine TBD/TODO im Plan. Alle Code-Blöcke vollständig.

**Typ-Konsistenz:** `PatientStatus`, `InsuranceType`, `Gender`, `UserRole`, `GoalStatus`, `DocumentType` — in `database.ts` (Task 2) definiert und konsistent in allen nachfolgenden Tasks verwendet.
