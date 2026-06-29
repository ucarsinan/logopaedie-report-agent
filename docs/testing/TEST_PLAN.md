# TEST_PLAN.md — Manueller Testplan

> Version: 1.0 — 2026-06-03
> Testdaten: siehe `TEST_DATA.md`
> Ergebnisse eintragen in: `TEST_REPORT.md`

**Legende:**

| Symbol | Bedeutung |
|---|---|
| **Vorbedingung** | Muss erfüllt sein, bevor der Test startet |
| **Schritte** | Nummerierte Aktionen |
| **Erwartet** | Was korrekt aussehen soll |
| **Prio** | P1 = kritisch · P2 = wichtig · P3 = nice-to-have |

---

## Abschnitt AUTH — Authentifizierung

### TC-AUTH-001 — Registrierung (Happy Path)

**Prio:** P1 | **Feature:** Register

**Vorbedingung:** App läuft (`./dev.sh`), noch kein Konto mit dieser E-Mail.

**Schritte:**
1. Öffne `http://localhost:3000/register`
2. Fülle aus: Name `Anna Müller`, E-Mail `anna.mueller@logopaedie-test.de`, Passwort `Test1234!Demo`
3. Klicke "Registrieren"

**Erwartet:**
- Weiterleitung oder Meldung "Bitte verifiziere deine E-Mail"
- Im Terminal-Log: `POST /auth/register` → 200 oder 201
- E-Mail-Verifizierungslink wird gesendet (SMTP konfiguriert) oder im Backend-Log sichtbar

---

### TC-AUTH-002 — E-Mail-Verifizierung

**Prio:** P1 | **Feature:** Verify Email

**Vorbedingung:** TC-AUTH-001 abgeschlossen, Verifizierungslink liegt vor.

**Schritte:**
1. Öffne den Verifizierungslink aus der E-Mail (oder Backend-Log)
2. Warte auf Weiterleitung

**Erwartet:**
- Seite `/verify-email` zeigt Erfolgsmeldung
- Danach: Login mit dem Konto möglich

---

### TC-AUTH-003 — Login (Happy Path)

**Prio:** P1 | **Feature:** Login

**Vorbedingung:** Konto `anna.mueller@logopaedie-test.de` ist verifiziert.

**Schritte:**
1. Öffne `http://localhost:3000/login`
2. E-Mail und Passwort eingeben
3. Klicke "Anmelden"

**Erwartet:**
- Weiterleitung auf das Dashboard / Berichteübersicht
- Kein Fehler im UI
- `access_token` Cookie gesetzt (DevTools → Application → Cookies)

---

### TC-AUTH-004 — Login mit falschem Passwort

**Prio:** P1 | **Feature:** Login — Error Handling

**Schritte:**
1. Öffne `/login`
2. Gib richtige E-Mail, aber falsches Passwort `Falsch1234!` ein
3. Klicke "Anmelden"

**Erwartet:**
- Fehlermeldung im UI: "Ungültige Anmeldedaten" o.ä.
- Kein Token gesetzt
- Backend-Log: 401

---

### TC-AUTH-005 — 2FA einrichten

**Prio:** P2 | **Feature:** TOTP 2FA Setup

**Vorbedingung:** Eingeloggt als `anna.mueller@logopaedie-test.de`.

**Schritte:**
1. Navigiere zu `http://localhost:3000/settings/security`
2. Klicke "Zwei-Faktor-Authentifizierung einrichten"
3. Scanne den QR-Code mit einer Authenticator-App (z.B. Google Authenticator)
4. Gib den aktuellen 6-stelligen Code ein
5. Klicke "Aktivieren"

**Erwartet:**
- Erfolgsmeldung: "2FA aktiviert"
- Backup-Codes werden angezeigt (speichern!)
- `/auth/2fa/enable` → 200

---

### TC-AUTH-006 — Login mit 2FA

**Prio:** P2 | **Feature:** Login + 2FA

**Vorbedingung:** TC-AUTH-005 abgeschlossen.

**Schritte:**
1. Öffne `/login`, logge dich ein
2. Nach Passworteingabe erscheint 2FA-Formular
3. Gib aktuellen TOTP-Code aus Authenticator-App ein

**Erwartet:**
- Weiterleitung auf Dashboard nach korrektem Code
- Bei falschem Code: Fehlermeldung ohne Login

---

### TC-AUTH-007 — Passwort vergessen / Reset

**Prio:** P2 | **Feature:** Password Reset

**Schritte:**
1. Öffne `/forgot-password`
2. Gib `anna.mueller@logopaedie-test.de` ein
3. Klicke "Link senden"
4. Öffne Reset-Link aus der E-Mail
5. Gib neues Passwort ein (z.B. `NeuesTest1234!`)
6. Bestätige das neue Passwort

**Erwartet:**
- Erfolgsmeldung nach Reset
- Login mit neuem Passwort funktioniert
- Login mit altem Passwort schlägt fehl

---

### TC-AUTH-008 — Session-Liste anzeigen und Session löschen

**Prio:** P3 | **Feature:** Sessions

**Vorbedingung:** Eingeloggt; optimalerweise auf zwei Geräten/Browsern aktiv.

**Schritte:**
1. Navigiere zu `/settings/security`
2. Scroll zu "Aktive Sitzungen"
3. Klicke auf "Sitzung beenden" bei einer alten Session

**Erwartet:**
- Session aus der Liste verschwunden
- Im anderen Browser: nächster API-Aufruf → 401

---

### TC-AUTH-009 — Logout

**Prio:** P1 | **Feature:** Logout

**Schritte:**
1. Klicke auf Logout-Button in der Navigation
2. Beobachte Weiterleitung

**Erwartet:**
- Weiterleitung auf `/login`
- Cookies gelöscht (DevTools prüfen)
- Direktzugriff auf `/berichte` leitet zurück zu `/login`

---

### TC-AUTH-010 — Rate Limit bei Login

**Prio:** P3 | **Feature:** Rate Limiting

**Schritte:**
1. Versuche 6× hintereinander Login mit falschem Passwort

**Erwartet:**
- Nach 5 Fehlversuchen: HTTP 429 oder UI-Meldung "Zu viele Versuche"
- Wartezeit im Response-Header oder UI

---

## Abschnitt PAT — Patientenverwaltung

### TC-PAT-001 — Neuen Patienten anlegen

**Prio:** P1 | **Feature:** Patients

**Vorbedingung:** Eingeloggt als `anna.mueller@logopaedie-test.de`.

**Schritte:**
1. Navigiere zu `http://localhost:3000/patienten`
2. Klicke "Neuer Patient" oder `+`-Button
3. Fülle aus:
   - Vorname: `Emma`, Nachname: `Richter`
   - Geburtsdatum: `15.03.2018`
   - Pseudonym: `ER-2018`
4. Speichere

**Erwartet:**
- Patient erscheint in der Patientenliste
- Detailseite aufrufbar
- Backend: `POST /patients` → 201

---

### TC-PAT-002 — Weitere Patienten anlegen

**Prio:** P1 | **Feature:** Patients

**Wie TC-PAT-001**, aber:
- Patient 2: Thomas Bergmann, 08.11.1975, Pseudonym `TB-1975`
- Patient 3: Lena Fischer, 22.07.2019, Pseudonym `LF-2019`

---

### TC-PAT-003 — Patientenliste anzeigen und suchen

**Prio:** P2 | **Feature:** Patients — List/Search

**Schritte:**
1. Öffne `/patienten`
2. Überprüfe: Alle 3 Patienten sichtbar
3. Suche nach "Emma"

**Erwartet:**
- Nur Emma Richter erscheint in den Suchergebnissen

---

### TC-PAT-004 — Patienten bearbeiten

**Prio:** P2 | **Feature:** Patients — Edit

**Schritte:**
1. Öffne Detailseite von Emma Richter
2. Klicke "Bearbeiten"
3. Ändere Pseudonym zu `ER-2018-b`
4. Speichere

**Erwartet:**
- Aktualisiertes Pseudonym in der Detailseite

---

### TC-PAT-005 — Patienten löschen

**Prio:** P3 | **Feature:** Patients — Delete

**Schritte:**
1. Öffne Detailseite von einem Testpatienten (z.B. Lena Fischer)
2. Klicke "Löschen"
3. Bestätige den Dialog

**Erwartet:**
- Patient nicht mehr in der Liste
- `DELETE /patients/{id}` → 200 oder 204

---

### TC-PAT-006 — Patienten-History anzeigen

**Prio:** P2 | **Feature:** Patients — History

**Vorbedingung:** Für Emma Richter existiert mindestens 1 Sitzung (nach TC-SES-xxx).

**Schritte:**
1. Öffne Detailseite Emma Richter
2. Klicke auf "Verlauf" oder "History"-Tab

**Erwartet:**
- Liste der bisherigen Sitzungen und Reports sichtbar

---

## Abschnitt SES — Sitzungen & Anamnese

### TC-SES-001 — Neue Sitzung starten (mit Patient)

**Prio:** P1 | **Feature:** Session — Start

**Vorbedingung:** Emma Richter existiert (TC-PAT-001).

**Schritte:**
1. Navigiere zu `/module/report`
2. Falls Patientenauswahl erscheint: wähle Emma Richter
3. Klicke "Neue Sitzung starten"

**Erwartet:**
- Sitzung erstellt, Anamnese-Chat öffnet sich
- Session-ID sichtbar (12-stelliger Hex-String, z.B. `a1b2c3d4e5f6`)
- Backend: `POST /sessions` → 201

---

### TC-SES-002 — Anamnese via Chat durchführen

**Prio:** P1 | **Feature:** Session — Chat (Anamnesis)

**Vorbedingung:** TC-SES-001 abgeschlossen.

**Schritte:**
1. Tippe in das Chat-Feld die Anamnese-Antworten aus `TEST_DATA.md` (Patient Emma Richter) ein
2. Beantworte jede KI-Frage mit den vorbereiteten Antworten
3. Beobachte, ob der Fortschritt/Status sich ändert

**Erwartet:**
- KI stellt strukturierte Fragen (Hauptproblem, Anamnese, Ziele)
- Jede Antwort wird angenommen
- Nach mehreren Austauschen: Status wechselt zu "bereit für Bericht" o.ä.

---

### TC-SES-003 — Audio-Aufnahme hochladen

**Prio:** P1 | **Feature:** Session — Audio Upload

**Vorbedingung:** Laufende Sitzung, Audiodatei aus `TEST_DATA.md` (Aufnahme A) bereit.

**Schritte:**
1. Klicke auf den "Audio hochladen"-Button
2. Wähle die vorbereitete Audio-Datei (MP3/WAV, < 25 MB)
3. Warte auf Transkription

**Erwartet:**
- Fortschrittsanzeige während Upload
- Transkription erscheint im Chat oder separatem Feld
- Fachwörter korrekt erkannt (z.B. "Anlautposition", "Phonem")
- Backend: `POST /sessions/{id}/upload` → 200

---

### TC-SES-004 — Live-Audioaufnahme (Browser-Mikrofon)

**Prio:** P2 | **Feature:** Session — Live Recording

**Schritte:**
1. In laufender Sitzung: Klicke "Aufnehmen"
2. Erlaube Mikrofon-Zugriff im Browser
3. Sprich den Text aus Aufnahme A (TEST_DATA.md) ca. 30 Sekunden
4. Klicke "Stoppen"

**Erwartet:**
- Aufnahme-Indikator zeigt aktive Aufnahme
- Nach Stopp: Transkription erscheint
- Kein Browser-Crash, kein Tonausfall

---

### TC-SES-005 — Sitzung abrufen (GET /sessions/{id})

**Prio:** P2 | **Feature:** Session — Retrieval

**Schritte:**
1. Notiere die Session-ID aus TC-SES-001
2. Öffne `http://localhost:8001/sessions/{id}` im Browser (oder curl)

**Erwartet:**
- JSON mit Session-Daten: Status, Patient-ID, erstellte Nachrichten

---

## Abschnitt REP — Berichtgenerierung

### TC-REP-001 — Befundbericht generieren

**Prio:** P1 | **Feature:** Report — Generate (befundbericht)

**Vorbedingung:** Anamnese in TC-SES-002 abgeschlossen.

**Schritte:**
1. Klicke "Bericht generieren"
2. Wähle Typ: **Befundbericht**
3. Warte auf Generierung (10–30 Sekunden, Groq-abhängig)

**Erwartet:**
- Bericht erscheint im UI mit Sektionen: Anamnese, Befund, Diagnose, Therapieempfehlung, Prognose
- Patientenname (Emma Richter) korrekt eingefügt
- Kein "Lorem ipsum", keine leeren Sektionen
- Backend: `POST /sessions/{id}/generate` → 200

---

### TC-REP-002 — Therapiebericht kurz generieren

**Prio:** P1 | **Feature:** Report — therapiebericht_kurz

**Wie TC-REP-001**, Typ: **Therapiebericht (kurz)**.

**Erwartet:** Kurzer Verlaufsbericht, Schwerpunkt auf Fortschritt der aktuellen Sitzung.

---

### TC-REP-003 — Therapiebericht lang generieren

**Prio:** P2 | **Feature:** Report — therapiebericht_lang

**Wie TC-REP-001**, Typ: **Therapiebericht (lang)**.

**Erwartet:** Detaillierter Bericht mit mehr Kontext, Methoden, ausführlicher Empfehlung.

---

### TC-REP-004 — Abschlussbericht generieren

**Prio:** P2 | **Feature:** Report — abschlussbericht

**Wie TC-REP-001**, Typ: **Abschlussbericht**.

**Erwartet:** Zusammenfassung des gesamten Therapieverlaufs, Prognose, Empfehlungen für Nachsorge.

---

### TC-REP-005 — Berichteübersicht anzeigen

**Prio:** P1 | **Feature:** Reports — List

**Vorbedingung:** Mindestens 1 Bericht generiert.

**Schritte:**
1. Navigiere zu `/berichte`

**Erwartet:**
- Liste aller generierten Berichte mit Typ, Datum, Patientenname
- Statistiken sichtbar (Gesamt, nach Typ)

---

### TC-REP-006 — Bericht-Deeplink öffnen

**Prio:** P2 | **Feature:** Reports — Deeplink

**Schritte:**
1. Klicke auf einen Bericht in der Übersicht
2. Beobachte URL-Änderung zu `/berichte/{id}`

**Erwartet:**
- Bericht vollständig dargestellt
- URL direkt aufrufbar (kein Refresh-Problem)

---

### TC-REP-007 — Vergleich zweier Berichte

**Prio:** P2 | **Feature:** Compare

**Vorbedingung:** Mindestens 2 Berichte für denselben Patienten.

**Schritte:**
1. Navigiere zu `/module/compare`
2. Wähle zwei Berichte für Emma Richter aus
3. Klicke "Vergleichen"

**Erwartet:**
- Unterschiede / Entwicklung zwischen den Berichten werden hervorgehoben
- Kein Crash bei identischen Berichten

---

## Abschnitt PHO — Phonologische Analyse

### TC-PHO-001 — Phonologische Analyse aus Text

**Prio:** P2 | **Feature:** Phonological Analysis

**Vorbedingung:** Eingeloggt, laufende Sitzung optional.

**Schritte:**
1. Navigiere zu `/module/phonology`
2. Gib folgenden Text ein:
   ```
   Emma spricht: Regen → Wegen, Schule → Sule, Frosch → Fwosch, Straße → Stwasse
   ```
3. Klicke "Analysieren"

**Erwartet:**
- Auflistung der betroffenen Phoneme: /r/, /sch/
- Erkannte Substitutionsmuster
- ICD-ähnliche Klassifikation (Dyslalie)
- Backend: `POST /analysis/phonological-text` → 200

---

### TC-PHO-002 — Phonologische Analyse aus Audio

**Prio:** P3 | **Feature:** Phonological Analysis — Audio

**Schritte:**
1. Lade Aufnahme A in das Phonologie-Modul
2. Klicke "Analysieren"

**Erwartet:**
- Transkription + phonologische Analyse in einem Schritt
- `/analysis/phonological` → 200

---

## Abschnitt SOAP — SOAP-Notizen

### TC-SOAP-001 — SOAP-Note generieren

**Prio:** P1 | **Feature:** SOAP Notes

**Vorbedingung:** Sitzung mit Thomas Bergmann abgeschlossen (TC-SES-002 für Thomas).

**Schritte:**
1. Navigiere zu `/module/soap`
2. Falls keine aktive Sitzung: Wähle die Sitzung von Thomas Bergmann
3. Klicke "SOAP-Note generieren"

**Erwartet:**
- SOAP-Note mit 4 Sektionen: Subjektiv, Objektiv, Assessment, Plan
- Inhalt basiert auf der Sitzung
- Kein "undefined" oder leere Felder
- Backend: `POST /sessions/{id}/soap` → 200

---

### TC-SOAP-002 — SOAP-Note abrufen

**Prio:** P2 | **Feature:** SOAP Notes — Get

**Schritte:**
1. Nach TC-SOAP-001: Navigiere zu `/berichte/{id}`
2. Prüfe ob SOAP-Sektion vorhanden

**Erwartet:**
- SOAP-Daten über `GET /reports/{id}/soap` abrufbar

---

## Abschnitt PLAN — Therapieplanung

### TC-PLAN-001 — Therapieplan generieren

**Prio:** P2 | **Feature:** Therapy Plan

**Vorbedingung:** Sitzung mit mindestens einer Anamnese.

**Schritte:**
1. Navigiere zu `/module/therapy-plan` oder innerhalb einer Sitzung
2. Klicke "Therapieplan erstellen"

**Erwartet:**
- Strukturierter Therapieplan: Ziele, Methoden, Frequenz, Dauer
- Bezug auf Patientendiagnose erkennbar
- Backend: `POST /sessions/{id}/therapy-plan` → 200

---

## Abschnitt SUGG — Vorschläge

### TC-SUGG-001 — Therapievorschläge generieren

**Prio:** P2 | **Feature:** Suggestions

**Schritte:**
1. Navigiere zu `/module/suggest`
2. Gib ein: `Artikulationsstörung /r/, Schulkind 7 Jahre`
3. Klicke "Vorschläge"

**Erwartet:**
- Liste mit konkreten Übungen / Methoden
- Backend: `POST /suggest` → 200

---

## Abschnitt HIST — Verlauf

### TC-HIST-001 — Sitzungsverlauf anzeigen

**Prio:** P2 | **Feature:** History

**Vorbedingung:** Mindestens 2 Sitzungen für Emma Richter.

**Schritte:**
1. Navigiere zu `/module/history` oder Patientendetailseite → History-Tab
2. Wähle Emma Richter

**Erwartet:**
- Chronologische Liste aller Sitzungen
- Reports pro Sitzung sichtbar

---

## Abschnitt PDF — Export

### TC-PDF-001 — PDF-Export eines Berichts

**Prio:** P1 | **Feature:** PDF Export

**Vorbedingung:** Mindestens 1 Bericht generiert.

**Schritte:**
1. Öffne den Bericht in `/berichte/{id}`
2. Klicke "Als PDF exportieren"

**Erwartet:**
- PDF-Download startet (Browser-Download-Dialog oder direktes PDF)
- PDF enthält: Patientenname, Datum, Berichtstext
- Kein leeres PDF, kein Fehler
- Backend: `GET /reports/{id}/pdf` → 200 mit `application/pdf`

---

## Abschnitt ADM — Admin

### TC-ADM-001 — Audit-Log anzeigen

**Prio:** P2 | **Feature:** Admin — Audit Log

**Vorbedingung:** Eingeloggt als `admin@logopaedie-test.de` (Rolle: admin).

**Schritte:**
1. Navigiere zu `http://localhost:3000/admin/audit`

**Erwartet:**
- Tabelle mit sicherheitsrelevanten Events sichtbar
- Events: Login, Registrierung, Passwortänderung, 2FA, etc.
- Nicht-Admin-Benutzer → Redirect oder 403

---

### TC-ADM-002 — Benutzer sperren

**Prio:** P3 | **Feature:** Admin — User Lock

**Schritte:**
1. Aus der Admin-Ansicht: Benutzer `anna.mueller@logopaedie-test.de` sperren
2. Versuche als Anna einzuloggen

**Erwartet:**
- Login schlägt fehl: "Konto gesperrt" o.ä.
- Admin kann Sperre aufheben: Login wieder möglich

---

## Abschnitt UX — UI / Usability

### TC-UX-001 — Dark/Light Mode Toggle

**Prio:** P3 | **Feature:** Theme

**Schritte:**
1. Klicke auf den Theme-Toggle-Button (oben rechts oder in der Navigation)

**Erwartet:**
- UI wechselt zwischen Dark und Light Mode
- Alle Texte lesbar, kein weißer Text auf weißem Hintergrund
- Einstellung bleibt nach Seitenreload erhalten

---

### TC-UX-002 — Responsiveness Mobile

**Prio:** P3 | **Feature:** Responsive Layout

**Schritte:**
1. Öffne Chrome DevTools → Device: iPhone 12
2. Navigiere durch: `/`, `/berichte`, `/patienten`, `/module/report`

**Erwartet:**
- Navigation kollabiert zu Hamburger-Menü
- Kein horizontales Overflow
- Formulare bedienbar

---

### TC-UX-003 — Demo-Modus (unauthenticated)

**Prio:** P2 | **Feature:** Demo Mode

**Schritte:**
1. Öffne `/module/report` ohne eingeloggt zu sein

**Erwartet:**
- Demo-Modus aktiv (kein Login-Redirect für `/module/report`)
- Onboarding-Overlay erscheint
- Demo-Funktionen nutzbar (eingeschränkt)

---

### TC-UX-004 — 404-Seite

**Prio:** P3 | **Feature:** Error Pages

**Schritte:**
1. Öffne `http://localhost:3000/diese-seite-existiert-nicht`

**Erwartet:**
- Custom 404-Seite erscheint (nicht blanke Next.js-404)
- Link zurück zur Hauptseite

---

### TC-UX-005 — Onboarding Overlay (Keyboard + Escape)

**Prio:** P3 | **Feature:** OnboardingOverlay a11y

**Vorbedingung:** Demo-Modus oder erstes Login.

**Schritte:**
1. Öffne die Seite mit Onboarding-Overlay
2. Drücke `Escape`

**Erwartet:**
- Overlay schließt sich (oder deaktiviert sich korrekt)
- Fokus kehrt zum auslösenden Element zurück

---

## Regressions-Smoke-Test (5 Minuten)

Schnell-Check nach jeder Code-Änderung:

| # | Aktion | Erwartet |
|---|---|---|
| R1 | `./dev.sh` starten | Kein Error im Terminal |
| R2 | `GET http://localhost:8001/livez` | `{"status":"alive"}` |
| R3 | `http://localhost:3000/` öffnen | Landing Page lädt |
| R4 | Login mit `anna.mueller` | Dashboard sichtbar |
| R5 | `/patienten` öffnen | Liste lädt |
| R6 | Sitzung öffnen oder starten | Chat-Interface erscheint |
| R7 | Logout | Redirect auf `/login` |
