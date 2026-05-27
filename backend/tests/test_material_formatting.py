"""L-3: long uploaded materials must not be silently cut. Keep more context and,
when a cut is unavoidable, mark it explicitly so the omission is visible.
"""

from __future__ import annotations

from models.schemas import UploadedMaterial
from services.report_generator import _MATERIAL_CHAR_BUDGET, _format_materials
from services.session_store import Session


def _session_with_material(text: str) -> Session:
    s = Session("aabbccddeeff")
    s.materials = [
        UploadedMaterial(
            filename="vorbefund.pdf",
            content_type="application/pdf",
            extracted_text=text,
            material_type="alter_bericht",
        )
    ]
    return s


def test_short_material_is_kept_verbatim():
    s = _session_with_material("Kurzer Vorbefund.")
    out = _format_materials(s)
    assert "Kurzer Vorbefund." in out
    assert "gekürzt" not in out.lower()


def test_long_material_truncation_is_marked_and_keeps_more_context():
    s = _session_with_material("A" * (_MATERIAL_CHAR_BUDGET + 5000))
    out = _format_materials(s)
    # Truncation is now explicit instead of a silent cut.
    assert "gekürzt" in out.lower()
    # And we retain meaningfully more than the old hard 2000-char cap.
    assert _MATERIAL_CHAR_BUDGET > 2000
    assert out.count("A") >= _MATERIAL_CHAR_BUDGET
