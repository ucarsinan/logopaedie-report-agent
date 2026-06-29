#!/usr/bin/env python3
"""
Generate a highly attractive, warm, and modern 10-slide PowerPoint-style
PDF presentation for the Logopädie Report Agent MVP.

Design System:
- Theme: Friendly clinical with communication accents
- Color Palette:
  * Background: Stone-Cream Slate `#fafaf9` (warm white, easy on the eyes)
  * Dark Navy: `#1e293b` (Slate-800) for banners and headings
  * Primary Text: `#1c1917` (Stone-900) - warm charcoal
  * Communication Cyan: `#0891b2` (Cyan-600) for accents and voice representation
  * Friendly Orange: `#f97316` (Orange-500) representing energy and speech warmth
  * Card Background: Pure White `#ffffff` with a Slate-200 border `#e2e8f0`
- Cards: White container boxes with a 4pt top accent stripe (alternating Cyan/Orange)
- Title Slide: Deep slate background with overlapping voice bubble circles
- Bullet lists: Custom HTML indicators (✓, ✦, !, ➔) for a premium dashboard feel
"""

import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# Colors
C_BG_WARM = colors.HexColor("#fafaf9")  # Cream warm white Stone-50
C_NAVY = colors.HexColor("#1e293b")  # Slate-800
C_CHARCOAL = colors.HexColor("#1c1917")  # Stone-900 (Primary text)
C_CYAN = colors.HexColor("#0891b2")  # Cyan-600 (Main brand accent)
C_ORANGE = colors.HexColor("#f97316")  # Orange-500 (Secondary accent)
C_BORDER = colors.HexColor("#e2e8f0")  # Slate-200
C_TEXT_MUTED = colors.HexColor("#78716c")  # Stone-500
C_CARD_BG = colors.HexColor("#ffffff")  # White


class SlideCanvas(Canvas):
    """
    Two-pass canvas that handles page count calculations and overdraws
    the footer slide counter with the resolved count.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            if self._pageNumber > 1:
                self.draw_page_number(num_pages)
            super().showPage()
        super().save()

    def draw_page_number(self, total_pages):
        self.saveState()
        width, height = self._pagesize

        # Cover the placeholder "Folie X" page number in the footer
        self.setFillColor(C_BG_WARM)
        self.rect(width - 150, 24, 110, 16, fill=True, stroke=False)

        # Paint the final resolved slide count
        self.setFont("Helvetica", 8)
        self.setFillColor(C_TEXT_MUTED)
        page_str = f"Folie {self._pageNumber} von {total_pages}"
        self.drawRightString(width - 40, 32, page_str)
        self.restoreState()


def draw_title_slide_background(canvas: Canvas, doc: SimpleDocTemplate) -> None:
    """Draws a premium warm dark slate background with overlapping voice wave circles."""
    canvas.saveState()
    width, height = doc.pagesize

    # Solid background fill (Dark Slate)
    canvas.setFillColor(colors.HexColor("#0f172a"))  # Slate-900
    canvas.rect(0, 0, width, height, fill=True, stroke=False)

    # Overlapping Voice Wave/Bubble Circles (Communication Concept)
    canvas.setFillColor(colors.HexColor("#1e293b"))  # Deep slate
    canvas.circle(width - 80, height / 2, 280, fill=True, stroke=False)

    canvas.setFillColor(colors.HexColor("#0f766e"))  # Tealish Cyan
    canvas.circle(width - 120, height / 2 + 30, 190, fill=True, stroke=False)

    canvas.setFillColor(colors.HexColor("#0891b2"))  # Brighter Cyan
    canvas.circle(width - 200, height / 2 + 100, 110, fill=True, stroke=False)

    canvas.setFillColor(colors.HexColor("#ea580c"))  # Coral Orange
    canvas.circle(width - 40, height / 2 - 130, 155, fill=True, stroke=False)

    canvas.setFillColor(colors.HexColor("#f97316"))  # Friendly Orange
    canvas.circle(width - 160, height / 2 - 60, 60, fill=True, stroke=False)

    # Bottom accent bar
    canvas.setFillColor(C_ORANGE)
    canvas.rect(0, 0, width, 12, fill=True, stroke=False)

    canvas.restoreState()


def draw_content_slide_background(canvas: Canvas, doc: SimpleDocTemplate) -> None:
    """Draws a clean warm cream background, top banners, and footers for content slides."""
    canvas.saveState()
    width, height = doc.pagesize

    # Background fill
    canvas.setFillColor(C_BG_WARM)
    canvas.rect(0, 0, width, height, fill=True, stroke=False)

    # Top Banner
    canvas.setFillColor(C_NAVY)
    canvas.rect(0, height - 12, width, 12, fill=True, stroke=False)
    canvas.setFillColor(C_CYAN)
    canvas.rect(0, height - 16, width, 4, fill=True, stroke=False)

    # Footer dividing line
    canvas.setStrokeColor(colors.HexColor("#e7e5e4"))  # Stone-200
    canvas.setLineWidth(1.0)
    canvas.line(40, 50, width - 40, 50)

    # Footer Brand
    canvas.setFont("Helvetica-Bold", 8)
    canvas.setFillColor(C_CYAN)
    canvas.drawString(40, 32, "LOGOPÄDIE REPORT AGENT")

    # Orange separation dot
    canvas.setFillColor(C_ORANGE)
    canvas.circle(162, 35, 2.5, fill=True, stroke=False)

    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(C_TEXT_MUTED)
    canvas.drawString(173, 32, "Therapie-Dokumentation neu gedacht (Juni 2026)")

    # Placeholder slide number (will be covered and updated in pass 2)
    canvas.drawRightString(width - 40, 32, f"Folie {doc.page}")

    canvas.restoreState()


def _build_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title_slide_title": ParagraphStyle(
            "TitleSlideTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=34,
            leading=42,
            textColor=colors.white,
            alignment=0,
            spaceAfter=15,
        ),
        "title_slide_subtitle": ParagraphStyle(
            "TitleSlideSubtitle",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=16,
            leading=22,
            textColor=colors.HexColor("#cffafe"),  # Very soft light cyan
            spaceAfter=120,
        ),
        "title_slide_meta": ParagraphStyle(
            "TitleSlideMeta",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10.5,
            leading=15,
            textColor=colors.HexColor("#94a3b8"),
        ),
        "breadcrumb": ParagraphStyle(
            "SlideBreadcrumb",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=C_CYAN,
            spaceAfter=4,
        ),
        "slide_title": ParagraphStyle(
            "SlideTitle",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            textColor=C_NAVY,
            spaceAfter=20,
        ),
        "card_title": ParagraphStyle(
            "CardTitle",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=C_NAVY,
            spaceAfter=8,
        ),
        "card_body": ParagraphStyle(
            "CardBody",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9.2,
            leading=13.5,
            textColor=C_CHARCOAL,
        ),
        "timeline_header": ParagraphStyle(
            "TimelineHeader",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=12,
            textColor=colors.white,
            alignment=1,
        ),
        "schema_table_header": ParagraphStyle(
            "SchemaTableHeader",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9.5,
            leading=12,
            textColor=colors.white,
        ),
        "schema_table_cell": ParagraphStyle(
            "SchemaTableCell",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=C_CHARCOAL,
        ),
    }


def make_card(
    title: str,
    bullets: list[str],
    styles: dict[str, ParagraphStyle],
    width: float,
    height: float = None,
    accent_color: colors.Color = C_CYAN,
) -> Table:
    """Helper to generate a beautiful white container card with a colored top border accent."""
    content = [Paragraph(title, styles["card_title"]), Spacer(1, 4)]
    for bullet in bullets:
        content.append(Paragraph(bullet, styles["card_body"]))
        content.append(Spacer(1, 5))
    content.pop()  # remove last spacer

    card = Table([[content]], colWidths=[width], rowHeights=height)
    card.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), C_CARD_BG),
                ("BOX", (0, 0), (-1, -1), 0.8, C_BORDER),
                ("PADDING", (0, 0), (-1, -1), 14),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                (
                    "LINEABOVE",
                    (0, 0),
                    (-1, 0),
                    4,
                    accent_color,
                ),  # 4pt top accent stripe
            ]
        )
    )
    return card


def build_presentation(output_path: str):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=landscape(A4),
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=65,
    )
    styles = _build_styles()
    story = []

    # Page width available = 841.89 - 80 = 761.89
    slide_w = 761.89

    # =========================================================================
    # SLIDE 1: Title Slide (Dark Navy)
    # =========================================================================
    story.append(Spacer(1, 90))
    story.append(Paragraph("Logopädie Report Agent", styles["title_slide_title"]))
    story.append(
        Paragraph(
            "AI-gestützte Dokumentation und Prozessbegleitung für die Logopädie-Praxis",
            styles["title_slide_subtitle"],
        )
    )

    meta_text = (
        "<b>Entwickler:</b> Sinan Ucar<br/>"
        "<b>Tech-Stack Showcase:</b> Next.js, FastAPI, SQLModel, PostgreSQL Neon, Redis & Groq AI<br/>"
        "<b>Code-Repository:</b> github.com/ucarsinan/logopaedie-report-agent"
    )
    story.append(Paragraph(meta_text, styles["title_slide_meta"]))
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 2: Die Projekt-Idee & Problemstellung
    # =========================================================================
    story.append(Paragraph("01 / EINLEITUNG & PROBLEMSTELLUNG", styles["breadcrumb"]))
    story.append(Paragraph("Die Projekt-Idee & Problemstellung", styles["slide_title"]))

    col_w = (slide_w - 20) / 2
    left_bullets = [
        "<font color='#f97316'><b>!</b></font> <b>Hoher Dokumentationsaufwand:</b> Therapeuten verbringen bis zu 30-40% ihrer Arbeitszeit mit dem Schreiben von klinischen Berichten, SOAP-Notizen und Behandlungsplänen.",
        "<font color='#f97316'><b>!</b></font> <b>Kognitive Belastung:</b> Das manuelle Mitschreiben während der Therapiestunde stört den Behandlungsfluss und beeinträchtigt die persönliche Interaktion mit dem Patienten.",
        "<font color='#f97316'><b>!</b></font> <b>Unstrukturierte Datenflut:</b> Audioaufnahmen oder handschriftliche Notizen sind schwer auszuwerten und im Praxisalltag nicht standardisiert nutzbar.",
    ]
    right_bullets = [
        "<font color='#0891b2'><b>✓</b></font> <b>Geführter Sprach-Assistent:</b> Strukturierte Anamnesegespräche per Text- oder Audio-Chat nehmen alle behandlungsrelevanten Daten flexibel auf.",
        "<font color='#0891b2'><b>✓</b></font> <b>Automatisierte Fachberichte:</b> Direkte, präzise Generierung von fachsprachlichen Berichten nach ICF-Standard (Befund-, Therapie- & Abschlussberichte).",
        "<font color='#0891b2'><b>✓</b></font> <b>Ganzheitlicher Workflow:</b> Eine integrierte Plattform zur Reduktion administrativer Lasten bei gleichzeitiger Qualitätssicherung durch KI.",
    ]

    card_left = make_card(
        "Das Problem in der Praxis",
        left_bullets,
        styles,
        col_w,
        height=270,
        accent_color=C_ORANGE,
    )
    card_right = make_card(
        "Unsere Lösung: Logopädie Report Agent",
        right_bullets,
        styles,
        col_w,
        height=270,
        accent_color=C_CYAN,
    )

    t = Table([[card_left, "", card_right]], colWidths=[col_w, 20, col_w])
    t.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(t)
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 3: Die Kern-Features des MVP
    # =========================================================================
    story.append(Paragraph("02 / FUNKTIONSUMFANG", styles["breadcrumb"]))
    story.append(Paragraph("Die Kern-Features des MVP", styles["slide_title"]))

    col_w3 = (slide_w - 40) / 3
    bullets_f1 = [
        "<font color='#0891b2'><b>✓</b></font> <b>Geführter Chatbot:</b> Führt Therapeuten strukturiert durch das Anamnesegespräch.",
        "<font color='#0891b2'><b>✓</b></font> <b>Audio-Recording:</b> Direktes Aufnehmen und automatisches Übertragen in den Anamnese-Fluss.",
    ]
    bullets_f2 = [
        "<font color='#f97316'><b>✦</b></font> <b>Dateiuploads:</b> Verarbeitung von PDF, DOCX und TXT (z. B. Arztberichte).",
        "<font color='#f97316'><b>✦</b></font> <b>Kontextinjektion:</b> Extrahiert Dokumenteninhalte und übergibt diese direkt an den AI-Prompt.",
    ]
    bullets_f3 = [
        "<font color='#0891b2'><b>✓</b></font> <b>Berichtstypen:</b> Befundbericht, Therapiebericht (kurz/lang), Abschlussbericht.",
        "<font color='#0891b2'><b>✓</b></font> <b>JSON-Erzwingung:</b> Strikte Validierung der Berichtsstruktur via Pydantic.",
    ]

    c1 = make_card(
        "1. Geführte Anamnese",
        bullets_f1,
        styles,
        col_w3,
        height=270,
        accent_color=C_CYAN,
    )
    c2 = make_card(
        "2. Material-Integration",
        bullets_f2,
        styles,
        col_w3,
        height=270,
        accent_color=C_ORANGE,
    )
    c3 = make_card(
        "3. Strukturierte Berichte",
        bullets_f3,
        styles,
        col_w3,
        height=270,
        accent_color=C_CYAN,
    )

    t = Table([[c1, "", c2, "", c3]], colWidths=[col_w3, 20, col_w3, 20, col_w3])
    t.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(t)
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 4: Weitere Fach-Module & Workflows
    # =========================================================================
    story.append(Paragraph("03 / ERWEITERTE FUNKTIONEN", styles["breadcrumb"]))
    story.append(Paragraph("Zusätzliche klinische Module", styles["slide_title"]))

    bullets_f4 = [
        "<font color='#0891b2'><b>✓</b></font> <b>SOAP-Notizen:</b> Generierung strukturierter Therapiedokumentationen (Subjective, Objective, Assessment, Plan) aus Sitzungsmitschriften.",
        "<font color='#0891b2'><b>✓</b></font> <b>Therapieplan-Generator:</b> Automatische Ableitung maßgeschneiderter Übungspläne, Frequenzen und klinischer Ziele direkt aus dem erstellten Bericht.",
    ]
    bullets_f5 = [
        "<font color='#f97316'><b>✦</b></font> <b>Phonologische Ausspracheanalyse:</b> Spezialisierte Analyse kindlicher Aussprachestörungen anhand von Wortpaaren oder transkribiertem Audio.",
        "<font color='#f97316'><b>✦</b></font> <b>Berichtsvergleich & Vorschläge:</b> Vergleich zweier Berichtszeitpunkte zur Dokumentation von Fortschritten sowie KI-Textbausteine (Suggestions).",
    ]

    c4 = make_card(
        "Dokumentation & Therapieplanung",
        bullets_f4,
        styles,
        col_w,
        height=270,
        accent_color=C_CYAN,
    )
    c5 = make_card(
        "Diagnostik-Erweiterungen & Analyse",
        bullets_f5,
        styles,
        col_w,
        height=270,
        accent_color=C_ORANGE,
    )

    t = Table([[c4, "", c5]], colWidths=[col_w, 20, col_w])
    t.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(t)
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 5: Systemarchitektur & Datenfluss
    # =========================================================================
    story.append(Paragraph("04 / SYSTEMARCHITEKTUR", styles["breadcrumb"]))
    story.append(Paragraph("Architektur & Monorepo-Datenfluss", styles["slide_title"]))

    bullets_arch1 = [
        "<font color='#0891b2'><b>➔</b></font> <b>Next.js 16 (App Router):</b> React 19 Komponenten mit Tailwind CSS v4 für responsive, moderne UIs.",
        "<font color='#0891b2'><b>➔</b></font> <b>BFF (Backend-for-Frontend):</b> Next Route Handlers managen Sessions und leiten APIs weiter. Verhindert direkte Browser-Backend-Kopplung.",
    ]
    bullets_arch2 = [
        "<font color='#f97316'><b>➔</b></font> <b>FastAPI (Python 3.12):</b> Asynchroner REST-Server für performante KI-Operationen.",
        "<font color='#f97316'><b>➔</b></font> <b>SQLModel ORM:</b> Pydantic v2 Typensicherheit für SQLite (lokaler Fallback) und PostgreSQL.",
    ]
    bullets_arch3 = [
        "<font color='#0891b2'><b>➔</b></font> <b>Neon PostgreSQL:</b> Cloud-Datenbank für persistente Nutzer-, Patienten- und Berichtsdaten.",
        "<font color='#0891b2'><b>➔</b></font> <b>Upstash Redis:</b> Fernet-verschlüsselter In-Memory Cache für transiente 24h-Sessions und Rate-Limiting.",
    ]

    c_arch1 = make_card(
        "Client-Layer (Frontend & BFF)",
        bullets_arch1,
        styles,
        col_w3,
        height=270,
        accent_color=C_CYAN,
    )
    c_arch2 = make_card(
        "API-Service (Backend)",
        bullets_arch2,
        styles,
        col_w3,
        height=270,
        accent_color=C_ORANGE,
    )
    c_arch3 = make_card(
        "Daten & Speicher (Persistence)",
        bullets_arch3,
        styles,
        col_w3,
        height=270,
        accent_color=C_CYAN,
    )

    t = Table(
        [[c_arch1, "", c_arch2, "", c_arch3]],
        colWidths=[col_w3, 20, col_w3, 20, col_w3],
    )
    t.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(t)
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 6: Die KI-Pipeline & Prompt-Engineering
    # =========================================================================
    story.append(Paragraph("05 / AI ENGINE", styles["breadcrumb"]))
    story.append(Paragraph("KI-Pipeline & Prompt-Engineering", styles["slide_title"]))

    bullets_ai1 = [
        "<font color='#0891b2'><b>✓</b></font> <b>Groq API Integration:</b> Nutzung dedizierter LPU-Inferenz für extrem geringe Generierungslatenz.",
        "<font color='#0891b2'><b>✓</b></font> <b>Whisper large-v3:</b> Transkribiert Demo-Audio und synthetische Beispielsitzungen in wenigen Sekunden.",
        "<font color='#0891b2'><b>✓</b></font> <b>Llama-3.3-70b-versatile:</b> NLP-Zentralhirn zur Strukturierung und Textgenerierung.",
        "<font color='#0891b2'><b>✓</b></font> <b>API Fallback-Rotation:</b> Automatischer Failover zwischen Modellen bei Ausfällen oder Limits.",
    ]
    bullets_ai2 = [
        "<font color='#f97316'><b>✦</b></font> <b>Medizinisches System-Prompting:</b> Eingebettete Fachregeln nach ICF, ICD-10 Codierung, SGB V sowie Pflicht zur Pseudonymisierung.",
        "<font color='#f97316'><b>✦</b></font> <b>Strikter JSON Mode:</b> API-Antworten werden via JSON-Schema erzwungen und durch Pydantic validiert (kein unstrukturierter Text).",
        "<font color='#f97316'><b>✦</b></font> <b>Material-Merging:</b> Textinhalte hochgeladener Dokumente werden dynamisch in den LLM-Context gepackt.",
    ]

    c_ai1 = make_card(
        "KI-Modelle & Inferenz",
        bullets_ai1,
        styles,
        col_w,
        height=270,
        accent_color=C_CYAN,
    )
    c_ai2 = make_card(
        "Steuerung & Prompt-Strategie",
        bullets_ai2,
        styles,
        col_w,
        height=270,
        accent_color=C_ORANGE,
    )

    t = Table([[c_ai1, "", c_ai2]], colWidths=[col_w, 20, col_w])
    t.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(t)
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 7: Datenmodell & Anwendungs-Sicherheit
    # =========================================================================
    story.append(Paragraph("06 / ANWENDUNGSSICHERHEIT", styles["breadcrumb"]))
    story.append(Paragraph("Sicherheitsarchitektur des MVP", styles["slide_title"]))

    col_w4 = (slide_w - 60) / 4
    bullets_sec1 = [
        "<font color='#0891b2'><b>✓</b></font> JWT Access/Refresh.",
        "<font color='#0891b2'><b>✓</b></font> httpOnly-Cookies.",
        "<font color='#0891b2'><b>✓</b></font> Hashing mit Argon2id.",
    ]
    bullets_sec2 = [
        "<font color='#f97316'><b>✦</b></font> 2FA via TOTP-QR-Codes.",
        "<font color='#f97316'><b>✦</b></font> Email-Verifikation.",
        "<font color='#f97316'><b>✦</b></font> Sichere Password-Resets.",
    ]
    bullets_sec3 = [
        "<font color='#0891b2'><b>✓</b></font> slowapi Rate-Limits.",
        "<font color='#0891b2'><b>✓</b></font> IP-Blocklist-Erkennung.",
        "<font color='#0891b2'><b>✓</b></font> Fernet-Verschlüsselung.",
    ]
    bullets_sec4 = [
        "<font color='#f97316'><b>✦</b></font> Audit-Trail aller Logins.",
        "<font color='#f97316'><b>✦</b></font> Async BackgroundLogs.",
    ]

    c_sec1 = make_card(
        "Authentifizierung",
        bullets_sec1,
        styles,
        col_w4,
        height=270,
        accent_color=C_CYAN,
    )
    c_sec2 = make_card(
        "Multi-Faktor-Auth",
        bullets_sec2,
        styles,
        col_w4,
        height=270,
        accent_color=C_ORANGE,
    )
    c_sec3 = make_card(
        "API-Schutz & Crypt",
        bullets_sec3,
        styles,
        col_w4,
        height=270,
        accent_color=C_CYAN,
    )
    c_sec4 = make_card(
        "Audit-Logging", bullets_sec4, styles, col_w4, height=270, accent_color=C_ORANGE
    )

    t = Table(
        [[c_sec1, "", c_sec2, "", c_sec3, "", c_sec4]],
        colWidths=[col_w4, 20, col_w4, 20, col_w4, 20, col_w4],
    )
    t.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(t)
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 8: Datenbank-Schema (Datenmodell)
    # =========================================================================
    story.append(Paragraph("07 / DATENMODELL", styles["breadcrumb"]))
    story.append(Paragraph("Datenbank-Schema & Relationen", styles["slide_title"]))

    # Let's show a beautiful structured table with definitions
    schema_data = [
        [
            Paragraph("Benutzer & Sitzungen", styles["schema_table_header"]),
            Paragraph("System-Auditing", styles["schema_table_header"]),
            Paragraph("Klinische Berichte & Pläne", styles["schema_table_header"]),
        ],
        [
            # Col 1: Users
            Paragraph(
                "<b>users</b><br/>"
                "• <i>id (UUID, PK)</i><br/>"
                "• email (Varchar, UK)<br/>"
                "• password_hash (Text)<br/>"
                "• role (Varchar)<br/>"
                "• totp_enabled (Bool)<br/>"
                "• locked_until (DateTime)<br/>"
                "<br/>"
                "<b>user_sessions</b><br/>"
                "• <i>id (UUID, PK)</i><br/>"
                "• user_id (UUID, FK)<br/>"
                "• refresh_token_hash (Text)<br/>"
                "• expires_at / revoked_at<br/>"
                "<br/>"
                "<b>email_tokens</b><br/>"
                "• <i>id (UUID, PK)</i><br/>"
                "• user_id (UUID, FK)<br/>"
                "• purpose / expires_at",
                styles["schema_table_cell"],
            ),
            # Col 2: Auditing
            Paragraph(
                "<b>audit_log</b><br/>"
                "• <i>id (UUID, PK)</i><br/>"
                "• user_id (UUID, FK)<br/>"
                "• event (Varchar)<br/>"
                "• ip_address (Varchar)<br/>"
                "• user_agent (Text)<br/>"
                "• metadata_json (JSON)<br/>"
                "• created_at (DateTime)<br/>"
                "<br/>"
                "<font color='#0891b2'><b>Sicherheits-Audit trail:</b></font><br/>"
                "Ermöglicht nachvollziehbare Demo-Events für Datenexporte und Authentifizierungsvorgänge; echte Compliance-Freigabe bleibt ein separater Roadmap-Schritt.",
                styles["schema_table_cell"],
            ),
            # Col 3: Reports & Plans
            Paragraph(
                "<b>reports</b><br/>"
                "• <i>id (Int, PK)</i><br/>"
                "• user_id (UUID, FK)<br/>"
                "• pseudonym (Varchar)<br/>"
                "• report_type (Varchar)<br/>"
                "• content_json (JSON)<br/>"
                "• created_at (DateTime)<br/>"
                "<br/>"
                "<b>therapyplanrecord</b><br/>"
                "• <i>id (Int, PK)</i><br/>"
                "• report_id (Int, FK)<br/>"
                "• patient_pseudonym (Varchar)<br/>"
                "• plan_data (Text)<br/>"
                "<br/>"
                "<b>soaprecord</b><br/>"
                "• <i>id (Int, PK)</i><br/>"
                "• report_id (Int, FK)<br/>"
                "• subjective / objective / assessment / plan (Text)",
                styles["schema_table_cell"],
            ),
        ],
    ]

    schema_table = Table(schema_data, colWidths=[240, 240, 240], rowHeights=[24, 230])
    schema_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), C_NAVY),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 1, C_BORDER),
                ("PADDING", (0, 0), (-1, -1), 10),
                ("BACKGROUND", (0, 1), (-1, -1), C_CARD_BG),
                ("LINEABOVE", (0, 0), (-1, 0), 4, C_CYAN),  # Colored top bar
            ]
        )
    )
    story.append(schema_table)
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 9: Projekt-Timeline & Meilensteine
    # =========================================================================
    story.append(Paragraph("08 / IMPLEMENTATION PROCESS", styles["breadcrumb"]))
    story.append(Paragraph("Projekt-Timeline (8-Wochen-Plan)", styles["slide_title"]))

    timeline_w = (slide_w - 60) / 4
    timeline_data = [
        [
            Paragraph("Woche 1-3: Fundament", styles["timeline_header"]),
            Paragraph("Woche 4-5: KI & Logik", styles["timeline_header"]),
            Paragraph("Woche 6-7: Frontend & BFF", styles["timeline_header"]),
            Paragraph("Woche 8: Release", styles["timeline_header"]),
        ],
        [
            # W1-3
            Paragraph(
                "• Projektidee & Git-Setup<br/>"
                "• Datenbank-Schema (SQLModel)<br/>"
                "• Initial FastAPI-Architektur<br/>"
                "• CRUD-Endpunkte für Berichte, SOAP & Patienten",
                styles["schema_table_cell"],
            ),
            # W4-5
            Paragraph(
                "• Integration Groq-Whisper (STT)<br/>"
                "• Prompts für Llama-3.3-70b<br/>"
                "• Erzwingung JSON-Ausgabe<br/>"
                "• JWT-Auth & TOTP-2FA Flow<br/>"
                "• Asynchrones Audit-Logging",
                styles["schema_table_cell"],
            ),
            # W6-7
            Paragraph(
                "• Next.js 16 Interface<br/>"
                "• BFF Proxy-Layer (Route Handlers)<br/>"
                "• Implementierung aller 7 Module<br/>"
                "• PDF-Export via ReportLab<br/>"
                "• Styling mit Tailwind CSS v4",
                styles["schema_table_cell"],
            ),
            # W8
            Paragraph(
                "• Pre-Commit Hooks & Linting<br/>"
                "• 530+ Backend Pytests<br/>"
                "• 32 Playwright E2E-Tests<br/>"
                "• Deployment auf Vercel live<br/>"
                "• Erstellung MVP-Slides",
                styles["schema_table_cell"],
            ),
        ],
    ]

    timeline_table = Table(
        timeline_data,
        colWidths=[timeline_w, timeline_w, timeline_w, timeline_w],
        rowHeights=[24, 230],
    )
    timeline_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 0), C_CYAN),  # Alternating timeline colors
                ("BACKGROUND", (1, 0), (1, 0), C_ORANGE),
                ("BACKGROUND", (2, 0), (2, 0), C_CYAN),
                ("BACKGROUND", (3, 0), (3, 0), C_ORANGE),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 1, C_BORDER),
                ("PADDING", (0, 0), (-1, -1), 12),
                ("BACKGROUND", (0, 1), (-1, -1), C_CARD_BG),
            ]
        )
    )
    story.append(timeline_table)
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 10: Fazit & Ausblick
    # =========================================================================
    story.append(Paragraph("09 / RESÜMEE & AUSBLICK", styles["breadcrumb"]))
    story.append(Paragraph("Fazit & Roadmap zur Produktreife", styles["slide_title"]))

    concl_left = [
        "<font color='#0891b2'><b>✓</b></font> <b>Stabiles Monorepo-Fundament:</b> Keine starre Konzeptstudie, sondern ein lauffähiges System mit sauber getrennter Client/Server-Architektur.",
        "<font color='#0891b2'><b>✓</b></font> <b>Umfangreiche Testabdeckung:</b> Über 530 API- und Service-Tests sowie 32 automatisierte Playwright E2E-Tests senken das Regressionsrisiko deutlich.",
        "<font color='#0891b2'><b>✓</b></font> <b>Lauffähiges MVP-Deployment:</b> Als Portfolio-Demo auf Vercel erreichbar, inklusive asynchroner PDF-Generierung.",
    ]
    concl_right = [
        "<font color='#f97316'><b>➔</b></font> <b>Produktive Praxis-Compliance (Roadmap):</b> Das MVP nutzt Groq nur für synthetische Demo-Daten; echter Praxiseinsatz erfordert eine separate Provider-/Compliance-Architektur (lokal oder EU-Provider), rechtliche Prüfung sowie AVV/DPA/ZDR nach Bedarf.",
        "<font color='#f97316'><b>➔</b></font> <b>RAG / Vektor-Datenbank:</b> Einbindung einer intelligenten Suche über historische Patientenakten und Lehrmaterialien.",
        "<font color='#f97316'><b>➔</b></font> <b>Diktiergeräte-Kopplung:</b> Direkte Schnittstellen zu Hardware-Diktiergeräten für schnelles Audio-Merging.",
    ]

    card_concl_left = make_card(
        "Erreichte MVP-Ziele",
        concl_left,
        styles,
        col_w,
        height=270,
        accent_color=C_CYAN,
    )
    card_concl_right = make_card(
        "Nächste Schritte zur Produktreife",
        concl_right,
        styles,
        col_w,
        height=270,
        accent_color=C_ORANGE,
    )

    t = Table([[card_concl_left, "", card_concl_right]], colWidths=[col_w, 20, col_w])
    t.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(t)

    # Build the document
    doc.build(
        story,
        onFirstPage=draw_title_slide_background,
        onLaterPages=draw_content_slide_background,
        canvasmaker=SlideCanvas,
    )
    print(f"Presentation successfully generated at {output_path}")


if __name__ == "__main__":
    out_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target = os.path.join(out_dir, "docs", "mvp-presentation.pdf")
    build_presentation(target)
