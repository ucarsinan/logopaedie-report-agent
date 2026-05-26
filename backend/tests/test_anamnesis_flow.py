"""Pure-logic tests for the slot-driven anamnesis catalog and controller."""

from __future__ import annotations

from services.anamnesis_catalog import (
    CATEGORY_BY_INDIKATION,
    HEAD,
    ICD_BY_INDIKATION,
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
