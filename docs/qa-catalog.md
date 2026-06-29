# Frage-Antwort-Katalog (Q&A) — Logopädie Report Agent MVP

Dieser Katalog bereitet Sie systematisch auf Fragen vor, die während und nach Ihrer MVP-Präsentation gestellt werden können. Er ist logisch aufgebaut: von allgemeinen Fragen zu Produkt und Idee über tiefe technische Fragen zur KI-Pipeline und Systemarchitektur bis hin zu kritischen Fragen bzgl. Datenschutz (DSGVO) und Qualitätssicherung.

---

## Inhaltsverzeichnis
1. [Kategorie A: Idee, Produkt & Mehrwert (High-Level)](#1-kategorie-a-idee-produkt--mehrwert-high-level)
2. [Kategorie B: KI-Technologien & Prompt-Engineering](#2-kategorie-b-ki-technologien--prompt-engineering)
3. [Kategorie C: Software-Architektur & Systemkomponenten](#3-kategorie-c-software-architektur--systemkomponenten)
4. [Kategorie D: Datensicherheit, Verschlüsselung & DSGVO-Konformität](#4-kategorie-d-datensicherheit-verschl%C3%BCsselung--dsgvo-konformit%C3%A4t)
5. [Kategorie E: Testing, DevOps & Deployment](#5-kategorie-e-testing-devops--deployment)

---

## 1. Kategorie A: Idee, Produkt & Mehrwert (High-Level)

### F1: Was genau macht der Logopädie Report Agent und welchen Nutzen bringt er?
*   **Antwort:** Das MVP demonstriert einen intelligenten Dokumentationsassistenten für Logopäd:innen mit synthetischen Demo-Daten. Es begleitet den Dokumentationszyklus exemplarisch: Text- oder Demo-Audio-Anamnese, Transkription, hochgeladene Beispieldokumente und strukturierte fachsprachliche Berichtsentwürfe (nach ICF/SGB V). Zudem zeigt es SOAP-Notizen, Therapiepläne und Ausspracheanalysen.
*   **Mehrwert:** Zeiteinsparung (bis zu 30-40% der Arbeitszeit von Logopäd:innen fließt in Administration), Reduzierung der kognitiven Last während der Therapie (kein hektisches Mitschreiben nötig) und Qualitäts-Standardisierung.

### F2: Warum reicht es nicht, einfach ChatGPT mit einem System-Prompt zu nutzen?
*   **Antwort:** ChatGPT ist für den klinischen Alltag unzureichend:
    1.  **Fehlende Struktur:** LLMs neigen ohne technologische Gatter zum Halluzinieren oder weichen vom JSON-Schema ab. Das MVP reduziert dieses Risiko über Pydantic-Schemas, API-JSON-Modi und Backend-Validierung, statt ungeprüften Freitext direkt zu speichern.
    2.  **Datenschutz:** Patientendaten dürfen nicht ungefiltert in US-Systeme fließen. Das aktuelle MVP nutzt Groq nur für synthetische Demo-Daten; für echten Praxiseinsatz müsste eine separate lokale oder EU-basierte Provider- und Compliance-Architektur implementiert werden.
    3.  **Integrierter Workflow:** Ein einzelner Chatbot bietet keinen automatischen PDF-Export, keinen Vor- und Nachher-Vergleich von Berichten, keine phonologische Wortpaar-Analyse und keine strukturierte Speicherung von Patienten-IDs.

### F3: Wer ist die Zielgruppe und ist das Tool für den echten Praxiseinsatz gedacht?
*   **Antwort:** Die primäre Zielgruppe sind niedergelassene Logopäd:innen sowie logopädische Praxen. Dieses MVP ist aktuell ein lauffähiger Portfolio-Prototyp (Showcase) für synthetische Demo-Daten und nutzt heute direkt Groq für STT/NLP. Für produktiven Praxiseinsatz in Deutschland müsste zuerst eine separate Provider- und Compliance-Architektur implementiert werden, z. B. mit lokaler KI oder einem geeigneten EU-Provider, inklusive rechtlicher Prüfung sowie AVV/DPA/ZDR-Regelungen je nach Anbieter und Betriebsmodell.

---

## 2. Kategorie B: KI-Technologien & Prompt-Engineering

### F4: Warum wurde Groq als Inferenz-Provider gewählt und nicht OpenAI oder Azure?
*   **Antwort:** **Geschwindigkeit (Latenz).** Groq nutzt spezialisierte LPU-Chips (Language Processing Units), die Whisper (STT) und Llama 3.3 (NLP) in Bruchteilen von Sekunden verarbeiten. Für ein interaktives Audio-Interface im klinischen Gespräch ist eine Inferenzgeschwindigkeit von >100 Tokens/Sekunde entscheidend, damit Therapeut:innen nicht sekundenlang auf Transkripte warten müssen. Zudem bietet Groq ein exzellentes Preis-Leistungs-Verhältnis für das Prototyping.
*   **Alternativen & wieso verworfen:**
    *   *OpenAI API:* Langsamer in der Transkription und teurer im API-Aufruf.
    *   *Lokales Whisper:* Zu rechenintensiv für Standard-Developer-Laptops oder günstige Hosting-Instanzen ohne dedizierte GPU.

### F5: Warum Llama-3.3-70b-versatile und nicht GPT-4o oder Claude 3.5 Sonnet?
*   **Antwort:** Llama-3.3-70b ist ein State-of-the-Art Open-Weights-Modell, das in vielen Benchmarks auf dem Niveau von kommerziellen Modellen agiert. Durch die Nutzung von Groq ist es extrem schnell. Für logopädische Dokumentation in deutscher Sprache ist das Modell hervorragend feinabgestimmt.
*   **Alternativen & wieso verworfen:**
    *   *GPT-4o / Claude 3.5:* Sehr stark, aber Closed-Source (Vendor-Lock-in) und deutlich teurer bei hohem Kontextaufkommen. Zudem widersprechen sie dem langfristigen Ziel, die Software komplett offline/lokal auf Praxisrechnern laufen zu lassen. Open-Weights-Modelle wie Llama können problemlos lokal migriert werden.

### F6: Wie wird sichergestellt, dass die KI-Generierung immer ein gültiges Datenformat liefert?
*   **Antwort:** Über zwei Mechanismen:
    1.  **JSON Mode (API-Ebene):** Wir weisen Groq an, Antworten strikt im JSON-Format zurückzugeben.
    2.  **Pydantic-Validierung (Backend-Ebene):** Das FastAPI-Backend parst das empfangene JSON gegen vordefinierte TypeScript-äquivalente Pydantic-Klassen. Schlägt die Validierung fehl (z. B. durch fehlende Felder oder falsche Typen), greift unser Exception-Handling und startet ggf. einen strukturierten Fallback.

### F7: Nutzt das Tool RAG (Retrieval-Augmented Generation) oder eine Vektordatenbank für die Dokumenten-Uploads?
*   **Antwort:** **Nein, bewusst nicht im MVP.** Da wir Dokumente (PDF/DOCX/TXT) sitzungsbezogen hochladen, passen die extrahierten Texte direkt in das große Kontextfenster von Llama-3.3 (128k Tokens). Ein RAG-System mit Chunking, Embeddings und einer Vektordatenbank wie pgvector oder Pinecone hätte für diesen Anwendungsfall die Latenz erhöht und unnötige Infrastrukturkosten verursacht. Das direkte Einfügen ("Injektion") des extrahierten Texts in den Systemprompt ist für Einzeltherapiesitzungen performanter und einfacher. RAG ist jedoch als Roadmap-Punkt für das praxisweite Durchsuchen historischer Akten vorgesehen.

---

## 3. Kategorie C: Software-Architektur & Systemkomponenten

### F8: Warum wurde FastAPI (Python) für das Backend gewählt und nicht Node.js/NestJS?
*   **Antwort:**
    1.  **Klinische & KI-Bibliotheken:** Python ist die Lingua Franca für KI. Bibliotheken wie `reportlab` (PDF-Generierung), `python-docx`, `PyPDF2` (Dokumentenverarbeitung) und Daten-Validierung (Pydantic v2) lassen sich in Python nativ und stabil orchestrieren.
    2.  **Performance:** FastAPI ist dank `asyncio` und `uvicorn` extrem schnell und ressourcenschonend.
    3.  **Typensicherheit mit SQLModel:** SQLModel verbindet Pydantic und SQLAlchemy. Dadurch definieren wir Tabellenschemata und API-Validierungsschemata in einer einzigen Python-Klasse, was Redundanz und Fehler im Monorepo minimiert.
*   **Alternativen & wieso verworfen:**
    *   *Node.js (NestJS):* Hervorragend für I/O-lastige Services, erfordert aber für PDF-Parsing und KI-Kopplung oft instabile Third-Party-Brücken oder Subprozesse.

### F9: Was ist das BFF-Pattern (Backend-for-Frontend) und warum verwenden Sie Next.js-Route-Handlers als Proxy?
*   **Antwort:** Das Frontend kommuniziert niemals direkt mit dem FastAPI-Backend. Stattdessen gehen alle Anfragen über die Next.js-Route-Handler (`src/app/backend-api/...`).
    *   **Grund:** **Sicherheit.** Die sensiblen JWT-Tokens (Access/Refresh) werden vom BFF in `httpOnly` und `Secure` Cookies im Browser des Nutzers gespeichert. JavaScript im Browser hat dadurch keinen Zugriff auf die Tokens (Schutz vor XSS-Angriffen). Der Next.js-Proxy fängt die Anfrage ab, liest das verschlüsselte Cookie aus, hängt das Token als `Authorization: Bearer`-Header an und leitet die Anfrage serverseitig an das FastAPI-Backend weiter.

### F10: Warum wird Redis für Sessions und PostgreSQL für Berichte genutzt?
*   **Antwort:**
    *   **Upstash Redis (Session-Store):** Der Anamnesechat, temporär transkribierte Audios und Uploads sind transiente Daten (flüchtig). Redis bietet extrem schnelle Lese-/Schreibzugriffe und besitzt ein integriertes TTL-Feature (Time-To-Live). Nach 24 Stunden verfallen die verschlüsselten Sessions automatisch. Das spart Speicherplatz und löscht Patientendaten zuverlässig.
    *   **Neon PostgreSQL (Persistenz-Store):** Generierte Berichte, SOAP-Notizen, Behandlungspläne und Benutzeraccounts müssen dauerhaft und relational gespeichert werden (z. B. Fremdschlüssel-Beziehung von Bericht zu Benutzer). PostgreSQL bietet ACID-Garantien, robuste Indizes und relationale Integrität.

---

## 4. Kategorie D: Datensicherheit, Verschlüsselung & DSGVO-Konformität

### F11: Logopäden unterliegen in Deutschland der Schweigepflicht (§203 StGB) und der DSGVO. Wie wird das gelöst?
*   **Antwort:** Für das **MVP (Demo/Portfolio)** wurden technische Schutzmechanismen für synthetische Demo-Daten umgesetzt:
    1.  **Pseudonymisierungs-Guidelines:** Systemprompts fordern, Echtnamen, Adressen oder Geburtsdaten nicht an die KI zu übergeben. Das ist ein Demo-Schutzmechanismus, keine rechtliche Freigabe für echte Patientendaten.
    2.  **Kurze Speicherzyklen:** Transiente Sessiondaten werden mit 24h TTL in Redis abgelegt und zusätzlich verschlüsselt. Das reduziert Demo-Risiken, ersetzt aber keine rechtliche Prüfung des Betriebsmodells.
*   **Für die Produktivversion (ADR-P1):**
    Die aktuelle Codebasis ist noch nicht über ein `AIProvider`-Interface oder einen `LocalProvider` abstrahiert, sondern nutzt Groq direkt für Demo-Workflows. Vor realer Verarbeitung von Patientendaten müsste diese Provider- und Compliance-Architektur erst implementiert und rechtlich geprüft werden:
    *   *Lokale Option:* `faster-whisper` für Speech-to-Text und ein lokal betriebenes LLM via Ollama/Llama ohne Cloud-Transfer.
    *   *EU-Provider-Option:* Geeigneter europäischer Anbieter mit rechtlich geprüfter Vertragslage.
    *   *Compliance-Gates:* AVV/DPA, ZDR bzw. Datenaufbewahrungsregeln, Schweigepflichtprüfung und Freigabe für das konkrete Betriebsmodell.

### F12: Wie schützt die Anwendung Daten im Cache (Data at Rest) und bei der Übertragung (Data in Transit)?
*   **Antwort:**
    *   **In Transit:** SSL/TLS-Verschlüsselung erzwingt HTTPS für alle Client-BFF-Backend-Verbindungen.
    *   **At Rest (Redis):** Alle in Upstash Redis abgelegten Anamnesedaten werden symmetrisch mittels **Fernet-Verschlüsselung** (`cryptography` Python-Bibliothek) verschlüsselt, bevor sie die FastAPI-Instanz verlassen. Selbst bei einem unbefugten Zugriff auf die Redis-Datenbank sind die Daten ohne den geheimen `SESSION_ENCRYPTION_KEY` unlesbar.

### F13: Warum gibt es ein Audit-Log und wie wird es befüllt?
*   **Antwort:** Im medizinischen Umfeld ist die Nachvollziehbarkeit Pflicht. Das Audit-Log (`audit_log`-Tabelle) speichert jede kritische Aktion (z. B. Login, Passwortänderung, Export eines PDF-Berichts) mit Zeitstempel, Benutzer-ID, Eventtyp (z. B. `user.pdf_exported`) und IP-Adresse.
    *   **Technische Umsetzung:** Um die API-Antwortzeit nicht zu blockieren, wird das Schreiben der Logeinträge über FastAPI **`BackgroundTasks`** asynchron im Hintergrund ausgeführt. Schlägt das Logging fehl, bricht die Hauptanfrage nicht ab, sondern meldet den Fehler im Server-Log.

---

## 5. Kategorie E: Testing, DevOps & Deployment

### F14: Wie wird die Qualität und Stabilität des Codes sichergestellt?
*   **Antwort:** Über ein mehrstufiges Test- und Qualitätssicherungssystem in einer CI/CD-Pipeline (GitHub Actions):
    1.  **Backend-Tests:** Über 530 automatisierte Pytest-Tests testen Services, Router, Auth-Flows und API-Grenzwerte.
    2.  **Frontend-Tests:** Vitest-Tests decken die UI-Komponenten ab.
    3.  **E2E-Tests:** 32 Playwright E2E-Szenarien simulieren den kompletten Nutzerpfad (Login, 2FA, Patient anlegen, Bericht generieren, PDF exportieren) in einem Chromium-Browser.
    4.  **Static Code Analysis:** `ruff` für Backend-Linting, `mypy` für strenge Python-Typenprüfung und `tsc` für TypeScript-Validierung laufen bei jedem Commit.

### F15: Wie läuft das Vercel-Deployment ab und welche Grenzen gibt es?
*   **Antwort:** Die App wird als Next.js/FastAPI monorepo über Vercel (mittels `experimentalServices`) deployed.
    *   **Grenzen:** Da der Python-Backend-Teil als serverlose Funktion (Vercel Functions) läuft, kann es bei seltenem Zugriff zu "Cold Starts" kommen. Zudem greift ein maximales Payload-Limit von 25 MB für Audio-Uploads. Das ist für MVP-Zwecke (typische Audio-Schnipsel von 5–10 Minuten) absolut ausreichend.
