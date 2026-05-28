"""Tests for PDF generation service."""

from __future__ import annotations

from services import pdf_generator
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

    def test_generate_pdf_no_cross_call_state_leak(self, monkeypatch):
        """Regression: header context must be per-call (closure), not module-global.

        Before the closure refactor, ``_HEADER_CTX`` was a module-level dict
        that ``generate_pdf`` mutated just before ``doc.build()``. As soon as
        the call was wrapped in ``loop.run_in_executor``, two concurrent
        renders would race on that dict and patient A's pseudonym could leak
        into patient B's running header. We simulate that race here by
        interleaving two renders via ``ThreadPoolExecutor`` and asserting
        that every ``_draw_header`` call still sees the pseudonym of the
        render that originated it.
        """
        from concurrent.futures import ThreadPoolExecutor
        from threading import Event, Lock

        per_thread: dict[int, list[str]] = {}
        lock = Lock()
        first_in_header = Event()
        proceed = Event()

        original = pdf_generator._draw_header

        def _spy(canvas, doc, ctx):
            # Force interleaving: PATIENT-A's first header call blocks until
            # PATIENT-B's render has started and reassigned its own context.
            # Under the old module-global design this would corrupt A's ctx;
            # with the closure each render keeps its own.
            import threading

            tid = threading.get_ident()
            with lock:
                per_thread.setdefault(tid, []).append(ctx.patient)
            if ctx.patient == "PATIENT-A" and not first_in_header.is_set():
                first_in_header.set()
                proceed.wait(timeout=5.0)
            return original(canvas, doc, ctx)

        monkeypatch.setattr(pdf_generator, "_draw_header", _spy)

        long_text = ("Lorem ipsum dolor sit amet. " * 200).strip()

        def _content(pseudonym: str) -> dict:
            return {
                "report_type": "befundbericht",
                "patient": {"pseudonym": pseudonym},
                "anamnese": long_text,
                "befund": long_text,
            }

        with ThreadPoolExecutor(max_workers=2) as pool:
            fut_a = pool.submit(generate_pdf, _content("PATIENT-A"))
            assert first_in_header.wait(timeout=5.0), "render A never reached _draw_header"
            fut_b = pool.submit(generate_pdf, _content("PATIENT-B"))
            # Give B's render time to enter _draw_header (and thus race on
            # any shared context) before we let A continue.
            import time

            time.sleep(0.2)
            proceed.set()
            fut_a.result(timeout=10.0)
            fut_b.result(timeout=10.0)

        assert per_thread, "_draw_header was never called"
        # Each thread must only ever have seen its own pseudonym — no leak.
        for tid, seen in per_thread.items():
            unique = set(seen)
            assert len(unique) == 1, (
                f"thread {tid} saw mixed pseudonyms {unique} — header context leaked across renders"
            )
