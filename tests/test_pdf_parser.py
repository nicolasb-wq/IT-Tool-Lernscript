"""Edge-Case-Tests für den PDF-Parser — mit echten, on-the-fly erzeugten PDFs."""
import fitz
import pytest

from app.services.pdf_parser import ParserError, extract_text


def _text_pdf(text: str = "Netzwerktechnik Grundlagen. " * 30) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text, fontsize=11)
    return doc.tobytes()


def _scanned_pdf(text: str = "Subnetzmaske und CIDR Notation") -> bytes:
    """Simuliert einen Scan: Text wird gerastert und NUR als Bild eingebettet."""
    src = fitz.open()
    page = src.new_page()
    page.insert_text((72, 120), text, fontsize=24)
    pix = page.get_pixmap(dpi=200)
    scan = fitz.open()
    p2 = scan.new_page()
    p2.insert_image(p2.rect, pixmap=pix)
    return scan.tobytes()


def test_normal_text_pdf():
    text = extract_text(_text_pdf())
    assert "Netzwerktechnik" in text


def test_non_pdf_bytes_rejected():
    with pytest.raises(ParserError, match="kein gültiges PDF"):
        extract_text(b"Dies ist eine als PDF getarnte Textdatei " * 50)


def test_docx_magic_bytes_rejected():
    # .docx beginnt wie jedes ZIP mit PK\x03\x04
    with pytest.raises(ParserError, match="kein gültiges PDF"):
        extract_text(b"PK\x03\x04" + b"\x00" * 500)


def test_corrupted_pdf_rejected():
    broken = _text_pdf()[:200]  # Header ok, Rest fehlt
    with pytest.raises(ParserError, match="beschädigt"):
        extract_text(broken)


def test_password_protected_pdf_rejected():
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "geheim")
    encrypted = doc.tobytes(
        encryption=fitz.PDF_ENCRYPT_AES_256, user_pw="pw123", owner_pw="pw123"
    )
    with pytest.raises(ParserError, match="passwortgeschützt"):
        extract_text(encrypted)


def test_empty_pdf_rejected():
    doc = fitz.open()
    doc.new_page()  # eine Seite, aber ohne jeden Inhalt
    with pytest.raises(ParserError, match="kein Text extrahiert"):
        extract_text(doc.tobytes())


def test_scanned_pdf_goes_through_ocr():
    """Kernfall der OCR-Entscheidung: Bild-PDF liefert per Tesseract echten Text."""
    text = extract_text(_scanned_pdf())
    assert "Subnetzmaske" in text


def test_ocr_page_cap_enforced(monkeypatch):
    monkeypatch.setenv("MAX_OCR_PAGES", "1")
    src = fitz.open()
    p = src.new_page()
    p.insert_text((72, 120), "Seite", fontsize=24)
    pix = p.get_pixmap(dpi=100)
    scan = fitz.open()
    for _ in range(2):  # 2 Bild-Seiten > Limit 1
        pg = scan.new_page()
        pg.insert_image(pg.rect, pixmap=pix)
    with pytest.raises(ParserError, match="OCR ist auf 1 Seiten begrenzt"):
        extract_text(scan.tobytes())
