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

# ── ICD-10 derived deterministically from the indication key (no asking) ─────
ICD_BY_INDIKATION: dict[str, list[str]] = {
    "SP1": ["F80.1"],  # TODO: fachlich bestätigen
    "SP2": ["F80.20"],  # TODO: fachlich bestätigen
    "SP3": ["F80.0"],  # TODO: fachlich bestätigen
    "SP4": ["H90.3"],  # TODO: fachlich bestätigen
    "SP5": ["R47.0"],  # TODO: fachlich bestätigen
    "SP6": ["R47.1"],  # TODO: fachlich bestätigen
    "ST1": ["R49.0"],  # TODO: fachlich bestätigen
    "ST2": ["R49.0"],  # TODO: fachlich bestätigen
    "SC1": ["R13.0"],  # TODO: fachlich bestätigen
    "RE1": ["F98.5"],
    "RE2": ["F98.6"],
    "OFD": ["F80.8"],  # TODO: fachlich bestätigen
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
