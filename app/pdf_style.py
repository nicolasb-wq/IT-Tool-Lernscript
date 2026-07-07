"""Zentrale Stil-Definition für Lernscript-PDFs.

Alle Farbwerte wurden programmatisch aus den Referenz-PDFs
(WBS NEINT1) via PyMuPDF gemessen — keine Schätzwerte.
"""
import os
import re
from xml.sax.saxutils import escape as _xml_escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, Table, TableStyle

# ---------------------------------------------------------------- Farben
PRIMARY_BLUE = colors.HexColor("#0071B2")
LIGHT_BLUE = colors.HexColor("#D2E8F4")
FOOTER_TEXT = colors.HexColor("#89A5C9")
BODY_DARK = colors.HexColor("#161616")
ACCENT_ORANGE = colors.HexColor("#FE5000")
SIGNAL_RED = colors.HexColor("#FF0000")

# Kapitelbanner-Palette (rotierend pro Thema)
CHAPTER_COLORS = [
    colors.HexColor("#0071B2"),  # Blau
    colors.HexColor("#92D050"),  # Grün
    colors.HexColor("#FFC000"),  # Gelb
    colors.HexColor("#FE5000"),  # Orange
    colors.HexColor("#7ACFFF"),  # Hellblau
    colors.HexColor("#868686"),  # Grau
]

BOX_STYLES = {
    "merke":    {"bg": LIGHT_BLUE,                  "border": PRIMARY_BLUE,               "label": "MERKE"},
    "beispiel": {"bg": colors.HexColor("#E8F5DC"),  "border": colors.HexColor("#92D050"), "label": "BEISPIEL"},
    "achtung":  {"bg": colors.HexColor("#FDEAE2"),  "border": ACCENT_ORANGE,              "label": "ACHTUNG"},
    "info":     {"bg": colors.HexColor("#F0F0F0"),  "border": colors.HexColor("#868686"), "label": "INFO"},
}

# ------------------------------------------------------------ Typografie
# Source Sans 3 (= Nachfolgename von "Source Sans Pro", optisch identisch),
# SIL Open Font License 1.1 — Lizenz liegt unter app/fonts/LICENSE-SourceSans.md.
_FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")

FONT = "SourceSans"
FONT_BOLD = "SourceSans-Bold"
FONT_ITALIC = "SourceSans-Italic"
FONT_BOLD_ITALIC = "SourceSans-BoldItalic"


def _register_fonts() -> None:
    """Registriert die 4 TTF-Schnitte bei ReportLab. Fällt auf Helvetica zurück,
    falls die Font-Dateien fehlen (z. B. in einer minimalen Docker-Schicht ohne
    app/fonts/) — dann bleibt das PDF trotzdem erzeugbar, nur optisch abweichend.
    """
    global FONT, FONT_BOLD, FONT_ITALIC, FONT_BOLD_ITALIC
    mapping = {
        FONT: "SourceSans3-Regular.ttf",
        FONT_BOLD: "SourceSans3-Bold.ttf",
        FONT_ITALIC: "SourceSans3-It.ttf",
        FONT_BOLD_ITALIC: "SourceSans3-BoldIt.ttf",
    }
    try:
        for name, filename in mapping.items():
            path = os.path.join(_FONT_DIR, filename)
            pdfmetrics.registerFont(TTFont(name, path))
        pdfmetrics.registerFontFamily(
            FONT, normal=FONT, bold=FONT_BOLD, italic=FONT_ITALIC, boldItalic=FONT_BOLD_ITALIC
        )
    except Exception:
        FONT = "Helvetica"
        FONT_BOLD = "Helvetica-Bold"
        FONT_ITALIC = "Helvetica-Oblique"
        FONT_BOLD_ITALIC = "Helvetica-BoldOblique"


_register_fonts()

PAGE_SIZE = A4
MARGIN = 20 * mm

STYLES = {
    "title": ParagraphStyle("title", fontName=FONT_BOLD, fontSize=26,
                            textColor=PRIMARY_BLUE, spaceAfter=10, leading=31),
    "h2": ParagraphStyle("h2", fontName=FONT_BOLD, fontSize=16,
                         textColor=PRIMARY_BLUE, spaceBefore=12, spaceAfter=6, leading=20),
    "kicker": ParagraphStyle("kicker", fontName=FONT_ITALIC, fontSize=12,
                             textColor=PRIMARY_BLUE, spaceAfter=8, leading=15),
    "body": ParagraphStyle("body", fontName=FONT, fontSize=11,
                           textColor=BODY_DARK, leading=16, spaceAfter=5),
    "bullet": ParagraphStyle("bullet", fontName=FONT, fontSize=11,
                             textColor=BODY_DARK, leading=16, leftIndent=6 * mm,
                             bulletIndent=0, bulletFontName=FONT, spaceAfter=4,
                             bulletColor=PRIMARY_BLUE),
    "box_body": ParagraphStyle("box_body", fontName=FONT, fontSize=10.5,
                               textColor=BODY_DARK, leading=15),
    "footer": ParagraphStyle("footer", fontName=FONT, fontSize=9,
                             textColor=FOOTER_TEXT),
}


_ALLOWED_TAGS = re.compile(r"&lt;(/?)(b|i|u)&gt;")


def safe_markup(text: object) -> str:
    """Escapet KI-generierten Text für ReportLab-Paragraphen, erlaubt aber
    einfache Formatierung (<b>, <i>, <u>). Ohne dieses Escaping crasht
    Paragraph() bei jedem '<' oder '&' im Inhalt — in IT-Skripten
    (z. B. 'x < y', 'AT&T') praktisch garantiert."""
    escaped = _xml_escape(str(text))
    return _ALLOWED_TAGS.sub(r"<\1\2>", escaped)


def chapter_banner(text: str, index: int, width: float) -> Table:
    """Farbcodierter Kapitelbanner, Farbe rotiert über CHAPTER_COLORS."""
    color = CHAPTER_COLORS[index % len(CHAPTER_COLORS)]
    p = Paragraph(
        f'<font color="white"><b>{safe_markup(text)}</b></font>',
        ParagraphStyle("banner", fontName=FONT_BOLD, fontSize=15, leading=19),
    )
    t = Table([[p]], colWidths=[width])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), color),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return t


def content_box(kind: str, text: str, width: float) -> Table:
    """Merke/Beispiel/Achtung/Info-Box mit farbigem Rand + Label."""
    cfg = BOX_STYLES[kind]
    label = Paragraph(
        f'<b><font color="{cfg["border"].hexval().replace("0x", "#")}">{cfg["label"]}</font></b>',
        STYLES["box_body"],
    )
    body = Paragraph(safe_markup(text), STYLES["box_body"])
    t = Table([[label], [body]], colWidths=[width])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), cfg["bg"]),
        ("LINEBEFORE", (0, 0), (0, -1), 3, cfg["border"]),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (0, 0), 6),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 8),
    ]))
    return t


def comparison_table(headers: list[str], rows: list[list[str]], width: float) -> Table:
    """Vergleichstabelle im WBS-Stil (blauer Header, Zebra)."""
    data = [[Paragraph(f"<b><font color='white'>{safe_markup(h)}</font></b>", STYLES["box_body"]) for h in headers]]
    data += [[Paragraph(safe_markup(c), STYLES["box_body"]) for c in row] for row in rows]
    t = Table(data, colWidths=[width / len(headers)] * len(headers), repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY_BLUE),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#B8CDDD")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    for i in range(1, len(data)):
        if i % 2 == 0:
            style.append(("BACKGROUND", (0, i), (-1, i), LIGHT_BLUE))
    t.setStyle(TableStyle(style))
    return t


def footer_drawer(module_label: str):
    """onPage-Callback: hellblauer Fußbalken + blaue Linie mit V-Kerbe (WBS-Stil)."""
    def draw(canvas, doc):
        w, _ = PAGE_SIZE
        bar_h = 14 * mm
        canvas.saveState()
        canvas.setFillColor(LIGHT_BLUE)
        canvas.rect(0, 0, w, bar_h, stroke=0, fill=1)
        # Blaue Linie mit V-Kerbe (Notch mittig-links wie im Original bei ~47 %)
        notch_x, notch_w, notch_d = w * 0.47, 9 * mm, 4 * mm
        canvas.setStrokeColor(PRIMARY_BLUE)
        canvas.setLineWidth(2.2)
        y = bar_h
        canvas.lines([
            (0, y, notch_x - notch_w / 2, y),
            (notch_x - notch_w / 2, y, notch_x, y - notch_d),
            (notch_x, y - notch_d, notch_x + notch_w / 2, y),
            (notch_x + notch_w / 2, y, w, y),
        ])
        canvas.setFillColor(FOOTER_TEXT)
        canvas.setFont(FONT, 9)
        canvas.drawString(15 * mm, 5 * mm, module_label)
        canvas.drawRightString(w - 15 * mm, 5 * mm, str(canvas.getPageNumber()))
        canvas.restoreState()
    return draw
