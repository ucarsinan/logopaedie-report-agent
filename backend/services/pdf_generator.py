"""Generate professional PDF reports using reportlab.

Design choices (logopedist-printable clinical report):

* Body font: Times-Roman (serif) — pairs well with clinical/legal printouts, high
  legibility in long paragraphs. Heading font: Helvetica-Bold (sans) — distinct,
  modern contrast against the body. Both ship with reportlab; no system fonts
  required, so the output is byte-identical across environments.
* A4 page with 25 mm top/bottom and 20 mm side margins. The first page leaves
  extra room at the top for the title block; later pages reserve space for the
  running header.
* Running header: patient pseudonym (left) + report-type label and report date
  (right), with a thin accent rule below.
* Running footer: praxis branding placeholder, AI disclaimer, and a real
  "Seite X von Y" counter (two-pass via a NumberedCanvas subclass).
* Section headings sit on their own line under a thin rule. Headings are
  wrapped in KeepTogether with the first paragraph to avoid orphaned single-
  line headings at the page break.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

logger = logging.getLogger(__name__)

REPORT_TYPE_LABELS = {
    "befundbericht": "Befundbericht",
    "therapiebericht_kurz": "Therapiebericht (kurz)",
    "therapiebericht_lang": "Therapiebericht (lang)",
    "abschlussbericht": "Abschlussbericht",
}

SECTION_LABELS = {
    "anamnese": "Anamnese",
    "befund": "Befund",
    "therapieindikation": "Therapieindikation",
    "therapieziele": "Therapieziele",
    "empfehlung": "Empfehlung",
    "empfehlungen": "Empfehlungen",
    "therapeutische_diagnostik": "Therapeutische Diagnostik",
    "aktueller_krankheitsstatus": "Aktueller Krankheitsstatus",
    "aktueller_therapiestand": "Aktueller Therapiestand",
    "weiteres_vorgehen": "Weiteres Vorgehen",
    "therapieverlauf_zusammenfassung": "Therapieverlauf",
    "ergebnis": "Ergebnis",
}

SKIP_KEYS = {
    "report_type",
    "patient",
    "diagnose",
    "_db_id",
    "created_at",
    "id",
    "pseudonym",
}

# Subtle, clinical color palette. No flashy accents.
_ACCENT = colors.HexColor("#1a1a2e")  # near-black indigo for headings/title
_RULE_COLOR = colors.HexColor("#c8ccd4")  # soft grey rule under headings
_META_LABEL = colors.HexColor("#555770")  # mid-grey for meta labels
_FOOTER_GREY = colors.HexColor("#666666")

# Body / heading font families. Both built-in to reportlab.
_BODY_FONT = "Times-Roman"
_BODY_BOLD = "Times-Bold"
_HEAD_FONT = "Helvetica-Bold"
_META_FONT = "Helvetica"

# TODO: real branding — replace with the actual praxis name/address once known.
_PRAXIS_BRAND = "Praxis Logopädie — Demo"

AI_DISCLAIMER = "KI-generierter Entwurf – vor Verwendung fachlich prüfen und freigeben."


def _build_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "ReportTitle",
            parent=base["Title"],
            fontName=_HEAD_FONT,
            fontSize=18,
            leading=22,
            spaceAfter=2,
            textColor=_ACCENT,
            alignment=0,  # left-aligned for a clinical letterhead feel
        ),
        "subtitle": ParagraphStyle(
            "ReportSubtitle",
            parent=base["Normal"],
            fontName=_META_FONT,
            fontSize=10,
            leading=13,
            textColor=_META_LABEL,
            spaceAfter=10,
        ),
        "heading": ParagraphStyle(
            "SectionHeading",
            parent=base["Heading2"],
            fontName=_HEAD_FONT,
            fontSize=12.5,
            leading=15,
            spaceBefore=14,
            spaceAfter=2,
            textColor=_ACCENT,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "BodyText",
            parent=base["Normal"],
            fontName=_BODY_FONT,
            fontSize=10.5,
            leading=15,
            spaceAfter=6,
            alignment=4,  # justify
            firstLineIndent=0,
        ),
        "bullet": ParagraphStyle(
            "BulletItem",
            parent=base["Normal"],
            fontName=_BODY_FONT,
            fontSize=10.5,
            leading=15,
            leftIndent=18,
            bulletIndent=6,
            spaceAfter=2,
        ),
        "meta_label": ParagraphStyle(
            "MetaLabel",
            parent=base["Normal"],
            fontName=_META_FONT,
            fontSize=9,
            leading=12,
            textColor=_META_LABEL,
        ),
        "meta_value": ParagraphStyle(
            "MetaValue",
            parent=base["Normal"],
            fontName=_BODY_FONT,
            fontSize=10,
            leading=12,
            textColor=colors.black,
        ),
        "sig_label": ParagraphStyle(
            "SigLabel",
            parent=base["Normal"],
            fontName=_META_FONT,
            fontSize=8,
            textColor=_META_LABEL,
        ),
    }


def _section_rule() -> HRFlowable:
    """Thin underline rule placed directly under a section heading."""
    return HRFlowable(
        width="100%",
        thickness=0.6,
        color=_RULE_COLOR,
        spaceBefore=1,
        spaceAfter=6,
    )


# ---------------------------------------------------------------------------
# Header / footer rendering
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _PageContext:
    """Per-render header context.

    Captured fresh per ``generate_pdf`` call and closed over by the page hooks,
    so concurrent renders (e.g. inside ``loop.run_in_executor``) cannot leak
    one report's pseudonym into another's running header.
    """

    patient: str
    type_label: str
    report_date: str


def _draw_header(canvas: Canvas, doc: Any, ctx: _PageContext) -> None:
    """Running header: patient (left) and report type + date (right)."""
    if doc.page == 1:
        # First page already shows the full title block; keep the chrome
        # minimal there so the title doesn't compete with the running header.
        return
    width, height = A4
    canvas.saveState()
    top_y = height - 15 * mm
    canvas.setFont(_META_FONT, 9)
    canvas.setFillColor(_META_LABEL)
    if ctx.patient:
        canvas.drawString(20 * mm, top_y, ctx.patient)
    right_label = " · ".join(part for part in (ctx.type_label, ctx.report_date) if part)
    if right_label:
        canvas.drawRightString(width - 20 * mm, top_y, right_label)
    canvas.setStrokeColor(_RULE_COLOR)
    canvas.setLineWidth(0.4)
    canvas.line(20 * mm, top_y - 3 * mm, width - 20 * mm, top_y - 3 * mm)
    canvas.restoreState()


def _make_footer(canvas: Canvas, doc: Any) -> None:
    """Draw the AI/draft disclaimer + branding/page number on every page.

    Signature stays ``(canvas, doc)`` so that downstream tests
    (``test_pdf_disclaimer.py``) can keep calling it directly. The page
    counter falls back to ``Seite {doc.page}`` here; ``NumberedCanvas`` below
    rewrites it on the second pass to ``Seite X von Y``.
    """
    canvas.saveState()
    width, _ = A4
    # Reuse the timestamp captured once on NumberedCanvas so the first-pass
    # branding line and the second-pass overdraw never disagree (midnight-UTC
    # edge). Falls back to "now" when called directly with a non-NumberedCanvas
    # (used by test_pdf_disclaimer.py).
    now = getattr(canvas, "_generated_at", None) or datetime.now(UTC).strftime("%d.%m.%Y")
    branding = f"{_PRAXIS_BRAND} | Erstellt am {now} | Seite {doc.page}"
    canvas.setFillColor(_FOOTER_GREY)
    canvas.setFont("Helvetica-Oblique", 8)
    canvas.drawCentredString(width / 2, 1.6 * cm, AI_DISCLAIMER)
    canvas.setFont(_META_FONT, 8)
    canvas.drawCentredString(width / 2, 1.2 * cm, branding)
    canvas.restoreState()


def _make_on_page_hook(ctx: _PageContext) -> Any:
    """Build a reportlab per-page hook closed over the given context."""

    def _on_page(canvas: Canvas, doc: Any) -> None:
        _draw_header(canvas, doc, ctx)
        _make_footer(canvas, doc)

    return _on_page


class NumberedCanvas(Canvas):
    """Two-pass canvas that resolves ``Seite X von Y`` in the footer.

    Reportlab does not know the total page count while building. The standard
    workaround is to buffer each page's state, then on ``save`` replay every
    page with the known total. We overdraw a tighter footer here that
    replaces the placeholder line drawn by ``_make_footer``.

    The "generated at" timestamp is captured once at construction so the first-
    pass footer and the overdrawn second-pass footer always agree, even if the
    build straddles midnight UTC.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._saved_page_states: list[dict[str, Any]] = []
        self._generated_at = datetime.now(UTC).strftime("%d.%m.%Y")

    def showPage(self) -> None:
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        total_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self._overdraw_footer(total_pages)
            super().showPage()
        super().save()

    def _overdraw_footer(self, total_pages: int) -> None:
        """Paint a small opaque rectangle over the placeholder branding line
        and redraw it with ``Seite X von Y``. The disclaimer line above is
        preserved as-is.
        """
        width, _ = A4
        branding = (
            f"{_PRAXIS_BRAND}  |  Erstellt am {self._generated_at}  |  Seite {self._pageNumber} von {total_pages}"
        )
        self.saveState()
        # Cover the previous branding line (drawn by _make_footer) with white.
        self.setFillColor(colors.white)
        self.setStrokeColor(colors.white)
        self.rect(0, 1.0 * cm, width, 0.45 * cm, fill=1, stroke=0)
        # Repaint with the final page count.
        self.setFillColor(_FOOTER_GREY)
        self.setFont(_META_FONT, 8)
        self.drawCentredString(width / 2, 1.2 * cm, branding)
        self.restoreState()


# ---------------------------------------------------------------------------
# Content rendering helpers
# ---------------------------------------------------------------------------


def _build_meta_table(patient: dict[str, Any], report_date: str, styles: dict[str, ParagraphStyle]) -> Table | None:
    """Two-column label/value meta block under the title.

    Returns None if there is nothing to render so callers can skip the table.
    """
    rows: list[list[Any]] = []
    label_style = styles["meta_label"]
    value_style = styles["meta_value"]

    def _row(label: str, value: str) -> None:
        rows.append([Paragraph(label, label_style), Paragraph(value, value_style)])

    if patient.get("pseudonym"):
        _row("Patient", str(patient["pseudonym"]))
    if patient.get("age_group"):
        _row("Altersgruppe", str(patient["age_group"]))
    if patient.get("gender"):
        _row("Geschlecht", str(patient["gender"]))
    if report_date:
        _row("Berichtsdatum", report_date)

    if not rows:
        return None

    tbl = Table(rows, colWidths=[3.2 * cm, 12 * cm], hAlign="LEFT")
    tbl.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return tbl


def _build_diagnose_block(diagnose: dict[str, Any], styles: dict[str, ParagraphStyle]) -> list[Any]:
    """Diagnose heading + text + optional ICD/indication table."""
    block: list[Any] = []
    if not (diagnose.get("diagnose_text") or diagnose.get("icd_10_codes") or diagnose.get("indikationsschluessel")):
        return block
    block.append(Paragraph("Diagnose", styles["heading"]))
    block.append(_section_rule())
    if diagnose.get("diagnose_text"):
        block.append(Paragraph(str(diagnose["diagnose_text"]), styles["body"]))

    rows: list[list[Any]] = []
    if diagnose.get("indikationsschluessel"):
        rows.append(
            [
                Paragraph("Indikationsschlüssel", styles["meta_label"]),
                Paragraph(str(diagnose["indikationsschluessel"]), styles["meta_value"]),
            ]
        )
    if diagnose.get("icd_10_codes"):
        codes = ", ".join(str(c) for c in diagnose["icd_10_codes"])
        rows.append(
            [
                Paragraph("ICD-10", styles["meta_label"]),
                Paragraph(codes, styles["meta_value"]),
            ]
        )
    if rows:
        tbl = Table(rows, colWidths=[3.2 * cm, 12 * cm], hAlign="LEFT")
        tbl.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )
        block.append(Spacer(1, 4))
        block.append(tbl)
    return block


def _build_section(label: str, value: Any, styles: dict[str, ParagraphStyle]) -> list[Any]:
    """Heading + rule + content as a KeepTogether-able block.

    Avoids orphaned headings at a page break: the heading + first paragraph
    are wrapped in a KeepTogether so they stay on the same page. Subsequent
    paragraphs flow naturally.
    """
    leading: list[Any] = [
        Paragraph(label, styles["heading"]),
        _section_rule(),
    ]
    remainder: list[Any] = []

    if isinstance(value, list):
        if not value:
            return []
        first_item = True
        for item in value:
            para = Paragraph(f"&bull;&nbsp; {item}", styles["bullet"])
            if first_item:
                leading.append(para)
                first_item = False
            else:
                remainder.append(para)
    else:
        paragraphs = [p.strip() for p in str(value).split("\n") if p.strip()]
        if not paragraphs:
            return []
        leading.append(Paragraph(paragraphs[0], styles["body"]))
        for para in paragraphs[1:]:
            remainder.append(Paragraph(para, styles["body"]))

    return [KeepTogether(leading), *remainder]


def _build_signature_block(report_date: str, styles: dict[str, ParagraphStyle]) -> list[Any]:
    """Date + signature line at the end of the report."""
    sig_table = Table(
        [
            [f"Datum: {report_date}", "_" * 34],
            [
                Paragraph("", styles["sig_label"]),
                Paragraph("Unterschrift Therapeut/in", styles["sig_label"]),
            ],
        ],
        colWidths=["40%", "60%"],
        hAlign="LEFT",
    )
    sig_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                ("FONTNAME", (0, 0), (0, 0), _BODY_FONT),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("TEXTCOLOR", (0, 1), (-1, 1), _META_LABEL),
                ("FONTSIZE", (0, 1), (-1, 1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return [Spacer(1, 32), sig_table]


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def generate_pdf(content: dict, created_at: datetime | None = None) -> bytes:
    """Generate a PDF from a report content dict.

    ``content`` is the JSON blob persisted in ``ReportRecord.content_json``.
    ``created_at`` is an optional report timestamp shown in the running header
    and the signature line. When not provided we fall back to ``content
    ['created_at']`` (string) or, last resort, "now".
    """
    buf = io.BytesIO()

    report_type = content.get("report_type", "befundbericht")
    type_label = REPORT_TYPE_LABELS.get(report_type, report_type)
    title = f"Logopädischer {type_label}"

    patient: dict[str, Any] = content.get("patient") or {}
    patient_label = str(patient.get("pseudonym") or "—")

    report_date = _resolve_report_date(created_at, content.get("created_at"))

    page_ctx = _PageContext(
        patient=patient_label,
        type_label=type_label,
        report_date=report_date,
    )

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=25 * mm,
        bottomMargin=25 * mm,
        title=title,
        author="Logopädie Report Agent",
        subject=type_label,
        creator="Logopädie Report Agent",
    )
    styles = _build_styles()
    story: list[Any] = []

    # ---- Title block (page 1 only) -----------------------------------------
    story.append(Paragraph(title, styles["title"]))
    story.append(
        HRFlowable(
            width="100%",
            thickness=1.2,
            color=_ACCENT,
            spaceBefore=2,
            spaceAfter=8,
        )
    )
    meta_table = _build_meta_table(patient, report_date, styles)
    if meta_table is not None:
        story.append(meta_table)
        story.append(Spacer(1, 4))
        story.append(
            HRFlowable(
                width="100%",
                thickness=0.4,
                color=_RULE_COLOR,
                spaceBefore=2,
                spaceAfter=2,
            )
        )

    # ---- Diagnose ----------------------------------------------------------
    diagnose: dict[str, Any] = content.get("diagnose") or {}
    story.extend(_build_diagnose_block(diagnose, styles))

    # ---- Content sections --------------------------------------------------
    for key, value in content.items():
        if key in SKIP_KEYS or not value:
            continue
        label = SECTION_LABELS.get(key, key.replace("_", " ").title())
        story.extend(_build_section(label, value, styles))

    # ---- Signature block ---------------------------------------------------
    story.extend(_build_signature_block(report_date, styles))

    on_page = _make_on_page_hook(page_ctx)
    doc.build(
        story,
        onFirstPage=on_page,
        onLaterPages=on_page,
        canvasmaker=NumberedCanvas,
    )
    return buf.getvalue()


def _resolve_report_date(created_at: datetime | None, raw: Any) -> str:
    """Pick the most appropriate report date for display (dd.mm.yyyy)."""
    if isinstance(created_at, datetime):
        return created_at.strftime("%d.%m.%Y")
    if isinstance(raw, datetime):
        return raw.strftime("%d.%m.%Y")
    if isinstance(raw, str) and raw:
        # Try ISO-8601 first; if that fails just show the raw string.
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).strftime("%d.%m.%Y")
        except ValueError:
            return raw
    return datetime.now(UTC).strftime("%d.%m.%Y")
