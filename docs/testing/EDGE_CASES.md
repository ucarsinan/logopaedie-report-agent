# EDGE_CASES.md — Grenzwert- und Negativtests

> Ergänzt den Haupt-Testplan in `TEST_PLAN.md`.
> Fokus: Eingabevalidierung, Datei-Limits, Auth-Grenzen, Sitzungs-Edge-Cases,
> Netzwerkfehler und Race Conditions.
>
> **Technische Basis:**
> - Passwort-Mindestlänge: **12 Zeichen** (`Field(min_length=12)` in `backend/routers/auth.py`)
> - Audio-Upload-Limit: **25 MB** (`_MAX_UPLOAD_BYTES`)
> - Material-Upload-Limit: **10 MB** (`_MAX_MATERIAL_BYTES`)
> - Max. Materialien pro Session: **5** (`_MAX_MATERIALS`)
> - Session-ID-Format: **12-stellige Hex-Zeichenkette** (`^[0-9a-f]{12}$`)
> - `derive_age_group()` akzeptiert nur Alter im Fenster `[0, 120]` Jahre;
>   außerhalb → gibt `None` zurück (kein gültiger Alters-Bucket)
> - TOTP-Replay-Schutz: `last_totp_step`-Vergleich in `auth_service.py`
> - E-Mail-Validierung via lokalem `Annotated[str, AfterValidator(...)]` in `backend/routers/auth.py`

---

## Kategorie 1: Eingabevalidierung

### TC-EC-001 — Registrierung mit zu kurzem Passwort

**Kategorie:** Eingabevalidierung
**Prio:** P2
**Sicherheitsrelevanz:** Ja

**Vorbedingung:** Anwendung läuft lokal (`localhost:3000`). Kein eingeloggter User.

**Schritte:**
1. Navigiere zu `/register`.
2. Fülle Name und E-Mail-Adresse aus.
3. Gib als Passwort `kurz123` ein (7 Zeichen — unter dem 12-Zeichen-Minimum).
4. Klicke auf "Registrieren".

**Erwartet:**
- HTTP-Status: `422 Unprocessable Entity` (Pydantic-Validierungsfehler)
- UI-Reaktion: Inline-Fehlermeldung, z. B. "Passwort muss mindestens 12 Zeichen haben"
- Kein Benutzer wird angelegt
- Kein Datenverlust / Kein Crash

**Tatsächlich:** _(leer lassen)_

**Status:** ⬜ Nicht getestet

---

### TC-EC-002 — Registrierung mit ungültigem E-Mail-Format

**Kategorie:** Eingabevalidierung
**Prio:** P2
**Sicherheitsrelevanz:** Ja

**Vorbedingung:** Anwendung läuft lokal. Kein eingeloggter User.

**Schritte:**
1. Navigiere zu `/register`.
2. Gib als E-Mail `keineat-zeichen` ein (kein `@`-Symbol).
3. Gib ein gültiges Passwort ein (≥ 12 Zeichen).
4. Klicke auf "Registrieren".

**Erwartet:**
- HTTP-Status: `422 Unprocessable Entity` (lokale E-Mail-Validierung schlägt fehl)
- UI-Reaktion: Fehlermeldung "Ungültige E-Mail-Adresse"
- Kein Benutzer wird angelegt

**Tatsächlich:** _(leer lassen)_

**Status:** ⬜ Nicht getestet

---

### TC-EC-003 — Patientenname mit XSS-Payload

**Kategorie:** Eingabevalidierung
**Prio:** P2
**Sicherheitsrelevanz:** Ja — potenzieller Cross-Site-Scripting-Angriff

> **Sicherheitshinweis:** Patientendaten werden in der UI dargestellt. Wenn der Name
> unsanitisiert in das DOM geschrieben wird, könnte `<script>`-Injection ausgeführt
> werden. React escaped JSX-Werte automatisch, jedoch müssen alle `dangerouslySetInnerHTML`-
> Stellen und PDF-Export-Pfade separat geprüft werden.

**Vorbedingung:** Eingeloggter User. Formular "Neuer Patient" geöffnet.

**Schritte:**
1. Navigiere zu `/patienten/neu`.
2. Gib als Patientenname `<script>alert(1)</script>` ein.
3. Fülle Pflichtfelder (Geburtsdatum) aus.
4. Speichern.
5. Navigiere zurück zur Patientenliste und öffne den neu angelegten Eintrag.

**Erwartet:**
- HTTP-Status: `200 OK` oder `422` (je nach Backend-Validierung)
- UI-Reaktion: Der String wird als Literal-Text angezeigt, **kein** Alert-Dialog öffnet sich
- Im generierten Bericht erscheint der Name ebenfalls als Plaintext, kein Script-Execution
- Kein Crash

**Tatsächlich:** _(leer lassen)_

**Status:** ⬜ Nicht getestet

---

### TC-EC-004 — Patientenname mit 500 Zeichen

**Kategorie:** Eingabevalidierung
**Prio:** P3
**Sicherheitsrelevanz:** Nein

**Vorbedingung:** Eingeloggter User. Formular "Neuer Patient" geöffnet.

**Schritte:**
1. Navigiere zu `/patienten/neu`.
2. Generiere einen String mit 500 Zeichen (z. B. `"A" * 500`) und füge ihn als Namen ein.
3. Fülle Pflichtfelder aus.
4. Speichern.

**Erwartet:**
- HTTP-Status: `422 Unprocessable Entity` wenn Backend eine `max_length`-Regel definiert
  — oder `201 Created` wenn keine explizite Längengrenze existiert (dann: Datenbankfeld-Limit prüfen)
- UI-Reaktion: Fehlermeldung bei Ablehnung, oder der Name wird korrekt gespeichert/abgeschnitten
- Kein Datenbankfehler, kein unbehandelter 500er

**Tatsächlich:** _(leer lassen)_

**Hinweis:** `realname` ist in `PatientCreate` (routers/patients.py) aktuell als `str` ohne
explizite `max_length` definiert. Datenbankebene (Neon PostgreSQL) greift nicht ein, da
`LargeBinary` (encrypted) verwendet wird. Das Limit sollte auf Schema-Ebene ergänzt werden.

**Status:** ⬜ Nicht getestet

---

### TC-EC-005 — Geburtsdatum in der Zukunft

**Kategorie:** Eingabevalidierung
**Prio:** P2
**Sicherheitsrelevanz:** Nein

**Vorbedingung:** Eingeloggter User. Formular "Neuer Patient" geöffnet.

**Schritte:**
1. Navigiere zu `/patienten/neu`.
2. Gib als Geburtsdatum ein Datum 10 Jahre in der Zukunft ein (z. B. `2036-01-01`).
3. Speichern.

**Erwartet:**
- `derive_age_group()` liefert `None` (negatives Alter fällt aus dem `[0, 120]`-Fenster)
- HTTP-Status: `422 Unprocessable Entity` — oder der Patient wird angelegt, aber `age_group`
  wird nicht gesetzt (Backend-Verhalten abhängig davon, ob `None` als Fehler behandelt wird)
- UI-Reaktion: Klare Fehlermeldung "Geburtsdatum darf nicht in der Zukunft liegen"
- Kein Crash, kein falsches `age_group`-Bucket im generierten Bericht

**Tatsächlich:** _(leer lassen)_

**Status:** ⬜ Nicht getestet

---

### TC-EC-006 — Geburtsdatum vor 120 Jahren

**Kategorie:** Eingabevalidierung
**Prio:** P3
**Sicherheitsrelevanz:** Nein

**Vorbedingung:** Eingeloggter User. Formular "Neuer Patient" geöffnet.

**Schritte:**
1. Navigiere zu `/patienten/neu`.
2. Gib als Geburtsdatum `1900-01-01` ein (> 120 Jahre vor heute).
3. Speichern.

**Erwartet:**
- `derive_age_group()` liefert `None` (Alter > 120 — außerhalb des plausiblen Fensters)
- HTTP-Status: `422` oder Patient wird angelegt ohne gültiges `age_group`
- UI-Reaktion: Hinweis, dass das Geburtsdatum unplausibel ist
- Kein falsches Alters-Bucket im generierten Bericht

**Tatsächlich:** _(leer lassen)_

**Status:** ⬜ Nicht getestet

---

## Kategorie 2: File-Upload-Grenzen

### TC-EC-010 — Audio-Upload > 25 MB

**Kategorie:** File-Upload-Grenzen
**Prio:** P2
**Sicherheitsrelevanz:** Nein — Denial-of-Service-Prävention

**Vorbedingung:** Eingeloggter User. Aktive Sitzung geöffnet (`/module/report`).

**Schritte:**
1. Erstelle eine Dummy-Audio-Datei mit 26 MB (z. B. `dd if=/dev/urandom of=test.mp3 bs=1M count=26`).
2. Lade die Datei über die Audio-Upload-Schaltfläche hoch.

**Erwartet:**
- HTTP-Status: `413 Request Entity Too Large` (Backend wirft `FileTooLargeError`)
- UI-Reaktion: Fehlermeldung "Datei zu groß. Maximum: 25 MB." — kein leerer Fehler, kein Crash
- Die Sitzung bleibt nutzbar (kein Zustandsverlust)
- Backend-Log: Strukturierter Error-Eintrag, kein unbehandelter Traceback

**Tatsächlich:** _(leer lassen)_

**Status:** ⬜ Nicht getestet

---

### TC-EC-011 — Audio-Upload mit falscher Extension (.txt als .mp3 umbenannt)

**Kategorie:** File-Upload-Grenzen
**Prio:** P2
**Sicherheitsrelevanz:** Ja — MIME-Type-Spoofing / Content-Injection-Risiko

> **Sicherheitshinweis:** Wenn das Backend ausschließlich den Dateinamen zur Typ-Erkennung
> verwendet, kann ein Angreifer beliebige Inhalte als Audio einschleusen. Groq Whisper
> lehnt keine Audiodaten ab, aber ein manipulierter Content-Type könnte den Verarbeitungspfad
> abweichen lassen.

**Vorbedingung:** Eingeloggter User. Aktive Sitzung geöffnet.

**Schritte:**
1. Erstelle eine Textdatei mit Inhalt `Hallo Welt` und speichere sie als `test.mp3`.
2. Lade diese Datei über die Audio-Upload-Schaltfläche hoch.

**Erwartet:**
- HTTP-Status: `400 Bad Request` oder `422` — Backend soll den MIME-Type prüfen,
  nicht nur die Extension
- UI-Reaktion: Fehlermeldung "Ungültiges Dateiformat"
- Groq API wird **nicht** mit einem Text-File aufgerufen (unnötige API-Kosten vermeiden)
- Kein Crash

**Tatsächlich:** _(leer lassen)_

**Status:** ⬜ Nicht getestet

---

### TC-EC-012 — Material-Upload > 10 MB

**Kategorie:** File-Upload-Grenzen
**Prio:** P2
**Sicherheitsrelevanz:** Nein

**Vorbedingung:** Eingeloggter User. Aktive Sitzung geöffnet.

**Schritte:**
1. Erstelle eine Dummy-PDF mit 11 MB.
2. Lade sie über "Material hochladen" hoch.

**Erwartet:**
- HTTP-Status: `413 Request Entity Too Large`
- UI-Reaktion: Fehlermeldung mit Größenlimit-Hinweis "Maximum: 10 MB"
- Materialanzahl der Session bleibt unverändert
- Kein Crash

**Tatsächlich:** _(leer lassen)_

**Status:** ⬜ Nicht getestet

---

### TC-EC-013 — 6. Material hochladen (über dem 5er-Limit)

**Kategorie:** File-Upload-Grenzen
**Prio:** P2
**Sicherheitsrelevanz:** Nein

**Vorbedingung:** Eingeloggter User. Aktive Sitzung mit bereits **5 hochgeladenen Materialien**.

**Schritte:**
1. Lade 5 gültige Materialien hoch (je < 10 MB).
2. Versuche, ein 6. Material hochzuladen.

**Erwartet:**
- HTTP-Status: `400 Bad Request` mit Detail "Maximum 5 Dateien pro Session."
- UI-Reaktion: Upload-Schaltfläche deaktiviert oder Fehlermeldung "Maximale Anzahl erreicht"
- Kein 6. Material wird gespeichert
- Session-Zustand bleibt konsistent

**Tatsächlich:** _(leer lassen)_

**Status:** ⬜ Nicht getestet

---

### TC-EC-014 — Leere Audio-Datei (0 Bytes)

**Kategorie:** File-Upload-Grenzen
**Prio:** P3
**Sicherheitsrelevanz:** Nein

**Vorbedingung:** Eingeloggter User. Aktive Sitzung geöffnet.

**Schritte:**
1. Erstelle eine leere Datei: `touch empty.mp3`.
2. Lade sie über die Audio-Upload-Schaltfläche hoch.

**Erwartet:**
- HTTP-Status: `400 Bad Request` — leere Datei ist kein gültiges Audio
- UI-Reaktion: Fehlermeldung "Datei ist leer oder ungültig"
- Groq Whisper wird **nicht** aufgerufen
- Kein Crash, kein unbehandelter 500er

**Tatsächlich:** _(leer lassen)_

**Status:** ⬜ Nicht getestet

---

## Kategorie 3: Auth-Grenzen

### TC-EC-020 — Direktzugriff auf /admin/audit als normaler User

**Kategorie:** Auth-Grenzen
**Prio:** P1
**Sicherheitsrelevanz:** Ja — Authorization-Bypass-Risiko

> **Sicherheitshinweis:** `frontend/src/proxy.ts` prüft die `admin`-Rolle am
> Next.js-Middleware-Layer. Zusätzlich muss `GET /admin/audit` am Backend eine
> Rollen-Prüfung durchführen. Beide Schichten müssen unabhängig funktionieren
> (Defense in Depth).

**Vorbedingung:** Eingeloggter User **ohne** `admin`-Rolle.

**Schritte:**
1. Logge dich als normaler User ein.
2. Navigiere direkt zu `localhost:3000/admin/audit`.

**Erwartet:**
- Frontend-Middleware (`proxy.ts`): Redirect auf `/` oder `/login` (fehlende Admin-Rolle)
- Direkter API-Aufruf `GET /backend-api/admin/audit` (z. B. via curl mit gültigem Token):
  HTTP-Status `403 Forbidden`
- Kein Audit-Log-Inhalt wird ausgegeben

**Tatsächlich:** _(leer lassen)_

**Status:** ⬜ Nicht getestet

---

### TC-EC-021 — Zugriff auf /berichte ohne Login

**Kategorie:** Auth-Grenzen
**Prio:** P1
**Sicherheitsrelevanz:** Ja — unauthentifizierter Datenzugriff

**Vorbedingung:** Kein `access_token`-Cookie gesetzt (nicht eingeloggt oder Cookie manuell gelöscht).

**Schritte:**
1. Öffne ein Inkognito-Fenster.
2. Navigiere direkt zu `localhost:3000/berichte/irgendeine-id`.

**Erwartet:**
- Frontend-Middleware (`proxy.ts`): Redirect auf `/login`
- Der Bericht-Inhalt wird **nicht** angezeigt
- HTTP-Status der Middleware-Prüfung: `302 Redirect`

**Tatsächlich:** _(leer lassen)_

**Status:** ⬜ Nicht getestet

---

### TC-EC-022 — Abgelaufener Access-Token

**Kategorie:** Auth-Grenzen
**Prio:** P2
**Sicherheitsrelevanz:** Ja — Session-Continuity und Token-Sicherheit

**Vorbedingung:** Eingeloggter User. Access-Token-Ablaufzeit bekannt (aus JWT-Konfiguration).

**Schritte:**
1. Logge dich ein (Access-Token wird gesetzt).
2. Warte bis der Access-Token abgelaufen ist — oder setze das `access_token`-Cookie
   manuell auf einen abgelaufenen JWT.
3. Führe eine authentifizierte Aktion aus (z. B. Patientenliste laden).

**Erwartet:**
- BFF-Proxy erkennt den 401-Fehler vom Backend und ruft `POST /auth/refresh` auf
- Bei erfolgreichem Refresh: neue Tokens werden gesetzt, Anfrage wird wiederholt
- Bei abgelaufenem Refresh-Token: Redirect auf `/login`
- Kein unbehandelter Fehler-Screen

**Tatsächlich:** _(leer lassen)_

**Status:** ⬜ Nicht getestet

---

### TC-EC-023 — Login mit gesperrtem Konto

**Kategorie:** Auth-Grenzen
**Prio:** P2
**Sicherheitsrelevanz:** Ja — Account-Lockout-Mechanismus

**Vorbedingung:** User-Konto ist gesperrt (z. B. via Admin: `POST /admin/users/{id}/lock`,
oder durch mehrere fehlgeschlagene Login-Versuche die `locked_until` setzen).

**Schritte:**
1. Versuche, dich mit den Credentials des gesperrten Kontos einzuloggen.

**Erwartet:**
- HTTP-Status: `423 Locked` (Backend: `AccountLockedError`)
- UI-Reaktion: Fehlermeldung "Konto gesperrt" mit optionaler Information wann die Sperre endet
- Audit-Log: `login.locked`-Event wird geschrieben
- Kein Access-Token wird ausgestellt

**Tatsächlich:** _(leer lassen)_

**Status:** ⬜ Nicht getestet

---

### TC-EC-024 — 2FA-Code erneut verwenden (Replay-Angriff)

**Kategorie:** Auth-Grenzen
**Prio:** P1
**Sicherheitsrelevanz:** Ja — TOTP-Replay-Angriff

> **Sicherheitshinweis:** `auth_service.py` implementiert Replay-Schutz via
> `last_totp_step`-Vergleich (`matched_step <= user.last_totp_step`).
> Dieser Test verifiziert, dass das Sicherheitsmerkmal in der Praxis greift.

**Vorbedingung:** User mit aktivierter 2FA. Login-Flow bis zum 2FA-Schritt durchgeführt.

**Schritte:**
1. Logge dich ein — beim 2FA-Schritt erscheint das Challenge-Formular.
2. Gib einen gültigen TOTP-Code ein → erfolgreich eingeloggt.
3. Logge dich sofort wieder aus.
4. Starte einen neuen Login-Versuch mit denselben Credentials.
5. Beim 2FA-Schritt: gib denselben TOTP-Code aus Schritt 2 erneut ein
   (innerhalb des 30-Sekunden-Fensters).

**Erwartet:**
- HTTP-Status: `401 Unauthorized` (Replay erkannt: `is_replay = True`)
- UI-Reaktion: Fehlermeldung "Ungültiger oder bereits verwendeter Code"
- Kein Access-Token wird ausgestellt
- Audit-Log: Replay-Versuch wird geloggt

**Tatsächlich:** _(leer lassen)_

**Status:** ⬜ Nicht getestet

---

### TC-EC-025 — Falscher TOTP-Code aus anderer App

**Kategorie:** Auth-Grenzen
**Prio:** P2
**Sicherheitsrelevanz:** Ja

**Vorbedingung:** User mit aktivierter 2FA. Login-Flow bis zum 2FA-Schritt durchgeführt.

**Schritte:**
1. Logge dich ein bis zum 2FA-Schritt.
2. Gib einen falschen 6-stelligen Code ein (z. B. `000000` oder Code aus einer
   anderen 2FA-App, die nicht zu diesem Konto gehört).
3. Klicke auf "Bestätigen".

**Erwartet:**
- HTTP-Status: `401 Unauthorized`
- UI-Reaktion: Fehlermeldung "Ungültiger Code. Bitte erneut versuchen."
- Bei wiederholten Fehlversuchen: `locked_until` wird gesetzt (atomares Increment + Lockout)
- Kein Access-Token wird ausgestellt

**Tatsächlich:** _(leer lassen)_

**Status:** ⬜ Nicht getestet

---

## Kategorie 4: Sitzungs-Edge-Cases

### TC-EC-030 — Ungültige Session-ID in URL

**Kategorie:** Sitzungs-Edge-Cases
**Prio:** P2
**Sicherheitsrelevanz:** Ja — Session-Enumeration verhindern

> **Sicherheitshinweis:** Session-IDs sind 12-stellige Hex-Strings (`^[0-9a-f]{12}$`).
> Ungültige Formate müssen früh abgelehnt werden, damit kein Timing-Unterschied
> zwischen "Format ungültig" und "Session nicht gefunden" entsteht.

**Vorbedingung:** Eingeloggter User.

**Schritte:**
1. Navigiere zu einer URL mit ungültiger Session-ID, z. B.:
   - `localhost:3000/module/report?session=ZZZZZZZZZZZZ` (nicht Hex)
   - `localhost:3000/module/report?session=abc123` (zu kurz, 6 Zeichen)
   - `localhost:3000/module/report?session=` (leer)

**Erwartet:**
- HTTP-Status: `400 Bad Request` (Backend: `_validate_session_id()` schlägt fehl)
- UI-Reaktion: Fehlermeldung "Ungültige Sitzungs-ID", kein Ladeindikator der hängt
- Keine Information über existierende Sessions wird geleakt

**Tatsächlich:** _(leer lassen)_

**Status:** ⬜ Nicht getestet

---

### TC-EC-031 — Bericht für fremde Session generieren

**Kategorie:** Sitzungs-Edge-Cases
**Prio:** P1
**Sicherheitsrelevanz:** Ja — Insecure Direct Object Reference (IDOR)

> **Sicherheitshinweis:** `store.get_authorized()` prüft, dass `session.user_id == current_user_id`.
> Dieser Test verifiziert, dass ein User nicht auf Sessions eines anderen Users zugreifen kann.

**Vorbedingung:** Zwei eingeloggte User (User A und User B). User A hat eine aktive Session
mit bekannter Session-ID.

**Schritte:**
1. Als User B: kopiere die Session-ID von User A.
2. Sende `POST /backend-api/sessions/{session_id_von_A}/generate` mit dem Token von User B.

**Erwartet:**
- HTTP-Status: `403 Forbidden` (Backend: `get_authorized()` erkennt Eigentümer-Konflikt)
- UI-Reaktion: Fehlermeldung "Keine Berechtigung"
- Der Bericht von User A wird **nicht** generiert
- Kein Datenleck

**Tatsächlich:** _(leer lassen)_

**Status:** ⬜ Nicht getestet

---

### TC-EC-032 — Doppelklick auf "Bericht generieren" (Race Condition)

**Kategorie:** Sitzungs-Edge-Cases
**Prio:** P3
**Sicherheitsrelevanz:** Nein

**Vorbedingung:** Eingeloggter User. Ausgefüllte Sitzung, bereit zur Berichtsgenerierung.

**Schritte:**
1. Klicke schnell zweimal (Doppelklick) auf "Bericht generieren".
2. Beobachte, ob zwei parallele Anfragen an `POST /sessions/{id}/generate` gesendet werden.

**Erwartet:**
- Nur ein Bericht wird generiert (zweite Anfrage: `409 Conflict` oder wird durch
  UI-Debounce/Disabled-State verhindert)
- Kein doppelter Groq-API-Aufruf (Kostenrelevanz)
- Kein inkonsistenter Sitzungszustand

**Tatsächlich:** _(leer lassen)_

**Status:** ⬜ Nicht getestet

---

### TC-EC-033 — Chat-Nachricht mit 2000+ Zeichen

**Kategorie:** Sitzungs-Edge-Cases
**Prio:** P3
**Sicherheitsrelevanz:** Nein

**Vorbedingung:** Eingeloggter User. Aktive Sitzung mit Chat-Interface geöffnet.

**Schritte:**
1. Füge eine Nachricht mit 2001 Zeichen in das Chat-Eingabefeld ein.
2. Sende die Nachricht.

**Erwartet:**
- HTTP-Status: `422 Unprocessable Entity` wenn `max_length` auf dem `content`-Feld
  definiert ist (aktuell: `models/schemas.py` → `content: str = Field(min_length=1)`,
  kein `max_length` — daher wahrscheinlich `200 OK`)
- UI-Reaktion: Entweder Eingabe wird abgeschnitten oder Fehlermeldung
- Kein Backend-Crash, kein Redis-Overflow

**Tatsächlich:** _(leer lassen)_

**Hinweis:** `content`-Feld hat aktuell kein `max_length`. Sehr lange Nachrichten erhöhen
den Token-Verbrauch bei Groq. Eine `max_length=5000`-Begrenzung analog zum
`text`-Feld in `schemas.py` wäre sinnvoll.

**Status:** ⬜ Nicht getestet

---

### TC-EC-034 — Bericht generieren ohne Chat-Inhalt

**Kategorie:** Sitzungs-Edge-Cases
**Prio:** P2
**Sicherheitsrelevanz:** Nein

**Vorbedingung:** Eingeloggter User. Neue, leere Sitzung (keine Chat-Nachrichten, kein Audio).

**Schritte:**
1. Erstelle eine neue Sitzung.
2. Ohne irgendeinen Chat-Inhalt oder Audio: klicke auf "Bericht generieren".

**Erwartet:**
- HTTP-Status: `400 Bad Request` oder `422` — Sitzung hat keinen verwertbaren Inhalt
- UI-Reaktion: Fehlermeldung "Keine Inhalte für die Berichtsgenerierung vorhanden"
- Groq API wird **nicht** aufgerufen (unnötige Kosten und leerer Bericht vermeiden)
- Kein Crash

**Tatsächlich:** _(leer lassen)_

**Status:** ⬜ Nicht getestet

---

## Kategorie 5: Netzwerk / Browser

### TC-EC-040 — Backend-Verbindung während Reportgenerierung unterbrechen

**Kategorie:** Netzwerk / Browser
**Prio:** P3
**Sicherheitsrelevanz:** Nein

**Vorbedingung:** Eingeloggter User. Sitzung mit ausreichend Inhalt für Berichtsgenerierung.

**Schritte:**
1. Klicke auf "Bericht generieren" (Groq-API-Aufruf startet).
2. Während der Generierung (Ladeindikator sichtbar): Browser-DevTools öffnen →
   Network-Tab → "Offline" aktivieren.
3. Warte auf Fehlermeldung.

**Erwartet:**
- UI-Reaktion: Fehlermeldung "Verbindungsfehler. Bitte erneut versuchen."
- Kein eingefrierener Ladeindikator ohne Abbruchoption
- Sitzungsstatus bleibt konsistent (kein `"generating"`-Zustand der nicht zurückgesetzt wird)
- Nach Wiederherstellung der Verbindung: erneuter Generierungsversuch möglich

**Tatsächlich:** _(leer lassen)_

**Status:** ⬜ Nicht getestet

---

### TC-EC-041 — Seite während Audio-Upload neu laden

**Kategorie:** Netzwerk / Browser
**Prio:** P3
**Sicherheitsrelevanz:** Nein

**Vorbedingung:** Eingeloggter User. Audio-Upload im Gange (große Datei, ~10 MB).

**Schritte:**
1. Starte den Upload einer ~10 MB Audio-Datei.
2. Während der Upload-Fortschrittsbalken läuft: lade die Seite mit F5 neu.

**Erwartet:**
- Der unvollständige Upload wird abgebrochen (kein Zombie-Request im Backend)
- Nach dem Neuladen: Sitzung ist noch vorhanden, kein teilweise hochgeladenes Material
  wird angezeigt
- Kein verwaister Eintrag in der Materialliste

**Tatsächlich:** _(leer lassen)_

**Status:** ⬜ Nicht getestet

---

### TC-EC-042 — Zwei Browser-Tabs mit derselben Sitzung

**Kategorie:** Netzwerk / Browser
**Prio:** P3
**Sicherheitsrelevanz:** Nein

**Vorbedingung:** Eingeloggter User. Aktive Sitzung vorhanden.

**Schritte:**
1. Öffne dieselbe Sitzungs-URL in zwei Browser-Tabs (Tab A und Tab B).
2. In Tab A: sende eine Chat-Nachricht.
3. Wechsle zu Tab B: lade die Seite neu.
4. In Tab B: sende eine weitere Chat-Nachricht.
5. Wechsle zu Tab A: lade die Seite neu.

**Erwartet:**
- Beide Nachrichten sind in beiden Tabs nach dem Neuladen sichtbar
  (Redis-Session ist die Single Source of Truth)
- Kein Datenverlust, keine doppelten Nachrichten
- Kein inkonsistenter `collected_data`-Zustand im Anamnese-Katalog

**Tatsächlich:** _(leer lassen)_

**Status:** ⬜ Nicht getestet

---

## Kategorie 6: Gleichzeitige Operationen

### TC-EC-050 — Zwei Berichte gleichzeitig generieren

**Kategorie:** Gleichzeitige Operationen
**Prio:** P3
**Sicherheitsrelevanz:** Nein

**Vorbedingung:** Eingeloggter User. Zwei verschiedene Sitzungen mit ausreichend Inhalt.

**Schritte:**
1. Öffne Sitzung A in Tab 1 und Sitzung B in Tab 2.
2. Klicke in Tab 1 auf "Bericht generieren".
3. Wechsle sofort zu Tab 2 und klicke ebenfalls auf "Bericht generieren".
4. Warte bis beide Generierungen abgeschlossen sind.

**Erwartet:**
- Beide Berichte werden korrekt und unabhängig generiert
- Kein Vermischen von Sitzungsdaten zwischen den Berichten
- Rate-Limiter (`GENERATE_LIMIT`) greift ggf. für den zweiten Request — dann:
  klare Fehlermeldung statt hängendem Loader
- Kein Backend-Crash

**Tatsächlich:** _(leer lassen)_

**Status:** ⬜ Nicht getestet

---

### TC-EC-051 — Patient während laufender Sitzung löschen

**Kategorie:** Gleichzeitige Operationen
**Prio:** P2
**Sicherheitsrelevanz:** Nein — Datenkonsistenz

**Vorbedingung:** Eingeloggter User. Patient mit verknüpfter, aktiver Sitzung vorhanden.

**Schritte:**
1. Öffne eine aktive Sitzung des Patienten in Tab 1.
2. In Tab 2: navigiere zu `/patienten/{id}` und lösche den Patienten.
3. Wechsle zu Tab 1: versuche, die Sitzung weiterzuführen
   (Chat-Nachricht senden oder Bericht generieren).

**Erwartet:**
- HTTP-Status: `404 Not Found` oder `409 Conflict` wenn die Sitzung den Patient referenziert
  und die Referenzintegrität verletzt ist
- UI-Reaktion: Fehlermeldung "Patient nicht mehr vorhanden. Sitzung kann nicht fortgesetzt werden."
- Keine Orphan-Session die weiter schreibt
- Kein unbehandelter 500er durch Datenbankfehler

**Tatsächlich:** _(leer lassen)_

**Status:** ⬜ Nicht getestet

---

## Anhang: Testfall-Übersicht

| TC-ID | Name | Kategorie | Prio | Sicherheit | Status |
|---|---|---|---|---|---|
| TC-EC-001 | Zu kurzes Passwort | Eingabevalidierung | P2 | Ja | ⬜ |
| TC-EC-002 | Ungültiges E-Mail-Format | Eingabevalidierung | P2 | Ja | ⬜ |
| TC-EC-003 | XSS im Patientennamen | Eingabevalidierung | P2 | Ja | ⬜ |
| TC-EC-004 | Patientenname 500 Zeichen | Eingabevalidierung | P3 | Nein | ⬜ |
| TC-EC-005 | Geburtsdatum in der Zukunft | Eingabevalidierung | P2 | Nein | ⬜ |
| TC-EC-006 | Geburtsdatum vor 120 Jahren | Eingabevalidierung | P3 | Nein | ⬜ |
| TC-EC-010 | Audio > 25 MB | File-Upload-Grenzen | P2 | Nein | ⬜ |
| TC-EC-011 | Falscher MIME-Type (txt als mp3) | File-Upload-Grenzen | P2 | Ja | ⬜ |
| TC-EC-012 | Material > 10 MB | File-Upload-Grenzen | P2 | Nein | ⬜ |
| TC-EC-013 | 6. Material (über Limit) | File-Upload-Grenzen | P2 | Nein | ⬜ |
| TC-EC-014 | Leere Audio-Datei (0 Bytes) | File-Upload-Grenzen | P3 | Nein | ⬜ |
| TC-EC-020 | Admin-Seite als normaler User | Auth-Grenzen | P1 | Ja | ⬜ |
| TC-EC-021 | Berichte ohne Login | Auth-Grenzen | P1 | Ja | ⬜ |
| TC-EC-022 | Abgelaufener Access-Token | Auth-Grenzen | P2 | Ja | ⬜ |
| TC-EC-023 | Login mit gesperrtem Konto | Auth-Grenzen | P2 | Ja | ⬜ |
| TC-EC-024 | TOTP-Replay-Angriff | Auth-Grenzen | P1 | Ja | ⬜ |
| TC-EC-025 | Falscher TOTP-Code | Auth-Grenzen | P2 | Ja | ⬜ |
| TC-EC-030 | Ungültige Session-ID in URL | Sitzungs-Edge-Cases | P2 | Ja | ⬜ |
| TC-EC-031 | IDOR: fremde Session generieren | Sitzungs-Edge-Cases | P1 | Ja | ⬜ |
| TC-EC-032 | Doppelklick "Bericht generieren" | Sitzungs-Edge-Cases | P3 | Nein | ⬜ |
| TC-EC-033 | Chat-Nachricht 2000+ Zeichen | Sitzungs-Edge-Cases | P3 | Nein | ⬜ |
| TC-EC-034 | Bericht ohne Inhalt generieren | Sitzungs-Edge-Cases | P2 | Nein | ⬜ |
| TC-EC-040 | Backend offline während Generierung | Netzwerk / Browser | P3 | Nein | ⬜ |
| TC-EC-041 | Seitenneuladen während Upload | Netzwerk / Browser | P3 | Nein | ⬜ |
| TC-EC-042 | Zwei Tabs, dieselbe Sitzung | Netzwerk / Browser | P3 | Nein | ⬜ |
| TC-EC-050 | Zwei Berichte parallel generieren | Gleichzeitige Operationen | P3 | Nein | ⬜ |
| TC-EC-051 | Patient während Sitzung löschen | Gleichzeitige Operationen | P2 | Nein | ⬜ |
