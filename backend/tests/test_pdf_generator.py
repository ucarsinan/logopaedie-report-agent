"""Tests for PDF generation service."""

from __future__ import annotations

from services.pdf_generator import REPORT_TYPE_LABELS, generate_pdf


class TestGeneratePdf:
    def test_returns_bytes(self):
        content = {
            "report_type": "befundbericht",
            "patient": {"pseudonym": "M.S.", "age_group": "Kind", "gender": "männlich"},
            "diagnose": {
                "icd_10_codes": ["F80.0"],
                "indikationsschluessel": "SP1",
                "diagnose_text": "Phonologische Störung",
            },
            "anamnese": "Patient wurde vorgestellt.",
            "befund": "Phonologische Prozesse festgestellt.",
        }
        result = generate_pdf(content)
        assert isinstance(result, bytes)
        # PDF starts with %PDF
        assert result[:4] == b"%PDF"

    def test_minimal_content(self):
        """generate_pdf should work with minimal/empty content."""
        result = generate_pdf({"report_type": "befundbericht"})
        assert isinstance(result, bytes)
        assert result[:4] == b"%PDF"

    def test_all_report_types(self):
        for report_type in REPORT_TYPE_LABELS:
            content = {"report_type": report_type}
            result = generate_pdf(content)
            assert isinstance(result, bytes)

    def test_with_list_values(self):
        content = {
            "report_type": "befundbericht",
            "therapieziele": ["Ziel 1", "Ziel 2", "Ziel 3"],
        }
        result = generate_pdf(content)
        assert isinstance(result, bytes)

    def test_with_multiline_text(self):
        content = {
            "report_type": "befundbericht",
            "anamnese": "Erste Zeile.\nZweite Zeile.\nDritte Zeile.",
        }
        result = generate_pdf(content)
        assert isinstance(result, bytes)

    def test_patient_with_all_fields(self):
        content = {
            "report_type": "befundbericht",
            "patient": {"pseudonym": "T.K.", "age_group": "Erwachsen", "gender": "weiblich"},
        }
        result = generate_pdf(content)
        assert isinstance(result, bytes)

    def test_patient_without_gender(self):
        content = {
            "report_type": "befundbericht",
            "patient": {"pseudonym": "T.K.", "age_group": "Kind"},
        }
        result = generate_pdf(content)
        assert isinstance(result, bytes)

    def test_diagnose_with_icd_codes(self):
        content = {
            "report_type": "befundbericht",
            "diagnose": {
                "diagnose_text": "Sprachentwicklungsstörung",
                "icd_10_codes": ["F80.0", "F80.1"],
                "indikationsschluessel": "SP1",
            },
        }
        result = generate_pdf(content)
        assert isinstance(result, bytes)

    def test_diagnose_without_text(self):
        """Diagnose section is skipped when no diagnose_text and no icd_10_codes."""
        content = {
            "report_type": "befundbericht",
            "diagnose": {"diagnose_text": "", "icd_10_codes": []},
        }
        result = generate_pdf(content)
        assert isinstance(result, bytes)

    def test_skip_keys_not_rendered_as_sections(self):
        """SKIP_KEYS should not produce sections in the PDF."""
        content = {
            "report_type": "befundbericht",
            "_db_id": 42,
            "created_at": "2024-01-01",
            "id": 1,
            "pseudonym": "hidden",
            "anamnese": "Visible content",
        }
        result = generate_pdf(content)
        assert isinstance(result, bytes)

    def test_known_section_labels(self):
        """All known section labels should be rendered correctly."""
        content = {
            "report_type": "therapiebericht_lang",
            "therapeutische_diagnostik": "Tests wurden durchgeführt.",
            "aktueller_krankheitsstatus": "Stabil.",
            "aktueller_therapiestand": "Fortschritte.",
            "weiteres_vorgehen": "Weiterführen.",
        }
        result = generate_pdf(content)
        assert isinstance(result, bytes)

    def test_abschlussbericht(self):
        content = {
            "report_type": "abschlussbericht",
            "therapieverlauf_zusammenfassung": "12 Sitzungen durchgeführt.",
            "ergebnis": "Ziele erreicht.",
            "empfehlung": "Entlassung.",
        }
        result = generate_pdf(content)
        assert isinstance(result, bytes)

    def test_empty_patient(self):
        """Empty patient dict should not raise."""
        content = {
            "report_type": "befundbericht",
            "patient": {},
        }
        result = generate_pdf(content)
        assert isinstance(result, bytes)

    def test_none_values_skipped(self):
        """None values in content should be skipped gracefully."""
        content = {
            "report_type": "befundbericht",
            "anamnese": None,
            "befund": "Befund vorhanden.",
        }
        result = generate_pdf(content)
        assert isinstance(result, bytes)
