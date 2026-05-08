# Patienten-Integration Design

**Date:** 2026-05-08
**Status:** Approved
**Scope:** 4 targeted frontend changes to connect the Patienten area with the rest of the app

---

## Problem

The Patienten section feels disconnected from the rest of the app. The technical link (`patient_id` on Sessions/Reports) exists but is optional and invisible during actual workflows. Users can complete entire sessions without ever linking a patient, and there is no navigation path from Reports/Sessions back to a patient profile.

---

## Approach: Targeted Integration (4 surgical changes)

No structural nav changes. No global state refactor. Four independent, focused changes that together make the patient link visible and easy to use throughout the app.

**Workflow mode:** Patient-optional with soft nudge at module start. Demo mode remains accessible.

---

## Change 1: Patient-Picker Modal at Module Start

**Affected modules:** `report`, `therapy-plan`, `soap`, `phonology`
**Not affected:** `compare`, `suggest`, `history` (operate on existing reports)

**Behavior:**
- When a module opens without `?patient=` in the URL, a modal appears immediately
- Uses the existing `PatientSelector` component (already in `features/chat/PatientSelector.tsx`)
- Shows a search input + last 2–3 recently used patients for quick selection
- On patient selection: URL updates to `?patient={id}`, modal closes, session starts with `patient_id`
- "Demo-Modus: Ohne Patient fortfahren" as a secondary text link at the bottom

**Files to change:**
- `frontend/src/app/module/report/page.tsx`
- `frontend/src/app/module/therapy-plan/page.tsx`
- `frontend/src/app/module/soap/page.tsx`
- `frontend/src/app/module/phonology/page.tsx`
- New component: `frontend/src/features/patients/PatientPickerModal.tsx`

---

## Change 2: PatientContextBar in Module Layout

**Behavior:**
- `module/layout.tsx` reads `patient_id` from URL search params
- If present: fetches patient data via `GET /patients/{id}` and renders `PatientContextBar`
- Bar shows: avatar initial, name, system_id, disorder hint, "Profil ansehen →" link to `/patienten/{id}`
- If no `patient_id` (Demo mode): no bar, no banner — the picker at start already communicated this

**Files to change:**
- `frontend/src/app/module/layout.tsx`
- New component: `frontend/src/features/patients/PatientContextBar.tsx`

---

## Change 3: Patient Chips + Filter in History Module

**Behavior:**
- Each report card shows a patient chip (blue badge with name) if `patient_id` is set
- Reports without a patient show a yellow "Demo" badge
- Patient chip is clickable → navigates to `/patienten/{id}`
- New filter toggle above the list: **Alle · Mit Patient · Ohne Patient**
- Filter is client-side on the already-loaded dataset — no new API endpoint

**Backend change:**
- `GET /reports` response: include `patient_pseudonym` alongside `patient_id` so the frontend does not need to batch-fetch patient names

**Files to change:**
- `frontend/src/features/history/HistoryModule.tsx`
- `backend/routers/reports.py` — add `patient_pseudonym` to report response
- `backend/models/` — update ReportListItem schema

---

## Change 4: Quick-Action Grid in PatientDetail

**Behavior:**
- `PatientDetail.tsx` gets a 2×2 Quick-Action grid placed directly after Stammdaten, before Verlauf
- 4 actions: Neuer Bericht, Therapieplan, SOAP-Notes, Phonologie
- Each links to the respective module with `?patient={id}` pre-filled
- The existing "Bericht starten" button is removed (replaced by this grid)
- Reine Frontend-Änderung — no new API endpoint

**Files to change:**
- `frontend/src/features/patients/PatientDetail.tsx`
- New component: `frontend/src/features/patients/PatientQuickActions.tsx`

---

## Change 5: Dashboard — "Zuletzt bearbeitet" mit Patienten-Karten

**Behavior:**
- The existing "recent sessions/reports" section on the dashboard shows patient name + disorder + date instead of anonymous session IDs
- Each card links to the patient profile (if patient linked) or directly to the report (if Demo)
- Reports without a patient show a neutral "Demo" label

**Files to change:**
- `frontend/src/app/page.tsx` (or dashboard component — to be confirmed during implementation)

---

## Out of Scope

- Global "active patient" state across the entire app (Approach 2 — future enhancement)
- Patient-first mandatory workflow (Approach A — rejected in favour of soft nudge)

---

## Summary of New Components

| Component | Location | Purpose |
|---|---|---|
| `PatientPickerModal` | `features/patients/` | Modal at module start for patient selection |
| `PatientContextBar` | `features/patients/` | Persistent patient chip in module layout |
| `PatientQuickActions` | `features/patients/` | 2×2 action grid in PatientDetail |

## Summary of Changed Files

| File | Change |
|---|---|
| `app/module/layout.tsx` | Read `patient_id`, render `PatientContextBar` |
| `app/module/report/page.tsx` | Show `PatientPickerModal` if no patient |
| `app/module/therapy-plan/page.tsx` | Show `PatientPickerModal` if no patient |
| `app/module/soap/page.tsx` | Show `PatientPickerModal` if no patient |
| `app/module/phonology/page.tsx` | Show `PatientPickerModal` if no patient |
| `features/history/HistoryModule.tsx` | Patient chips + filter toggle |
| `features/patients/PatientDetail.tsx` | Replace single button with `PatientQuickActions` |
| `backend/routers/reports.py` | Add `patient_pseudonym` to report list response |
| `app/page.tsx` (dashboard) | Patient-Karten in "Zuletzt bearbeitet" |
