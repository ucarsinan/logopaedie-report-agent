"""Pure-logic tests for the slot-driven anamnesis catalog and controller."""

from __future__ import annotations

from services.anamnesis_catalog import (
    ANAMNESE,
    CATEGORY_BY_INDIKATION,
    HEAD,
    ICD_BY_INDIKATION,
    REPORT_SEQUENCE,
    build_sequence,
    next_slot,
)

_ALL_INDIKATION = {"SP1", "SP2", "SP3", "SP4", "SP5", "SP6", "ST1", "ST2", "SC1", "RE1", "RE2", "OFD"}


def test_head_first_slot_is_pseudonym():
    assert HEAD[0].key == "patient_pseudonym"


def test_age_group_slot_has_options():
    age = next(s for s in HEAD if s.key == "age_group")
    assert age.options == ["Kind", "Jugendliche/r", "Erwachsene/r"]


def test_icd_map_covers_all_indikation():
    assert set(ICD_BY_INDIKATION) == _ALL_INDIKATION
    assert ICD_BY_INDIKATION["RE1"] == ["F98.5"]
    assert ICD_BY_INDIKATION["RE2"] == ["F98.6"]


def test_category_map_covers_all_indikation():
    assert set(CATEGORY_BY_INDIKATION) == _ALL_INDIKATION
    assert CATEGORY_BY_INDIKATION["RE1"] == "redefluss"
    assert CATEGORY_BY_INDIKATION["SP5"] == "neuro"


def test_anamnese_has_default_for_every_category():
    for cat in {"sprache_kind", "neuro", "stimme", "dysphagie", "redefluss"}:
        assert "_default" in ANAMNESE[cat], f"{cat} missing _default"


def test_anamnese_slots_reuse_known_field_keys():
    known = {
        "sprachentwicklung",
        "motorische_entwicklung",
        "hoervermögen",
        "anamnese_familie",
        "mehrsprachigkeit",
        "symptombeginn",
        "ursache",
        "auswirkung_alltag",
        "bisherige_behandlung",
        "stimmbelastung",
        "hno_befund",
        "kostform",
        "aspirationszeichen",
    }
    for cat, by_age in ANAMNESE.items():
        for age, slots in by_age.items():
            for s in slots:
                assert s.key in known, f"{cat}/{age}: unknown slot key {s.key}"


def test_report_sequence_covers_four_types():
    assert set(REPORT_SEQUENCE) == {
        "befundbericht",
        "therapiebericht_kurz",
        "therapiebericht_lang",
        "abschlussbericht",
    }


def test_befundbericht_sequence_ends_with_diagnose():
    keys = [s.key for s in REPORT_SEQUENCE["befundbericht"]]
    assert keys[:3] == ["patient_pseudonym", "age_group", "indikationsschluessel"]
    assert keys[-1] == "diagnose_text"
    assert "__anamnese__" in keys  # placeholder marker expanded at runtime


def test_build_sequence_expands_anamnese_marker_by_category_and_age():
    seq = build_sequence("befundbericht", "RE1", "jugendlich")
    keys = [s.key for s in seq]
    assert "__anamnese__" not in keys
    assert "sprachentwicklung" in keys  # from redefluss/_default
    assert keys[0] == "patient_pseudonym"
    assert keys[-1] == "diagnose_text"


def test_build_sequence_without_disorder_stops_at_head():
    seq = build_sequence("befundbericht", None, None)
    keys = [s.key for s in seq]
    assert keys == ["patient_pseudonym", "age_group", "indikationsschluessel"]


def test_next_slot_returns_first_unfilled_required():
    collected = {"patient_pseudonym": "DL"}
    slot = next_slot("befundbericht", "RE1", "jugendlich", collected)
    assert slot.key == "age_group"


def test_next_slot_returns_none_when_all_filled():
    collected = {
        "patient_pseudonym": "DL",
        "age_group": "jugendlich",
        "indikationsschluessel": "RE1",
        "sprachentwicklung": "spät",
        "hoervermögen": "eingeschränkt",
        "symptombeginn": "mit 5",
        "bisherige_behandlung": "keine",
        "anamnese_familie": "keine",
        "auswirkung_alltag": "negativ",
        "diagnose_text": "Stottern",
    }
    assert next_slot("befundbericht", "RE1", "jugendlich", collected) is None


def test_next_slot_skips_optional_slots():
    assert (
        next_slot(
            "therapiebericht_kurz",
            "ST2",
            "erwachsen",
            {
                "patient_pseudonym": "DL",
                "age_group": "erwachsen",
                "indikationsschluessel": "ST2",
            },
        ).key
        == "therapieziele"
    )
