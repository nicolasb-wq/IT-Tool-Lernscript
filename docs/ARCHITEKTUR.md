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

- Login/Nutzerkonten: umgesetzt — schlanker Eigenbau (Projektentscheidung).
  bcrypt-Hashing, Session via signiertem HttpOnly-Cookie (SessionMiddleware,
  SECRET_KEY aus .env), Registrierung nur mit Invite-Code (statischer Wert
  INVITE_CODE aus .env, MVP-Entscheidung). SQLAlchemy 2.x eingeführt:
  users- und usage-Tabellen, DATABASE_URL aus .env (Default SQLite,
  Postgres-Wechsel beim Deployment = nur URL tauschen). Freikontingent hängt
  jetzt am Konto, nicht mehr am Browser-Cookie; Ergebnis-Downloads sind an den
  erzeugenden Nutzer gebunden. Alte Cookie-Zähler wurden nicht migriert
  (es gab noch keine echten Nutzer). Bewusst NICHT im MVP: Passwort-Reset und
  E-Mail-Verifikation (bräuchte SMTP), OAuth, Admin-UI.

- Deployment-Artefakte: umgesetzt — docker-compose.yml (App + Postgres 16 +
  Caddy mit Auto-HTTPS), Caddyfile (Domain als ENV-Variable), psycopg-Treiber,
  .env.production.example, scripts/backup.sh (pg_dump, 14 Stände) und
  vollständiges Runbook in docs/DEPLOYMENT.md (Server, Firewall 22/80/443,
  SSH-Härtung, DNS, Start, Backups, Updates, Fehlersuche).
  Entscheidungen: Postgres als Container auf dem VPS, Caddy, manuelles
  SSH-Deploy. Nicht lokal verifizierbar (kein Docker in der Sandbox):
  Compose-Lauf und Caddy-Zertifikatsbezug — erster echter Test auf dem Server.

- PDF-Parsing-Edge-Cases: umgesetzt — Magic-Bytes-Prüfung (Browser-Content-Type
  ist fälschbar), klare Fehler bei beschädigten/passwortgeschützten/leeren PDFs
  (ParserError -> HTTP 400 statt 500), OCR-Fallback für Scans (Tesseract deutsch,
  200 dpi Graustufen, MAX_OCR_PAGES=60 als DoS-Schutz). Große Module werden
  kapitelweise in mehreren API-Calls verarbeitet (Split an Absatzgrenzen bei
  MAX_INPUT_CHARS=150k, Kapitel werden zusammengeführt) — der stille
  Datenverlust durch hartes Abschneiden ist behoben. Ein Skript = weiterhin
  EIN Kontingent-Verbrauch, unabhängig von der Zahl interner API-Calls.
- Projekt-Review (5 behobene Mängel): (1) KI-Text wird jetzt escaped, bevor er
  in ReportLab-Paragraphen fließt (safe_markup; vorher Crash bei jedem '<' —
  in IT-Inhalten allgegenwärtig; <b>/<i>/<u> bleiben erlaubt). (2) ParserError
  wird in main.py abgefangen. (3) Dockerfile installiert Tesseract+deu.
  (4) .dockerignore ergänzt — verhindert v. a., dass .env-Secrets oder Backups
  ins Image geraten. (5) CI: veraltete QUOTA_DB-Variable entfernt, SECRET_KEY
  im Smoke-Test gesetzt, Tesseract-Installations-Step für die Test-Matrix.
  Kleinere Verbesserung: TTL-Purge des Ergebnis-Speichers auch im Download-Pfad.

- DSGVO-Texte: umgesetzt — Impressum und Datenschutzerklärung als echte,
  öffentlich (ohne Login) erreichbare Seiten (/impressum, /datenschutz),
  von Login/Register verlinkt. Inhaltlich beschreibt die Datenschutzerklärung
  die tatsächlichen Verarbeitungsvorgänge (Konto, temporäre PDF-Verarbeitung,
  Anthropic-API-Übermittlung, Session-Cookie, Hetzner-Hosting).
  WICHTIG, kein Rechtsrat: Entwurf mit echten Kontaktdaten des Betreibers,
  vor produktivem Betrieb fachlich prüfen lassen — insbesondere die
  internationale Datenübermittlung an Anthropic (USA) und die Frage, ob die
  private-Tätigkeit-Ausnahme (Art. 2 Abs. 2 lit. c DSGVO) hier überhaupt
  greift (eher nein, sobald fremde Dritte sich registrieren können).

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
