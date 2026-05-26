"""Slot catalog (pure data) for the slot-driven anamnesis flow.

Slot keys reuse existing collected_data field names so report_generator.py
and the extraction prompt keep working unchanged. No LLM, no I/O here.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Slot:
    key: str
    ask: str
    options: list[str] | None = None
    optional: bool = False


# ── Common head: asked for every report type, in this order ──────────────────
HEAD: list[Slot] = [
    Slot("patient_pseudonym", "nach dem Pseudonym oder den Initialen des Patienten"),
    Slot("age_group", "nach der Altersgruppe", options=["Kind", "Jugendliche/r", "Erwachsene/r"]),
    Slot(
        "indikationsschluessel",
        "nach dem Störungsbild bzw. Indikationsschlüssel",
        options=["SP1", "SP2", "SP3", "SP4", "SP5", "SP6", "ST1", "ST2", "SC1", "RE1", "RE2", "OFD"],
    ),
]

# ── ICD-10-GM suggested deterministically from the indication key (no asking) ─
# Codes verified against ICD-10-GM-2026 (BfArM, via icd-code.de) and the
# Heilmittelkatalog (Stimm-, Sprech-, Sprach- und Schlucktherapie). These are
# *suggestions* for the report; the therapist remains responsible for the final
# diagnosis code. Where the precise code is case-dependent, a note explains it.
ICD_BY_INDIKATION: dict[str, list[str]] = {
    "SP1": ["F80.1"],  # Expressive Sprachstörung (Sprachentwicklungsstörung)
    "SP2": ["F80.20"],  # Auditive Verarbeitungs- und Wahrnehmungsstörung (AVWS)
    "SP3": ["F80.0"],  # Artikulationsstörung / Dyslalie
    "SP4": ["H90.3"],  # Hörverlust-bedingt; tatsächlicher H90.-/H91.-Code ist audiologisch fallabhängig
    "SP5": ["R47.0"],  # Dysphasie und Aphasie
    "SP6": ["R47.1"],  # Dysarthrie und Anarthrie (Sprechapraxie wäre R48.2)
    "ST1": ["R49.0"],  # Dysphonie (organisch bedingt)
    "ST2": ["R49.0"],  # Dysphonie (funktionell bedingt)
    "SC1": ["R13.9"],  # Dysphagie o.n.A. (R13.0 nur bei Beaufsichtigungspflicht/Aspirationsrisiko)
    "RE1": ["F98.5"],  # Stottern
    "RE2": ["F98.6"],  # Poltern
    "OFD": ["F80.8"],  # Myofunktionelle Störung — kein präziser ICD-10-GM-Code; F80.8 als Näherung
}

# ── Maps an indication key to its anamnesis category ─────────────────────────
CATEGORY_BY_INDIKATION: dict[str, str] = {
    "SP1": "sprache_kind",
    "SP2": "sprache_kind",
    "SP3": "sprache_kind",
    "OFD": "sprache_kind",
    "SP4": "sprache_kind",
    "SP5": "neuro",
    "SP6": "neuro",
    "ST1": "stimme",
    "ST2": "stimme",
    "SC1": "dysphagie",
    "RE1": "redefluss",
    "RE2": "redefluss",
}

# ── Anamnesis topic slots per category, optionally per age group ─────────────
# Each category provides "_default"; add an age key only where it differs.
ANAMNESE: dict[str, dict[str, list[Slot]]] = {
    "sprache_kind": {
        "_default": [
            Slot("motorische_entwicklung", "wie die motorische Entwicklung verlief (Krabbeln, Laufen)"),
            Slot(
                "sprachentwicklung",
                "wie die Sprachentwicklung verlief (Lallen, erste Wörter, erste Sätze, Sprachverständnis)",
            ),
            Slot("hoervermögen", "nach Hörvermögen, HNO-Befunden und Paukenergüssen"),
            Slot("mehrsprachigkeit", "ob Mehrsprachigkeit vorliegt (welche Sprachen, Verteilung)"),
            Slot("anamnese_familie", "nach familiären Sprachauffälligkeiten"),
            Slot(
                "auswirkung_alltag", "nach Auswirkungen auf Kindergarten, Schule und die sozial-emotionale Entwicklung"
            ),
        ],
    },
    "neuro": {
        "_default": [
            Slot("symptombeginn", "seit wann die Symptome bestehen"),
            Slot("ursache", "nach der Ursache (z. B. Schlaganfall, OP, Trauma)"),
            Slot("bisherige_behandlung", "nach bisherigen Behandlungen und deren Ergebnissen"),
            Slot("auswirkung_alltag", "nach Auswirkungen auf Alltag und Beruf"),
        ],
    },
    "stimme": {
        "_default": [
            Slot("symptombeginn", "seit wann die Stimmprobleme bestehen"),
            Slot("stimmbelastung", "nach der beruflichen Stimmbelastung (z. B. Lehrer, Sänger)"),
            Slot("hno_befund", "nach dem HNO-/Stimmlippenbefund sowie Reflux, Allergien, Rauchen"),
            Slot("auswirkung_alltag", "nach Auswirkungen auf Alltag und Beruf"),
        ],
    },
    "dysphagie": {
        "_default": [
            Slot("ursache", "nach der Grunderkrankung (z. B. Schlaganfall, Parkinson, ALS)"),
            Slot("kostform", "nach der aktuellen Kostform und Flüssigkeitskonsistenz"),
            Slot("aspirationszeichen", "nach Aspirationszeichen (Husten beim Essen/Trinken)"),
            Slot("hno_befund", "nach vorhandenen FEES- oder Videofluoroskopie-Befunden"),
        ],
    },
    "redefluss": {
        "_default": [
            Slot("sprachentwicklung", "wie die Sprachentwicklung verlief"),
            Slot("hoervermögen", "nach Hörvermögen und HNO-Befunden"),
            Slot("symptombeginn", "seit wann die Redeflussstörung besteht und wie sie sich entwickelt hat"),
            Slot("bisherige_behandlung", "nach bisherigen Diagnosen oder Behandlungen"),
            Slot("anamnese_familie", "nach familiären Sprachauffälligkeiten"),
            Slot("auswirkung_alltag", "nach Auswirkungen auf Alltag, Schule oder Beruf"),
        ],
    },
}

# Marker expanded by build_sequence() into the matching ANAMNESE block.
_ANAMNESE_MARKER = Slot("__anamnese__", "")

# ── Ordered required slots per report type (mirrors _REQUIRED_FIELDS) ────────
REPORT_SEQUENCE: dict[str, list[Slot]] = {
    "befundbericht": [*HEAD, _ANAMNESE_MARKER, Slot("diagnose_text", "nach der zusammenfassenden Diagnose")],
    "therapiebericht_kurz": [*HEAD, Slot("therapieziele", "nach den aktuellen Therapiezielen")],
    "therapiebericht_lang": [
        *HEAD,
        _ANAMNESE_MARKER,
        Slot("diagnose_text", "nach der zusammenfassenden Diagnose"),
        Slot("therapieinhalte", "nach den bisherigen Therapieinhalten und -methoden"),
        Slot("fortschritte", "nach den Fortschritten seit Therapiebeginn"),
    ],
    "abschlussbericht": [
        *HEAD,
        Slot("therapieinhalte", "nach den bisherigen Therapieinhalten und -methoden"),
        Slot("anzahl_sitzungen", "nach der Anzahl der durchgeführten Sitzungen"),
        Slot("fortschritte", "nach den Fortschritten seit Therapiebeginn"),
        Slot("kooperation", "nach der Kooperation und Mitarbeit des Patienten bzw. der Eltern"),
    ],
}


def _anamnese_block(indikation: str | None, age_group: str | None) -> list[Slot]:
    if not indikation:
        return []
    category = CATEGORY_BY_INDIKATION.get(indikation)
    if not category or category not in ANAMNESE:
        return []
    by_age = ANAMNESE[category]
    return list(by_age.get(age_group or "", by_age["_default"]))


def build_sequence(report_type: str, indikation: str | None, age_group: str | None) -> list[Slot]:
    """Concrete ordered slot list for one case; __anamnese__ marker expanded.

    When indikation is None the sequence is truncated at the first
    __anamnese__ marker (HEAD-only mode — nothing to ask about disorder yet).
    """
    template = REPORT_SEQUENCE.get(report_type, REPORT_SEQUENCE["befundbericht"])
    result: list[Slot] = []
    for slot in template:
        if slot.key == "__anamnese__":
            if indikation is None:
                break  # HEAD-only mode: we can't ask disorder-specific slots yet
            result.extend(_anamnese_block(indikation, age_group))
        else:
            result.append(slot)
    return result


def next_slot(report_type: str, indikation: str | None, age_group: str | None, collected: dict) -> Slot | None:
    """First unfilled, non-optional slot in the sequence, or None when done."""
    for slot in build_sequence(report_type, indikation, age_group):
        if slot.optional:
            continue
        value = collected.get(slot.key)
        if not value or value == [] or value == "":
            return slot
    return None


# Human labels for composing the anamnesis narrative (subset of report_generator labels).
_FIELD_LABELS: dict[str, str] = {
    "motorische_entwicklung": "Motorische Entwicklung",
    "sprachentwicklung": "Sprachentwicklung",
    "hoervermögen": "Hörvermögen",
    "mehrsprachigkeit": "Mehrsprachigkeit",
    "anamnese_familie": "Familienanamnese",
    "symptombeginn": "Symptombeginn",
    "ursache": "Ursache",
    "bisherige_behandlung": "Bisherige Behandlung",
    "stimmbelastung": "Stimmbelastung",
    "hno_befund": "HNO-Befund",
    "kostform": "Kostform",
    "aspirationszeichen": "Aspirationszeichen",
    "auswirkung_alltag": "Auswirkung auf Alltag",
}


def options_line(slot: Slot) -> str | None:
    """Return slot options joined with en-dash separators, or None when slot has no options."""
    if not slot.options:
        return None
    return "– " + " – ".join(slot.options)


def compose_anamnese_persoenlich(
    report_type: str, indikation: str | None, age_group: str | None, collected: dict
) -> str:
    """Join filled anamnesis topic fields into one narrative string, in catalog order."""
    parts: list[str] = []
    for slot in _anamnese_block(indikation, age_group):
        value = collected.get(slot.key)
        if value and value != [] and value != "":
            label = _FIELD_LABELS.get(slot.key, slot.key)
            parts.append(f"{label}: {value}")
    return ". ".join(parts)
