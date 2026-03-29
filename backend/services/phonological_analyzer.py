"""Automatic phonological process analysis for speech therapy.

Compares target words with a child's production and identifies
phonological processes (Vorverlagerung, Rückverlagerung, etc.).
"""

from __future__ import annotations

from backend.models.schemas import PhonologicalAnalysis
from backend.services.groq_client import GroqService

_SYSTEM_PROMPT = """\
Du bist ein Experte für phonologische Analyse in der deutschen Logopädie.
Du analysierst die Aussprache von Kindern, indem du das Zielwort mit der
tatsächlichen Produktion des Kindes vergleichst.

## Deine Aufgabe
Analysiere jedes Wortpaar (Zielwort vs. Produktion) und identifiziere
die vorliegenden phonologischen Prozesse.

## Phonologische Prozesse im Deutschen (mit Beispielen)

### Substitutionsprozesse:
- **Vorverlagerung (Anterioration):** Velare/posteriore Laute werden durch anteriore ersetzt
  → /k/→/t/, /g/→/d/, /ŋ/→/n/ (z.B. "Kanne"→"Tanne")
- **Rückverlagerung (Posterioration):** Anteriore Laute werden durch posteriore ersetzt
  → /t/→/k/, /d/→/g/ (z.B. "Tür"→"Kür")
- **Plosivierung (Stopping):** Frikative/Affrikaten werden durch Plosive ersetzt
  → /f/→/p/, /s/→/t/, /ʃ/→/t/ (z.B. "Fisch"→"Pisch")
- **Frikativierung:** Plosive werden durch Frikative ersetzt
  → /t/→/s/, /k/→/x/
- **Deaffrizierung:** Affrikaten werden vereinfacht
  → /pf/→/f/, /ts/→/s/ (z.B. "Pferd"→"Ferd")
- **Glottalisierung:** Laute werden durch Glottalstop ersetzt
  → /k/→/ʔ/, /t/→/ʔ/
- **Labialisierung:** Nicht-labiale Laute werden durch labiale ersetzt
  → /t/→/p/, /s/→/f/

### Strukturprozesse:
- **Reduktion von Konsonantenverbindungen (Cluster Reduction):**
  → /kl/→/l/, /ʃt/→/t/, /br/→/b/ (z.B. "Kleid"→"Leid")
- **Silbenstrukturprozesse:**
  - Auslassung unbetonter Silben (z.B. "Banane"→"Nane")
  - Auslassung finaler Konsonanten (z.B. "Hund"→"Hun")
  - Tilgung initialer Konsonanten

### Assimilationsprozesse:
- **Progressive Assimilation:** Vorausgehender Laut beeinflusst folgenden
- **Regressive Assimilation:** Folgender Laut beeinflusst vorausgehenden
  → (z.B. "Tasche"→"Kasche" – /k/ von hinten beeinflusst /t/)

### Altersgemäße Einordnung (Richtwerte):
- Bis 2;6 Jahre: Vorverlagerung, Cluster-Reduktion, Auslassung finaler Konsonanten normal
- Bis 3;6 Jahre: Plosivierung, Deaffrizierung können noch auftreten
- Bis 4;0 Jahre: /ʃ/ kann noch durch /s/ ersetzt werden (Schetismus)
- Bis 5;0 Jahre: /s/ kann noch interdental sein (Sigmatismus)
- Ab 5;0 Jahre: Alle Laute sollten korrekt produziert werden

## Ausgabeformat
Antworte AUSSCHLIESSLICH mit einem JSON-Objekt:
{{
  "items": [
    {{
      "target_word": "<Zielwort>",
      "production": "<Produktion des Kindes>",
      "processes": ["<Prozess 1: Beschreibung>", "<Prozess 2: Beschreibung>"],
      "severity": "<leicht|mittel|schwer>"
    }}
  ],
  "summary": "<Zusammenfassende Einschätzung der phonologischen Entwicklung>",
  "age_appropriate": <true|false – basierend auf Alter falls angegeben>,
  "recommended_focus": ["<Empfohlener Therapieschwerpunkt 1>", "<...>"]
}}

## Wichtig
- Analysiere JEDEN Lautunterschied zwischen Zielwort und Produktion
- Benenne den konkreten Prozess mit IPA-Notation wo möglich
- Schweregrad: leicht = 1 Prozess, mittel = 2-3 Prozesse, schwer = 4+ Prozesse oder schwere Abweichung
- Erfinde KEINE Prozesse – nur was aus dem Vergleich ersichtlich ist
"""


class PhonologicalAnalyzer:
    def __init__(self, groq: GroqService) -> None:
        self._groq = groq

    async def analyze(
        self,
        word_pairs: list[dict[str, str]],
        child_age: str | None = None,
    ) -> PhonologicalAnalysis:
        """Analyze phonological processes from target/production word pairs."""
        pairs_text = "\n".join(
            f"- Zielwort: \"{p['target']}\" → Produktion: \"{p['production']}\""
            for p in word_pairs
        )

        age_info = f"\nAlter des Kindes: {child_age}" if child_age else ""

        messages = [
            {
                "role": "user",
                "content": (
                    f"Analysiere die folgenden Wortpaare:{age_info}\n\n{pairs_text}\n\n"
                    "Antworte ausschließlich mit dem JSON-Objekt."
                ),
            }
        ]

        data = await self._groq.json_completion(messages, _SYSTEM_PROMPT)

        return PhonologicalAnalysis(
            items=[
                {
                    "target_word": item.get("target_word", ""),
                    "production": item.get("production", ""),
                    "processes": item.get("processes", []),
                    "severity": item.get("severity", "leicht"),
                }
                for item in data.get("items", [])
            ],
            summary=data.get("summary", ""),
            age_appropriate=data.get("age_appropriate", True),
            recommended_focus=data.get("recommended_focus", []),
        )

    async def analyze_audio(
        self,
        target_audio_path: str,
        production_audio_path: str,
        child_age: str | None = None,
    ) -> PhonologicalAnalysis:
        """Analyze from two audio recordings (target + production)."""
        target_text = await self._groq.transcribe_audio(target_audio_path)
        production_text = await self._groq.transcribe_audio(production_audio_path)

        # Split into individual words for pair-wise analysis
        target_words = target_text.strip().split()
        production_words = production_text.strip().split()

        # Pair up words (match by position)
        pairs = []
        for i, tw in enumerate(target_words):
            pw = production_words[i] if i < len(production_words) else ""
            pairs.append({"target": tw, "production": pw})

        return await self.analyze(pairs, child_age)
