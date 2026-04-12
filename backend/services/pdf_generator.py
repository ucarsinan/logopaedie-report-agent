"""Generate professional PDF reports using reportlab."""

import io
import json
import logging
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
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
    "report_type", "patient", "diagnose", "_db_id", "created_at", "id", "pseudonym",
}


def _build_styles() -> dict:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "ReportTitle", parent=base["Title"], fontSize=16, spaceAfter=6,
        ),
        "subtitle": ParagraphStyle(
            "ReportSubtitle", parent=base["Normal"], fontSize=10,
            textColor=colors.grey, spaceAfter=12,
        ),
        "heading": ParagraphStyle(
            "SectionHeading", parent=base["Heading2"], fontSize=12,
            spaceBefore=14, spaceAfter=6, textColor=colors.HexColor("#1a1a2e"),
        ),
        "body": ParagraphStyle(
            "BodyText", parent=base["Normal"], fontSize=10,
            leading=14, spaceAfter=4,
        ),
        "bullet": ParagraphStyle(
            "BulletItem", parent=base["Normal"], fontSize=10,
            leading=14, leftIndent=20, bulletIndent=10,
        ),
        "footer": ParagraphStyle(
            "Footer", parent=base["Normal"], fontSize=8,
            textColor=colors.grey, alignment=1,
        ),
    }


def generate_pdf(content: dict) -> bytes:
    """Generate a PDF from a report content dict. Returns PDF bytes."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2.5 * cm,
    )
    styles = _build_styles()
    story: list = []

    report_type = content.get("report_type", "befundbericht")
    type_label = REPORT_TYPE_LABELS.get(report_type, report_type)

    # Title
    story.append(Paragraph(f"Logopädischer {type_label}", styles["title"]))

    # Patient info
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

    # Diagnose
    diagnose = content.get("diagnose", {})
    if diagnose and (diagnose.get("diagnose_text") or diagnose.get("icd_10_codes")):
        story.append(Paragraph("Diagnose", styles["heading"]))
        if diagnose.get("diagnose_text"):
            story.append(Paragraph(diagnose["diagnose_text"], styles["body"]))
        if diagnose.get("indikationsschluessel"):
            story.append(Paragraph(
                f"Indikationsschlüssel: {diagnose['indikationsschluessel']}",
                styles["body"],
            ))
        if diagnose.get("icd_10_codes"):
            story.append(Paragraph(
                f"ICD-10: {', '.join(diagnose['icd_10_codes'])}",
                styles["body"],
            ))

    # Content sections
    for key, value in content.items():
        if key in SKIP_KEYS or not value:
            continue
        label = SECTION_LABELS.get(key, key.replace("_", " ").title())
        story.append(Paragraph(label, styles["heading"]))

        if isinstance(value, list):
            for item in value:
                story.append(Paragraph(f"• {item}", styles["bullet"]))
        else:
            for para in str(value).split("\n"):
                if para.strip():
                    story.append(Paragraph(para.strip(), styles["body"]))

    # Signature area
    story.append(Spacer(1, 40))
    story.append(Paragraph("_" * 40, styles["body"]))
    story.append(Paragraph("Unterschrift Therapeut/in", styles["subtitle"]))

    # Footer with date
    story.append(Spacer(1, 20))
    now = datetime.now(timezone.utc).strftime("%d.%m.%Y")
    story.append(Paragraph(
        f"Erstellt am {now} | Generiert mit Logopädie Report Agent",
        styles["footer"],
    ))

    doc.build(story)
    return buf.getvalue()
