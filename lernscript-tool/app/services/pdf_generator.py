"""Baut aus strukturiertem Skript-JSON (von Claude) das fertige Lernscript-PDF."""
from io import BytesIO

from reportlab.lib.units import mm
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer

from app import pdf_style as st

CONTENT_WIDTH = st.PAGE_SIZE[0] - 2 * st.MARGIN


def build_pdf(script: dict) -> bytes:
    """script-Schema:
    {
      "titel": str, "modul": str, "untertitel": str,
      "kapitel": [{
        "titel": str,
        "bloecke": [{"typ": "text"|"bullets"|"merke"|"beispiel"|"achtung"|"info"|"tabelle"|"h2", ...}]
      }]
    }
    """
    buf = BytesIO()
    doc = BaseDocTemplate(buf, pagesize=st.PAGE_SIZE,
                          leftMargin=st.MARGIN, rightMargin=st.MARGIN,
                          topMargin=st.MARGIN, bottomMargin=st.MARGIN + 10 * mm)
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    doc.addPageTemplates([PageTemplate(id="all", frames=[frame],
                                       onPage=st.footer_drawer(script.get("modul", "")))])

    flow = [
        Paragraph(script["titel"], st.STYLES["title"]),
        Paragraph(script.get("untertitel", ""), st.STYLES["kicker"]),
        Spacer(1, 6 * mm),
    ]

    for i, kap in enumerate(script.get("kapitel", [])):
        flow.append(st.chapter_banner(kap["titel"], i, CONTENT_WIDTH))
        flow.append(Spacer(1, 4 * mm))
        for b in kap.get("bloecke", []):
            typ = b.get("typ")
            if typ == "h2":
                flow.append(Paragraph(b["text"], st.STYLES["h2"]))
            elif typ == "text":
                flow.append(Paragraph(b["text"], st.STYLES["body"]))
            elif typ == "bullets":
                for item in b["items"]:
                    flow.append(Paragraph(item, st.STYLES["bullet"], bulletText="•"))
            elif typ in st.BOX_STYLES:
                flow.append(Spacer(1, 2 * mm))
                flow.append(st.content_box(typ, b["text"], CONTENT_WIDTH))
                flow.append(Spacer(1, 3 * mm))
            elif typ == "tabelle":
                flow.append(Spacer(1, 2 * mm))
                flow.append(st.comparison_table(b["headers"], b["rows"], CONTENT_WIDTH))
                flow.append(Spacer(1, 3 * mm))
        flow.append(Spacer(1, 6 * mm))

    doc.build(flow)
    return buf.getvalue()
