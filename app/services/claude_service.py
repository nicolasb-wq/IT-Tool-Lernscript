"""Anbindung an die Anthropic API: Kurs-PDF-Text -> strukturiertes Lernscript-JSON.

Große Module (> MAX_INPUT_CHARS) werden an Absatzgrenzen in Teile zerlegt und
kapitelweise in mehreren API-Calls verarbeitet — kein stiller Datenverlust
mehr durch hartes Abschneiden. Ein Skript zählt weiterhin als EIN Verbrauch
des Freikontingents, unabhängig von der Zahl interner API-Calls.
"""
import json
import os

import anthropic

SYSTEM_PROMPT = """Du bist ein Lernscript-Autor für IT-Ausbildungsinhalte (Fachinformatiker).
Du erhältst den extrahierten Text eines Kursmodul-PDFs und erstellst daraus ein
beginnerfreundliches Lernscript als reines JSON (kein Markdown, keine Backticks):

{
  "titel": "...", "modul": "z.B. NEINT1", "untertitel": "...",
  "kapitel": [
    {"titel": "...", "bloecke": [
      {"typ": "text", "text": "..."},
      {"typ": "h2", "text": "..."},
      {"typ": "bullets", "items": ["...", "..."]},
      {"typ": "merke", "text": "..."},
      {"typ": "beispiel", "text": "..."},
      {"typ": "achtung", "text": "..."},
      {"typ": "info", "text": "..."},
      {"typ": "tabelle", "headers": ["..."], "rows": [["..."]]}
    ]}
  ]
}

Regeln:
- Beginnerfreundliche Sprache, Fachbegriffe beim ersten Auftreten kurz erklären.
- Pro Kapitel mind. eine Merke-Box; Beispiele wo sinnvoll; Achtung bei typischen Fehlern.
- Vergleiche (z.B. TCP/IP vs. OSI) als Tabelle.
- Rechnungen aus der Quelle (Subnetting etc.) selbst nachrechnen und korrigieren,
  falls die Quelle Fehler enthält — dann Info-Box mit Hinweis.
- Antworte ausschließlich mit dem JSON-Objekt."""

_PART_NOTE = (
    "\n\nHinweis: Dies ist TEIL {i} von {n} eines längeren Moduls. Erstelle "
    "ausschließlich Kapitel für den vorliegenden Teil. Keine Gesamt-Einleitung "
    "oder -Zusammenfassung (außer in Teil 1 bzw. Teil {n})."
)


def _model() -> str:
    return os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")


def _max_input_chars() -> int:
    return int(os.getenv("MAX_INPUT_CHARS", "150000"))


def _request_json(client: anthropic.Anthropic, system: str, user_msg: str) -> dict:
    """Ein API-Call + robustes JSON-Parsing (entfernt evtl. Markdown-Zäune)."""
    resp = client.messages.create(
        model=_model(),
        max_tokens=16000,
        system=system,
        messages=[{"role": "user", "content": user_msg}],
    )
    raw = "".join(b.text for b in resp.content if b.type == "text")
    raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(raw)


def _split_text(text: str, limit: int) -> list[str]:
    """Teilt an Absatzgrenzen in Stücke <= limit; überlange Absätze hart teilen."""
    chunks: list[str] = []
    current = ""
    for para in text.split("\n\n"):
        while len(para) > limit:  # pathologischer Einzelabsatz
            chunks.append(para[:limit])
            para = para[limit:]
        if len(current) + len(para) + 2 > limit and current:
            chunks.append(current)
            current = para
        else:
            current = f"{current}\n\n{para}" if current else para
    if current:
        chunks.append(current)
    return chunks


def generate_script(course_text: str, api_key: str, modulnummer: str | None = None) -> dict:
    client = anthropic.Anthropic(api_key=api_key)
    prefix = f"Modulnummer: {modulnummer or 'unbekannt'}\n\nKurstext:\n"
    limit = _max_input_chars()

    if len(course_text) <= limit:
        return _request_json(client, SYSTEM_PROMPT, prefix + course_text)

    chunks = _split_text(course_text, limit)
    merged: dict | None = None
    for i, chunk in enumerate(chunks, start=1):
        system = SYSTEM_PROMPT + _PART_NOTE.format(i=i, n=len(chunks))
        part = _request_json(client, system, prefix + chunk)
        if merged is None:
            merged = part
        else:
            merged["kapitel"].extend(part.get("kapitel", []))
    return merged or {"titel": "Leeres Modul", "modul": modulnummer or "", "kapitel": []}
