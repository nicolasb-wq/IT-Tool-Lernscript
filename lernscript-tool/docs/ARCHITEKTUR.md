# Architekturplan — Lernscript-Generator

## Entscheidungen (aus Klärungsphase)
KI generiert Text+Layout · Input: PDF-Upload · Web-App · FastAPI + Jinja2 (SSR)
· Anthropic API · Hybrid-Kosten (Freikontingent, dann eigener Key)
· Uploads nur temporär · Hosting: Hetzner Cloud VPS (EU, DSGVO)
· Ziel: production-ready in ~1 Monat, Portfolio-tauglich.

## Ablauf
Browser → POST /generate (PDF + Modulnr. + optional API-Key)
→ Quota-Check (SQLite) → PyMuPDF-Textextraktion (nur RAM)
→ Claude API (System-Prompt erzwingt Skript-JSON-Schema)
→ ReportLab (pdf_style.py + pdf_generator.py) → PDF-Download.
Keine Persistenz der Uploads/Ergebnisse (Datenschutz-Entscheidung).

## Komponenten
- app/pdf_style.py — gemessene Farb-/Typo-Konstanten, Banner/Boxen/Tabellen/Fußzeile
- app/services/pdf_parser.py — Textextraktion
- app/services/claude_service.py — Prompt + JSON-Parsing
- app/services/quota.py — Freikontingent (SQLite, ENV-konfigurierbar)
- app/services/pdf_generator.py — JSON → PDF
- app/main.py — FastAPI-Routen, templates/index.html — UI

## Roadmap (4 Wochen)
W1: MVP lokal lauffähig (dieses Gerüst), Source Sans Pro TTF einbetten,
    Prompt anhand echter Modul-PDFs tunen.
W2: Login (empfohlen: fastapi-users o. simple Session+Passwort), Quota an
    Nutzerkonto statt Cookie binden, Fehler-UI, Fortschrittsanzeige (SSE).
W3: Docker-Deploy auf Hetzner (Caddy als Reverse-Proxy mit HTTPS),
    Postgres statt SQLite, Rate-Limiting, Logging/Monitoring (z.B. Uptime Kuma).
W4: Tests ausbauen (E2E mit httpx), Doku, Portfolio-Politur, Beta-Nutzer.

## Sicherheits-/DSGVO-Notizen
- Nutzer-API-Keys niemals loggen oder speichern (nur pro Request im RAM).
- Hinweis in UI: Kursinhalte werden an Anthropic-API übertragen
  (Auftragsverarbeitung prüfen, AV-Vertrag/Anthropic-DPA für Mehrbenutzerbetrieb).
  Unsicher: rechtliche Details bitte selbst verifizieren, ich bin kein Anwalt.
- Uploads-Limit 25 MB, Content-Type-Prüfung vorhanden; später zusätzlich
  Magic-Bytes-Check.

## Bekannte offene Punkte
- ~~Font: Helvetica-Fallback~~ — erledigt: Source Sans 3 (OFL-lizenziert, optisch
  identisch zu "Source Sans Pro") ist eingebettet, siehe app/fonts/. Lizenz
  bestätigt geprüft (SIL OFL 1.1, freie Einbettung erlaubt). Fällt automatisch
  auf Helvetica zurück, falls die TTF-Dateien in einer Docker-Schicht fehlen
  sollten (defensive Absicherung in pdf_style._register_fonts()).
- Claude-Antworten >16k Tokens bei sehr großen Modulen: ggf. kapitelweises
  Generieren (mehrere API-Calls) in W2 nachrüsten.
- Multi-PDF-Upload (Punkt 1 der Prioritätenliste): umgesetzt — main.py verarbeitet
  mehrere Dateien, ein Skript pro Datei, Vorab-Quota-Check lehnt Batches ab,
  die das Freikontingent überschreiten, Downloads erfolgen einzeln nacheinander
  über /download/{id} mit kurzlebigem In-Memory-Speicher (15 Min. TTL).
- CI: umgesetzt — .github/workflows/ci.yml mit drei Jobs: ruff-Linting,
  pytest-Matrix (Python 3.11/3.12/3.13), Docker-Build + Health-Smoke-Test.
  Trigger: jeder Push + Pull Requests, ohne Branch-Filter. Ruff-Konfiguration
  in pyproject.toml (E/F/I/B/UP, FastAPI-Idiom B008 ausgenommen).
  Hinweis: Docker-Job und die Python-Versionen 3.11/3.13 konnten lokal nicht
  verifiziert werden (Sandbox hat kein Docker, nur Python 3.12) — erster
  echter Lauf erfolgt auf GitHub.
