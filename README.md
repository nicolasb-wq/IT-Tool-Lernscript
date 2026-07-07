# Lernscript-Generator

Web-App: Kursmodul-PDF hochladen → Claude erstellt beginnerfreundliches
Lernscript-JSON → ReportLab rendert es im WBS-Stil (gemessene Originalfarben).

## Quickstart (lokal)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # ANTHROPIC_API_KEY eintragen
uvicorn app.main:app --reload
# → http://127.0.0.1:8000
```

## Tests
```bash
pytest
```

## Docker
```bash
docker build -t lernscript .
docker run -p 8000:8000 --env-file .env -v ./data:/data lernscript
```

Details: docs/ARCHITEKTUR.md · Stilwerte: docs/STYLE_GUIDE.md · Produktiv-Deployment: docs/DEPLOYMENT.md
