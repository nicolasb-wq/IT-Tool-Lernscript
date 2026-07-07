"""Review-Fix-Tests: KI-Text mit Sonderzeichen darf die PDF-Erzeugung nicht crashen."""
from app.pdf_style import safe_markup
from app.services.pdf_generator import build_pdf


def test_safe_markup_escapes_but_keeps_formatting():
    assert safe_markup("x < y & z") == "x &lt; y &amp; z"
    assert safe_markup("<b>fett</b> und <i>kursiv</i>") == "<b>fett</b> und <i>kursiv</i>"
    assert safe_markup("<script>alert(1)</script>") == "&lt;script&gt;alert(1)&lt;/script&gt;"


def test_pdf_survives_hostile_content():
    """Vor dem Fix crashte das an jedem '<' — in IT-Inhalten allgegenwärtig."""
    script = {
        "titel": "Vergleich: a < b & b > c",
        "modul": "M", "untertitel": "<i>kursiv erlaubt</i>",
        "kapitel": [{
            "titel": "Operatoren <, >, &",
            "bloecke": [
                {"typ": "text", "text": "Wenn x < 10 && y > 5, dann ..."},
                {"typ": "bullets", "items": ["<b>fett</b> bleibt fett", "5 < 7"]},
                {"typ": "merke", "text": "AT&T nutzt < und >"},
                {"typ": "tabelle", "headers": ["Op <", "Op >"], "rows": [["a<b", "c>d"]]},
            ],
        }],
    }
    out = build_pdf(script)
    assert out.startswith(b"%PDF")
