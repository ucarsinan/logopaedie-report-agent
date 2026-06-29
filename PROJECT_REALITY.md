# PROJECT_REALITY

Last audit: 2026-06-29
Recommendation: continue
Confidence: high

## Core Problem
- Problem: Logopaedinnen brauchen weniger manuelle Dokumentationsarbeit fuer Anamnese, Berichte, SOAP-Notizen, Therapieplaene und phonologische Auswertungen.
- Affected user: Sprachtherapeutinnen/Logopaedinnen; aktuell primaer Portfolio-/MVP-Publikum, nicht echte Praxisproduktion.
- Painful current workflow: Mitschreiben, Strukturieren, Berichtstypen formulieren, PDF/Verlauf/Aktenbezug pflegen.
- Desired real-world outcome: Ein Demo-System zeigt glaubhaft, wie ein AI-gestuetzter Dokumentationsassistent Zeit spart und strukturierte Entwuerfe erzeugt.
- Success criteria: Live-Demo startet, Kernflows funktionieren mit Testdaten, Praesentationsclaims sind belegbar, keine reale Nutzung mit Patientendaten solange Groq/Vercel/Neon/Upstash-Architektur nicht rechtlich freigegeben ist.

## Current State
- Implemented: Next.js/FastAPI-Monorepo, BFF, JWT+2FA, Patientenverwaltung mit Feldverschluesselung, Redis-Session-Store, Groq STT/NLP, PDF-Export, CI-Konfiguration, Vercel-Deployment-Kontext.
- Partially implemented: Anamnese-Abschluss/M-6 ist laut `docs/ai/TASKS.md` owner-blocked; Produktreife-Provider-Abstraktion existiert in ADR/Plan, nicht im Code.
- Not verified: Echter Groq/Neon/Upstash-Demo-Report auf Vercel, echter neuer Vercel-Preview-Deploy nach dem BFF-Fallback-Fix, echte Praxis-Compliance, echte Nutzerzeitersparnis.
- Last stopping point: Canonical local verification via `scripts/verify.sh` is green; Vercel-Preview-Build lokal erfolgreich; BFF nutzt auf Vercel ohne explizites `BACKEND_URL` jetzt same-origin `/api`. Kein externer Deploy ausgefuehrt.

## Reality Findings
- Local evidence: Repo ist ein fortgeschrittener Portfolio-Demo-Prototyp. `docs/ai/PROJECT.md` markiert Status als Portfolio/Demo; `backend/services/groq_client.py` bindet Groq direkt; die oeffentliche Copy wurde auf Demo-/Roadmap-Claims korrigiert und mit Praesentations-/Q&A-Quelle committed.
- External sources: GDPR Art. 9 behandelt Gesundheitsdaten als besondere Kategorie; Groq dokumentiert, dass Inference-Daten zwar standardmaessig nicht behalten werden, aber fuer Reliability/Abuse bis 30 Tage gespeichert werden koennen, ZDR optional ist, und retained customer data in US-GCP-Buckets liegt.
- Best-practice implications: Portfolio-Demo mit synthetischen Daten ist plausibel. Echter Praxiseinsatz braucht vor Feature-Ausbau zuerst Provider-/Hosting-/DPA-/ZDR-/EU- oder Lokalstrategie, medizinische Review-Gates und klare KI-Entwurfskennzeichnung.
- Key uncertainty: Ob echte Groq-basierte Reportgenerierung in Produktion aktuell robust ist, wurde bewusst nicht getestet, um keine realen externen AI-Calls aus dem Smoke auszulösen.

## Gaps And Risks
- Missing essentials: AIProvider oder klare "not implemented yet"-Formulierung in tieferen technischen Plaenen; Abschlusslogik M-6; echter neuer Vercel-Preview-Deploy zur finalen externen Verifikation.
- Luftschloss/drift warnings: Nicht wieder in "Praxiseinsatz", "produktionsreif" oder "100% DSGVO" abrutschen, solange Provider-/Hosting-/Rechtsarchitektur fehlt.
- Risks: Compliance-Ueberclaim, unklare echte Groq-Livequalitaet, Vercel experimentalServices-/Rate-Limit-Risiko, owner-WIP im Anamnese-/Phonologie-Bereich.

## Next Logical Step
1. Step: Mit expliziter Freigabe einen echten Vercel-Preview-Deploy ausfuehren oder auf Owner-Freigabe fuer M-6 warten.
   Why: Die Dirty-Tree-Scopes wurden bewusst gesplittet und gelandet; `scripts/verify.sh` ist als lokaler Ein-Befehl-Check gruen. Der finale externe Nachweis erfordert einen echten Deploy.
   Validation: Bei Deploy-Freigabe ist die Preview-URL `Ready`, `/api/livez` liefert 200, `/api/health` liefert erwartbar 401 ohne Service-Token, Frontend laedt.
   Stop/continue rule: Kein `vercel deploy` ohne explizite menschliche Freigabe. Keine Anamnese-/Phonologie-Dateien anfassen, solange die Owner-WIP-Sperre in `docs/ai/TASKS.md` besteht.

## Do Not Build Yet
- Keine RAG-/VectorDB-, Diktiergeraete-, Praxismanagement- oder neue Feature-Arbeit, solange M-6 owner-blocked ist und die Demo-/Compliance-Grenze nicht fuer echte Praxisnutzung neu entschieden wurde.
- Keine echte Patientendaten-Verarbeitung ueber Groq/Vercel/Neon/Upstash ohne explizite rechtliche/vertragliche Freigabe.

## Source Links
- GDPR Art. 9: https://gdpr-info.eu/art-9-gdpr/
- Groq Your Data in GroqCloud: https://console.groq.com/docs/your-data
