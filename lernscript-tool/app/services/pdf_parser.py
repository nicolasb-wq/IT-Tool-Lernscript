"""Extrahiert Text aus hochgeladenen Kurs-PDFs (temporär, keine Persistenz)."""
import fitz  # PyMuPDF


def extract_text(pdf_bytes: bytes) -> str:
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        return "\n\n".join(page.get_text() for page in doc)
