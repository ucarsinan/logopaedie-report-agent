"""M-5: generated report PDFs must carry a visible AI/draft disclaimer, since
these are AI-drafted clinical documents that require professional review.
"""

from __future__ import annotations

from unittest.mock import MagicMock


def test_footer_draws_ai_disclaimer():
    from services.pdf_generator import AI_DISCLAIMER, _make_footer

    canvas = MagicMock()
    canvas._generated_at = "29.05.2026"
    doc = MagicMock()
    doc.page = 1

    _make_footer(canvas, doc)

    drawn = " ".join(str(call.args[-1]) for call in canvas.drawCentredString.call_args_list)
    assert AI_DISCLAIMER in drawn


def test_footer_branding_uses_stubbed_generated_at():
    from services.pdf_generator import _make_footer

    canvas = MagicMock()
    canvas._generated_at = "29.05.2026"
    doc = MagicMock()
    doc.page = 1

    _make_footer(canvas, doc)

    drawn = " ".join(str(call.args[-1]) for call in canvas.drawCentredString.call_args_list)
    assert "29.05.2026" in drawn
    assert "<MagicMock" not in drawn


def test_disclaimer_mentions_ai_and_review():
    from services.pdf_generator import AI_DISCLAIMER

    low = AI_DISCLAIMER.lower()
    assert "ki" in low  # KI-generiert
    assert "prüf" in low or "freigabe" in low or "freigeben" in low
