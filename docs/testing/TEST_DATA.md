# TEST_DATA.md — Reale Testdaten

> Testdaten für manuelle Tests. Vor dem Testlauf bereithalten.
> Alle Patientennamen sind fiktiv.

---

## Testumgebung

| Wert | Standard |
|---|---|
| Frontend | http://localhost:3000 |
| Backend | http://localhost:8001 |
| Start | `./dev.sh` im Projekt-Root |
| Voraussetzung | `backend/.env` vorhanden + Groq API Key gesetzt |

---

## Testbenutzer

### Benutzer A — Therapeutin (Hauptkonto)

```
E-Mail:     anna.mueller@logopaedie-test.de
Passwort:   Test1234!Demo
Rolle:      user
2FA:        zunächst deaktiviert
```

### Benutzer B — Admin

```
E-Mail:     admin@logopaedie-test.de
Passwort:   AdminTest1234!
Rolle:      admin
2FA:        zunächst deaktiviert
```

> Hinweis: Beide Konten müssen vor dem Testlauf manuell registriert und
> E-Mail-verifiziert werden (TC-AUTH-001). Für Admin-Rechte muss Benutzer B
> in der DB manuell auf `role=admin` gesetzt werden (SQL-Snippet in Abschnitt
> "Hilfsbefehle" unten).

---

## Testpatienten

### Patient 1 — Emma Richter (Kind, Artikulationsstörung)

```
Vorname:        Emma
Nachname:       Richter
Geburtsdatum:   2018-03-15  (ca. 7 Jahre)
Pseudonym:      ER-2018
Diagnose:       Dyslalie — /r/- und /sch/-Substitution
Anmerkungen:    Schulkind, 1. Klasse; Eltern kooperativ
```

**Anamnese-Chatantworten (für TC-SES-002):**

| KI-Frage (erwartet) | Muster-Antwort |
|---|---|
| Beschreiben Sie das Hauptproblem | Emma spricht das /r/ als /w/ aus und das /sch/ als /s/. Auffällig seit dem 4. Lebensjahr. |
| Bisherige Therapien | Ja, 6 Monate Logopädie im Vorjahr mit mäßigem Fortschritt. |
| Familienanamnese | Vater hatte ähnliche Auffälligkeiten im Kindesalter. |
| Schulische Situation | 1. Klasse, lesen und schreiben gerade in der Lernphase. |
| Motivation | Emma ist motiviert und möchte „richtig sprechen wie die anderen". |

**Phonologische Testbeispiele (für TC-PHO-001):**

```
Wort:       Regen → Emma sagt: "Wegen"
Wort:       Schule → Emma sagt: "Sule"
Wort:       Frosch → Emma sagt: "Fwosch"
Wort:       Straße → Emma sagt: "Stwasse"
```

---

### Patient 2 — Thomas Bergmann (Erwachsener, Aphasie)

```
Vorname:        Thomas
Nachname:       Bergmann
Geburtsdatum:   1975-11-08  (ca. 50 Jahre)
Pseudonym:      TB-1975
Diagnose:       Broca-Aphasie nach Schlaganfall (2024-01-15)
Anmerkungen:    IT-Ingenieur, versteht gut, Produktion stark eingeschränkt
```

**Anamnese-Chatantworten (für TC-SES-002):**

| KI-Frage (erwartet) | Muster-Antwort |
|---|---|
| Beschreiben Sie das Hauptproblem | Thomas kann Gespräche gut verstehen, findet aber Wörter kaum. Produziert Einwort-Äußerungen und Floskeln. |
| Beginn der Symptome | Nach Schlaganfall am 15.01.2024, linke Hemisphäre betroffen. |
| Bisherige Therapien | Akutrehabilitation 4 Wochen, seitdem ambulante Logopädie 2× wöchentlich. |
| Beruf und Alltag | War IT-Ingenieur. Lebt mit Ehefrau. Braucht Hilfe bei Kommunikation im Alltag. |
| Ziele | Wieder selbstständig telefonieren können, kurze Sätze bilden. |

---

### Patient 3 — Lena Fischer (Kind, Stottern)

```
Vorname:        Lena
Nachname:       Fischer
Geburtsdatum:   2019-07-22  (ca. 5 Jahre)
Pseudonym:      LF-2019
Diagnose:       Poltern / beginnende Stottersymptomatik
Anmerkungen:    Vorschulkind; Eltern besorgt, Lena selbst unauffällig
```

**Anamnese-Chatantworten (für TC-SES-002):**

| KI-Frage (erwartet) | Muster-Antwort |
|---|---|
| Beschreiben Sie das Hauptproblem | Lena wiederholt Laute und Silben, besonders am Satzanfang. Aufgetreten seit ca. 6 Monaten. |
| Auslöser / Verlauf | Kurz nach Einschulung in Kita-Gruppe. Verschlimmert sich bei Aufregung. |
| Familienanamnese | Onkel väterlicherseits stottert. |
| Reaktion des Umfeldes | Eltern reagieren besorgt, manchmal ungeduldig. |
| Motivation | Lena selbst merkt es kaum; Eltern wollen früh intervenieren. |

---

## Audio-Testdaten

### Aufnahme A — Kurze Gesprächsszene (für TC-SES-003)

Nimm ca. 30–60 Sekunden auf (Telefon oder Mikrofon). Sprich:

```
"Emma war heute sehr aufmerksam. Wir haben das /r/-Phonem in Anlautposition
geübt: Wörter wie Regen, Rad und Rose. Emma produzierte /r/ in 6 von 10
Versuchen korrekt, was eine deutliche Verbesserung gegenüber der letzten
Sitzung darstellt. Die Motivation war hoch. Hausaufgabe: Wörter mit /r/
5-mal täglich üben."
```

**Erwartung nach Transkription:**
- Korrekte Wiedergabe aller Fachwörter
- Phoneme in Schrägstrichen erkannt

### Aufnahme B — Längere Sitzungszusammenfassung (für TC-SES-004)

```
"Heutige Therapiesitzung mit Thomas Bergmann. Dauer: 45 Minuten.
Beginn mit Entspannungsübungen. Dann Wortabruftraining anhand von Bildern:
Haushaltsgegenstände. Thomas konnte 12 von 20 Bilder korrekt benennen,
Fortschritt im Vergleich zur Vorwoche von 8 auf 12. Satzkonstruktion:
Thomas bildete 3 Zwei-Wort-Äußerungen spontan. Therapieplan für nächste
Woche: Satzmuster 'Ich will...' einführen."
```

---

## Erwartete Report-Strukturen

### Befundbericht — Emma Richter (erwartet)

```
Sektionen:
- Anamnese
- Befund (Aussprache, Phonologie)
- Diagnose (Dyslalie)
- Therapieempfehlung
- Prognose
```

### SOAP-Note — Thomas Bergmann (erwartet)

```
S (Subjektiv):  Patient berichtet von Fortschritten beim Benennen.
O (Objektiv):   12/20 Bilder korrekt benannt (vorher 8/20).
A (Assessment): Langsame aber stetige Verbesserung der Wortabruffähigkeit.
P (Plan):       Satzmuster 'Ich will...' nächste Woche einführen.
```

---

## Hilfsbefehle

### Admin-Rolle setzen (psql / Neon-Konsole)

```sql
UPDATE users SET role = 'admin' WHERE email = 'admin@logopaedie-test.de';
```

### Aktuellen Redis-Zustand prüfen (optional)

```bash
# Backend-Logs live verfolgen (wenn dev.sh läuft):
tail -f /private/tmp/logo-backend.log
```

### Backend-API direkt testen (curl)

```bash
# Health-Check
curl http://localhost:8001/livez

# Login
curl -X POST http://localhost:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"anna.mueller@logopaedie-test.de","password":"Test1234!Demo"}'
```
