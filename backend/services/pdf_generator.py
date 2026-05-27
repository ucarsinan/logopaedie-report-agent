"""Generate professional PDF reports using reportlab."""

import io
import logging
from datetime import UTC, datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
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

_ACCENT = colors.HexColor("#1a1a2e")
_RULE_COLOR = colors.HexColor("#e0e0e0")


def _build_styles() -> dict:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "ReportTitle",
            parent=base["Title"],
            fontSize=16,
            spaceAfter=4,
            textColor=_ACCENT,
        ),
        "subtitle": ParagraphStyle(
            "ReportSubtitle",
            parent=base["Normal"],
            fontSize=10,
            textColor=colors.grey,
            spaceAfter=8,
        ),
        "heading": ParagraphStyle(
            "SectionHeading",
            parent=base["Heading2"],
            fontSize=12,
            spaceBefore=14,
            spaceAfter=6,
            textColor=_ACCENT,
        ),
        "body": ParagraphStyle(
            "BodyText",
            parent=base["Normal"],
            fontSize=10,
            leading=14,
            spaceAfter=4,
        ),
        "bullet": ParagraphStyle(
            "BulletItem",
            parent=base["Normal"],
            fontSize=10,
            leading=14,
            leftIndent=20,
            bulletIndent=10,
        ),
        "sig_label": ParagraphStyle(
            "SigLabel",
            parent=base["Normal"],
            fontSize=8,
            textColor=colors.grey,
        ),
    }


AI_DISCLAIMER = "KI-generierter Entwurf – vor Verwendung fachlich prüfen und freigeben."


def _make_footer(canvas, doc) -> None:
    """Draw the AI/draft disclaimer + page number/branding on every page."""
    canvas.saveState()
    width, _ = A4
    now = datetime.now(UTC).strftime("%d.%m.%Y")
    text = f"Erstellt am {now} | Logopädie Report Agent | Seite {doc.page}"
    canvas.setFillColor(colors.grey)
    # Disclaimer sits just above the branding line so it is visible on every page.
    canvas.setFont("Helvetica-Oblique", 8)
    canvas.drawCentredString(width / 2, 1.6 * cm, AI_DISCLAIMER)
    canvas.setFont("Helvetica", 8)
    canvas.drawCentredString(width / 2, 1.2 * cm, text)
    canvas.restoreState()


def _hr() -> HRFlowable:
    return HRFlowable(width="100%", thickness=0.5, color=_RULE_COLOR, spaceAfter=4)


def generate_pdf(content: dict) -> bytes:
    """Generate a PDF from a report content dict. Returns PDF bytes."""
    buf = io.BytesIO()

    report_type = content.get("report_type", "befundbericht")
    type_label = REPORT_TYPE_LABELS.get(report_type, report_type)
    title = f"Logopädischer {type_label}"

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2.5 * cm,
        title=title,
        author="Logopädie Report Agent",
        subject=type_label,
        creator="Logopädie Report Agent",
    )
    styles = _build_styles()
    story: list = []

    # Title block
    story.append(Paragraph(title, styles["title"]))

    patient = content.get("patient", {})
    if patient:
        info_parts = []
        if patient.get("pseudonym"):
            info_parts.append(f"Patient: {patient['pseudonym']}")
        if patient.get("age_group"):
            info_parts.append(f"Altersgruppe: {patient['age_group']}")
        if patient.get("gender"):
            info_parts.append(f"Geschlecht: {patient['gender']}")
        if info_parts:
            story.append(Paragraph(" | ".join(info_parts), styles["subtitle"]))

    story.append(_hr())

    # Diagnose
    diagnose = content.get("diagnose", {})
    if diagnose and (diagnose.get("diagnose_text") or diagnose.get("icd_10_codes")):
        story.append(Paragraph("Diagnose", styles["heading"]))
        if diagnose.get("diagnose_text"):
            story.append(Paragraph(diagnose["diagnose_text"], styles["body"]))
        if diagnose.get("indikationsschluessel"):
            story.append(
                Paragraph(
                    f"Indikationsschlüssel: {diagnose['indikationsschluessel']}",
                    styles["body"],
                )
            )
        if diagnose.get("icd_10_codes"):
            story.append(
                Paragraph(
                    f"ICD-10: {', '.join(diagnose['icd_10_codes'])}",
                    styles["body"],
                )
            )

    # Content sections
    for key, value in content.items():
        if key in SKIP_KEYS or not value:
            continue
        label = SECTION_LABELS.get(key, key.replace("_", " ").title())
        story.append(Paragraph(label, styles["heading"]))
        story.append(_hr())

        if isinstance(value, list):
            for item in value:
                story.append(Paragraph(f"• {item}", styles["bullet"]))
        else:
            for para in str(value).split("\n"):
                if para.strip():
                    story.append(Paragraph(para.strip(), styles["body"]))

    # Signature block — date left, signature line right
    story.append(Spacer(1, 40))
    now_str = datetime.now(UTC).strftime("%d.%m.%Y")
    sig_table = Table(
        [
            [f"Datum: {now_str}", "_" * 30],
            [Paragraph("", styles["sig_label"]), Paragraph("Unterschrift Therapeut/in", styles["sig_label"])],
        ],
        colWidths=["40%", "60%"],
    )
    sig_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("TEXTCOLOR", (0, 1), (-1, 1), colors.grey),
                ("FONTSIZE", (0, 1), (-1, 1), 8),
            ]
        )
    )
    story.append(sig_table)

    doc.build(story, onFirstPage=_make_footer, onLaterPages=_make_footer)
    return buf.getvalue()
