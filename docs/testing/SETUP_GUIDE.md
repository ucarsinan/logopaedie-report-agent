# SETUP_GUIDE.md — Lokale Testumgebung aufsetzen

> Schritt-für-Schritt-Anleitung zum Einrichten der lokalen Entwicklungsumgebung
> für manuelle Tests des Logopädie Report Agents.
>
> Stack: FastAPI (Python 3.12) + Next.js 16 — Monorepo
> Testplan: siehe `TEST_PLAN.md` | Testdaten: siehe `TEST_DATA.md`

---

## 1. Voraussetzungen

| Werkzeug | Mindestversion | Prüfen mit |
|---|---|---|
| Python | 3.12+ | `python3 --version` |
| Node.js | 22+ | `node --version` |
| npm | 10+ | `npm --version` |
| Git | beliebig | `git --version` |

**Externe Dienste:**

- **Groq API Key** (Pflicht für Audio/Report-Generierung) — kostenloser Account auf [console.groq.com](https://console.groq.com)
- **SMTP / E-Mail-Dienst** (Optional) — für E-Mail-Zustellung. Wenn nicht konfiguriert: Verifizierungslinks werden im Backend-Terminal ausgegeben (kein SMTP nötig für lokale Tests).
- **Authenticator-App** (Optional, nur für 2FA-Tests) — Google Authenticator, Authy oder ein beliebiger TOTP-Client.

---

## 2. Repository klonen und Dependencies installieren

```bash
git clone <repository-url>
cd logopaedie-report-agent
```

**Backend-Dependencies:**

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
```

**Frontend-Dependencies:**

```bash
cd ../frontend
npm install
```

---

## 3. Environment-Variablen konfigurieren

### 3.1 `.env`-Datei erstellen

```bash
cp backend/.env.example backend/.env
```

Öffne `backend/.env` in einem Editor und befülle die Felder.

### 3.2 Pflicht-Variablen (ohne diese startet die App nicht korrekt)

| Variable | Beschreibung | Beispielwert |
|---|---|---|
| `GROQ_API_KEY` | API-Key für Whisper (STT) + Llama (NLP) | `gsk_...` |
| `JWT_SECRET` | Geheimer Schlüssel für JWT-Signierung | beliebiger langer zufälliger String |
| `SESSION_ENCRYPTION_KEY` | Fernet-Schlüssel für Session-Verschlüsselung | 32-Byte URL-safe Base64-String |
| `PATIENT_ENCRYPTION_KEY` | Fernet-Schlüssel für Patienten-Datenverschlüsselung | 32-Byte URL-safe Base64-String |

**Groq API Key holen:**
1. Account anlegen auf [console.groq.com](https://console.groq.com)
2. In der Konsole: **API Keys** → **Create API Key**
3. Key kopieren und als `GROQ_API_KEY=gsk_...` in `.env` eintragen

**Fernet-Schlüssel generieren (einmalig, lokal):**

```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Diesen Befehl zweimal ausführen — jeweils einen Wert für `SESSION_ENCRYPTION_KEY` und einen für `PATIENT_ENCRYPTION_KEY` verwenden.

### 3.3 Optionale Variablen

| Variable | Beschreibung | Default |
|---|---|---|
| `DATABASE_URL` | PostgreSQL-URL (Neon) | SQLite (`sqlite:///./reports.db`) |
| `RESEND_API_KEY` | Resend.com API-Key für E-Mail-Versand | leer (Console-Fallback aktiv) |
| `EMAIL_FROM` | Absenderadresse für E-Mails | `noreply@localhost` |
| `APP_URL` | Basis-URL der Frontend-App | `http://localhost:3000` |
| `ALLOWED_ORIGINS` | CORS-Whitelist, kommagetrennt | `http://localhost:3000` |
| `KV_REST_API_URL` | Upstash Redis REST URL (Session-Store) | In-Memory-Fallback |
| `KV_REST_API_TOKEN` | Upstash Redis REST Token | — |
| `ACCESS_TOKEN_TTL_MINUTES` | Lebensdauer des Access-Tokens in Minuten | `15` |

### 3.4 SMTP-Bypass für lokale Tests

Wenn `RESEND_API_KEY` **nicht** gesetzt ist, fällt der E-Mail-Service automatisch in den
**Console-Modus**: Alle E-Mails (Verifizierung, Passwort-Reset) werden direkt im
Backend-Terminal ausgegeben — kein externer Dienst nötig.

Das Terminal zeigt dann z.B.:

```
EMAIL (console mode) -> anna.mueller@logopaedie-test.de
Subject: Verify your email
Welcome. Please verify your email by clicking:
http://localhost:3000/verify-email?token=<TOKEN>
If you did not create an account, ignore this message.
```

Den Link einfach aus dem Terminal kopieren und im Browser öffnen.

### 3.5 Minimale `.env` für lokale Tests

```dotenv
GROQ_API_KEY=gsk_<dein-key-hier>
JWT_SECRET=<langer-zufaelliger-string-min-32-zeichen>
SESSION_ENCRYPTION_KEY=<fernet-key>
PATIENT_ENCRYPTION_KEY=<fernet-key>
APP_URL=http://localhost:3000
ALLOWED_ORIGINS=http://localhost:3000
```

---

## 4. Datenbank initialisieren

### Option A — SQLite (Standard für lokale Tests, keine Konfiguration nötig)

Wenn `DATABASE_URL` nicht gesetzt ist, erstellt das Backend automatisch eine
SQLite-Datei unter `backend/reports.db`. Keine weiteren Schritte nötig.

### Option B — Neon PostgreSQL (optional, produktionsnäher)

1. Neon-Datenbank unter [neon.tech](https://neon.tech) anlegen
2. Connection-String in `.env` eintragen:
   ```dotenv
   DATABASE_URL=postgresql://user:password@host/dbname?sslmode=require
   ```
   Neon verwendet `postgres://`-Präfix — das Backend wandelt das automatisch in
   `postgresql://` um.

### Alembic-Migrationen ausführen

Nach dem ersten Aufsetzen und nach Code-Änderungen an Datenbankmodellen:

```bash
cd backend
source .venv/bin/activate
python -m alembic upgrade head
```

Bei SQLite-Nutzung: Tabellen werden beim ersten Start der App auch automatisch
via `SQLModel.metadata.create_all()` angelegt — der Alembic-Schritt ist für lokale
Tests meist nicht zwingend nötig, aber empfohlen.

---

## 5. App starten

Das Projekt enthält ein `dev.sh`-Skript, das Backend und Frontend parallel startet:

```bash
./dev.sh
```

**Was das Skript tut:**
1. Prüft ob `backend/.env` existiert — bricht sonst mit Fehlermeldung ab
2. Erstellt automatisch `backend/.venv`, falls noch nicht vorhanden
3. Installiert Backend-Dependencies via pip (quiet)
4. Installiert Frontend-Dependencies via npm, falls `node_modules` fehlt
5. Startet `uvicorn` auf Port `:8001` (Backend)
6. Startet `next dev` auf Port `:3000` (Frontend)

**Erwartete Ausgabe nach erfolgreichem Start:**

```
[Backend] Starting uvicorn on :8001
[Frontend] Starting Next.js on :3000
Backend:  http://localhost:8001
Frontend: http://localhost:3000
Press Ctrl+C to stop both services
```

**Health-Check (neues Terminal-Tab):**

```bash
curl http://localhost:8001/livez
# Erwartete Antwort: {"status":"alive"}
```

**Frontend öffnen:** `http://localhost:3000`

**Backend-Dokumentation (Swagger):** `http://localhost:8001/docs`

---

## 6. Testkonten anlegen

### Benutzer A — Therapeutin (`anna.mueller@logopaedie-test.de`)

1. Öffne `http://localhost:3000/register`
2. Fülle das Formular aus:
   - **Name:** `Anna Müller`
   - **E-Mail:** `anna.mueller@logopaedie-test.de`
   - **Passwort:** `Test1234!Demo`
3. Klicke "Registrieren"
4. Im Backend-Terminal erscheint der Verifizierungslink (Console-Modus):
   ```
   EMAIL (console mode) -> anna.mueller@logopaedie-test.de
   Subject: Verify your email
   Welcome. Please verify your email by clicking:
   http://localhost:3000/verify-email?token=<TOKEN>
   ```
5. Kopiere den vollständigen Link und öffne ihn im Browser
6. Nach erfolgreicher Verifizierung: Login unter `http://localhost:3000/login` möglich

**Verifizierungslink aus dem Log extrahieren (Alternativmethode via grep):**

Falls das Backend in eine Datei loggt (z.B. `/private/tmp/logo-backend.log`):

```bash
grep "verify-email" /private/tmp/logo-backend.log | tail -1
```

### Benutzer B — Admin (`admin@logopaedie-test.de`)

1. Registriere wie Benutzer A, mit:
   - **Name:** `Admin User`
   - **E-Mail:** `admin@logopaedie-test.de`
   - **Passwort:** `AdminTest1234!`
2. Verifizierungslink aus dem Terminal öffnen (wie oben)
3. Admin-Rolle setzen — SQL direkt ausführen:

**Bei SQLite:**

```bash
cd backend
source .venv/bin/activate
python3 -c "
import sqlite3
conn = sqlite3.connect('reports.db')
conn.execute(\"UPDATE users SET role = 'admin' WHERE email = 'admin@logopaedie-test.de'\")
conn.commit()
conn.close()
print('Rolle gesetzt.')
"
```

**Bei PostgreSQL (Neon):**

```sql
UPDATE users SET role = 'admin' WHERE email = 'admin@logopaedie-test.de';
```

4. Danach erneut einloggen, damit der neue Token mit der Admin-Rolle ausgestellt wird

---

## 7. Verifizieren, dass alles bereit ist

Vor dem Start der Testfälle aus `TEST_PLAN.md` alle Punkte abhaken:

- [ ] Backend läuft auf `:8001` (`[Backend] Starting uvicorn...` im Terminal sichtbar)
- [ ] Frontend läuft auf `:3000` (`[Frontend] ready ...` im Terminal sichtbar)
- [ ] `curl http://localhost:8001/livez` → `{"status":"alive"}`
- [ ] `http://localhost:3000` lädt ohne Fehler
- [ ] Login mit `anna.mueller@logopaedie-test.de` / `Test1234!Demo` möglich → Dashboard sichtbar
- [ ] Login mit `admin@logopaedie-test.de` / `AdminTest1234!` möglich → Dashboard sichtbar
- [ ] `http://localhost:3000/admin/audit` als Admin erreichbar (keine 403, keine Weiterleitung)
- [ ] `http://localhost:3000/patienten` lädt ohne Fehler

---

## 8. Bekannte Stolperfallen

### `GROQ_API_KEY` fehlt oder ungültig

**Symptom:** Berichtgenerierung, Audio-Upload und Transkription schlagen fehl.
Im Backend-Log: `AuthenticationError` oder `Invalid API key`.

**Lösung:** Gültigen Key von [console.groq.com](https://console.groq.com) holen und in `backend/.env` eintragen. Backend neu starten.

---

### SMTP nicht konfiguriert — kein E-Mail empfangen

**Symptom:** Nach Registrierung kommt keine E-Mail. Das ist **kein Fehler** — der
Console-Fallback ist aktiv. Den Verifizierungslink im Backend-Terminal lesen (Abschnitt 6).

---

### `backend/.env` fehlt — `dev.sh` bricht sofort ab

**Symptom:**
```
[Backend] Missing .env file — copy from .env.example:
  cp backend/.env.example backend/.env
```

**Lösung:**
```bash
cp backend/.env.example backend/.env
```
Dann Pflicht-Variablen aus Abschnitt 3.2 befüllen.

---

### Port `:8001` oder `:3000` bereits belegt

**Symptom:** `Address already in use` im Terminal.

**Lösung:**

```bash
# Wer belegt Port 8001?
lsof -i :8001
# Wer belegt Port 3000?
lsof -i :3000

# Prozess beenden (PID aus lsof-Ausgabe entnehmen):
kill <PID>
```

---

### `SESSION_ENCRYPTION_KEY` oder `PATIENT_ENCRYPTION_KEY` fehlt

**Symptom:** Backend startet, aber Login oder Patientenanlage schlägt mit `500 Internal Server Error` fehl. Im Log: `ValueError: PATIENT_ENCRYPTION_KEY is not set` oder ähnlich.

**Lösung:** Fernet-Schlüssel generieren (siehe Abschnitt 3.2) und in `.env` eintragen.

---

### Alembic-Fehler beim ersten Start

**Symptom:** `alembic.util.exc.CommandError: Can't locate revision identified by ...`

**Lösung:** Datenbank zurücksetzen (nur lokal/SQLite):

```bash
cd backend
rm -f reports.db
python -m alembic upgrade head
```

---

### Admin-Rolle nicht übernommen nach SQL-Update

**Symptom:** `/admin/audit` zeigt 403, obwohl SQL ausgeführt wurde.

**Ursache:** Der bestehende JWT enthält die alte Rolle. Der Token wird nicht automatisch invalidiert.

**Lösung:** Ausloggen und erneut einloggen — der neue Token enthält dann die Admin-Rolle.

---

## 9. Test beenden und aufräumen

**Services stoppen:**

```bash
# Im Terminal mit laufendem dev.sh:
Ctrl+C
```

Das Skript fährt Backend und Frontend sauber herunter (`kill 0`).

**Testdaten aus SQLite löschen (optional):**

```bash
cd backend
rm -f reports.db
```

Beim nächsten Start wird eine leere Datenbank angelegt.

**Testdaten aus PostgreSQL löschen (optional):**

```sql
-- Nur Testbenutzer entfernen (löscht verknüpfte Sessions/Reports via CASCADE):
DELETE FROM users WHERE email IN (
  'anna.mueller@logopaedie-test.de',
  'admin@logopaedie-test.de'
);
```

---

## Weiterführende Dokumente

- `TEST_PLAN.md` — alle Testfälle (TC-AUTH-001 bis TC-UX-005)
- `TEST_DATA.md` — Testpatienten, Audiodateien, Anamnese-Antworten
- `TEST_REPORT.md` — Ergebnisse eintragen
- `../../CLAUDE.md` — vollständige Projektdokumentation (Stack, API-Endpunkte, Deploy)
