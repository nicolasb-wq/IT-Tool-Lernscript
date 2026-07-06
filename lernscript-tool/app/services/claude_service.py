"""Anbindung an die Anthropic API: Kurs-PDF-Text -> strukturiertes Lernscript-JSON."""
import json
import os

import anthropic

MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

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


def generate_script(course_text: str, api_key: str, modulnummer: str | None = None) -> dict:
    client = anthropic.Anthropic(api_key=api_key)
    user_msg = f"Modulnummer: {modulnummer or 'unbekannt'}\n\nKurstext:\n{course_text[:150000]}"
    resp = client.messages.create(
        model=MODEL,
        max_tokens=16000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )
    raw = "".join(b.text for b in resp.content if b.type == "text")
    raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(raw)
