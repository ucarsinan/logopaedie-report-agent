"""M-2: the generative clinical prompts (phonology, SOAP, therapy plan) must be
grounded — no forced/invented findings, age judgments tied to norms, and the
SOAP subjective attributed to the right source (caregiver for young children).
"""

from __future__ import annotations


def test_phonology_prompt_is_grounded():
    from services.phonological_analyzer import _SYSTEM_PROMPT

    low = _SYSTEM_PROMPT.lower()
    assert "faktentreue" in low
    # only label processes actually derivable; don't force a known label
    assert "erfinde" in low
    # age-appropriateness must reference typical resolution ages, not a guess
    assert "abbaualter" in low


def test_soap_prompt_is_grounded():
    from services.soap_generator import _SOAP_SYSTEM_PROMPT

    low = _SOAP_SYSTEM_PROMPT.lower()
    assert "faktentreue" in low
    assert "erfinde" in low
    # subjective of a young child is the caregiver's report
    assert "bezugsperson" in low


def test_therapy_plan_prompt_is_grounded():
    from services.therapy_planner import _SYSTEM_PROMPT

    low = _SYSTEM_PROMPT.lower()
    assert "faktentreue" in low
    assert "erfinde" in low
    # proposed frequency/sessions are recommendations, not measured baselines
    assert "richtwert" in low or "empfehlung" in low
