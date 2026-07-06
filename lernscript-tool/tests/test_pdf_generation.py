"""Tests: Stil-Konstanten und PDF-Erzeugung."""
from app import pdf_style as st
from app.services.pdf_generator import build_pdf

SAMPLE = {
    "titel": "Testmodul", "modul": "NEINT1", "untertitel": "Untertitel",
    "kapitel": [{
        "titel": "Kapitel 1",
        "bloecke": [
            {"typ": "text", "text": "Ein Absatz."},
            {"typ": "bullets", "items": ["Punkt A", "Punkt B"]},
            {"typ": "merke", "text": "Wichtig!"},
            {"typ": "beispiel", "text": "192.168.1.0/24 hat 254 nutzbare Hosts."},
            {"typ": "achtung", "text": "Netz- und Broadcast-Adresse nicht vergeben."},
            {"typ": "tabelle", "headers": ["A", "B"], "rows": [["1", "2"], ["3", "4"]]},
        ],
    }],
}


def test_colors_match_reference():
    assert st.PRIMARY_BLUE.hexval() == "0x0071b2"
    assert st.LIGHT_BLUE.hexval() == "0xd2e8f4"
    assert st.ACCENT_ORANGE.hexval() == "0xfe5000"


def test_build_pdf_returns_valid_pdf():
    out = build_pdf(SAMPLE)
    assert out.startswith(b"%PDF")
    assert len(out) > 2000


def test_all_box_types_render():
    for kind in st.BOX_STYLES:
        s = {"titel": "T", "modul": "M", "kapitel": [{"titel": "K", "bloecke": [{"typ": kind, "text": "x"}]}]}
        assert build_pdf(s).startswith(b"%PDF")
