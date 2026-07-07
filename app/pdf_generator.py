"""Extrahiert Text aus hochgeladenen Kurs-PDFs (temporär, keine Persistenz).

Edge-Cases, die hier explizit behandelt werden:
- Datei ist gar kein PDF (Magic-Bytes-Prüfung statt Vertrauen in den
  Browser-Content-Type, der fälschbar ist)
- Beschädigte/nicht lesbare PDFs
- Passwortgeschützte PDFs
- Gescannte PDFs ohne Textebene -> OCR-Fallback (Tesseract, deutsch)
- Leere PDFs / kein extrahierbarer Inhalt
"""
import io
import os

import fitz  # PyMuPDF


class ParserError(ValueError):
    """Fachlicher Parser-Fehler mit nutzertauglicher Meldung."""


# Heuristik: unter diesem Durchschnitt (Zeichen pro Seite) gilt ein PDF als
# Scan ohne brauchbare Textebene und wandert in den OCR-Pfad.
_MIN_CHARS_PER_PAGE = 50


def _max_ocr_pages() -> int:
    return int(os.getenv("MAX_OCR_PAGES", "60"))


def _ocr_document(doc: "fitz.Document") -> str:
    """Rastert jede Seite (200 dpi, Graustufen) und OCRt sie mit Tesseract (deu)."""
    try:
        import pytesseract
        from PIL import Image
    except ImportError as e:  # pragma: no cover — in requirements enthalten
        raise ParserError(
            "Dieses PDF ist ein Scan ohne Textebene, aber die OCR-Komponenten "
            "sind auf dem Server nicht installiert."
        ) from e

    if len(doc) > _max_ocr_pages():
        raise ParserError(
            f"Dieses PDF ist ein Scan mit {len(doc)} Seiten — OCR ist auf "
            f"{_max_ocr_pages()} Seiten begrenzt. Bitte das PDF aufteilen."
        )

    parts = []
    for page in doc:
        pix = page.get_pixmap(dpi=200, colorspace=fitz.csGRAY)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        try:
            parts.append(pytesseract.image_to_string(img, lang="deu"))
        except pytesseract.TesseractNotFoundError as e:
            raise ParserError(
                "Dieses PDF ist ein Scan ohne Textebene, aber Tesseract-OCR "
                "ist auf dem Server nicht installiert."
            ) from e
    return "\n\n".join(parts)


def extract_text(pdf_bytes: bytes) -> str:
    # 1) Magic Bytes: laut PDF-Spezifikation darf der Header innerhalb der
    #    ersten 1024 Bytes liegen — Browser-Content-Type allein ist fälschbar.
    if b"%PDF-" not in pdf_bytes[:1024]:
        raise ParserError("Die Datei ist kein gültiges PDF (fehlende PDF-Signatur).")

    # 2) Beschädigte Dateien
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as e:
        raise ParserError("Das PDF ist beschädigt oder konnte nicht gelesen werden.") from e

    with doc:
        # 3) Passwortschutz
        if doc.needs_pass:
            raise ParserError(
                "Das PDF ist passwortgeschützt. Bitte den Schutz entfernen "
                "und erneut hochladen."
            )
        if len(doc) == 0:
            raise ParserError("Das PDF enthält keine Seiten.")

        # 4) Normale Textextraktion
        text = "\n\n".join(page.get_text() for page in doc).strip()

        # 5) Scan-Erkennung -> OCR-Fallback
        if len(text) < _MIN_CHARS_PER_PAGE * len(doc):
            ocr_text = _ocr_document(doc).strip()
            if len(ocr_text) > len(text):
                text = ocr_text

    # 6) Auch nach OCR nichts Brauchbares
    if not text:
        raise ParserError(
            "Aus dem PDF konnte kein Text extrahiert werden — es scheint leer "
            "oder ausschließlich grafisch ohne erkennbaren Text zu sein."
        )
    return text
