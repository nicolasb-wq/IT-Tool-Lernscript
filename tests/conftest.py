"""Gemeinsame Test-Fixtures: frische DB pro Test via db.configure(), gemockte Claude-API."""
import pytest
from fastapi.testclient import TestClient

SAMPLE_SCRIPT = {
    "titel": "Test", "modul": "M",
    "kapitel": [{"titel": "K1", "bloecke": [{"typ": "text", "text": "Inhalt"}]}],
}

INVITE = "geheimer-code"


def pdf_file(name: str) -> tuple:
    return ("files", (name, b"%PDF-1.4 dummy content", "application/pdf"))


@pytest.fixture()
def app_client(tmp_path, monkeypatch, request):
    """Frischer App-Zustand pro Test: eigene SQLite-Datei, Mocks, geleerter
    Ergebnis-Speicher. FREE_GENERATIONS via indirekter Parametrisierung
    steuerbar (Default: 5) — wird zur Laufzeit gelesen, kein Reload nötig."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-central-test")
    monkeypatch.setenv("INVITE_CODE", INVITE)
    monkeypatch.setenv("FREE_GENERATIONS", getattr(request, "param", "5"))

    from app import db
    db.configure(f"sqlite:///{tmp_path}/test.sqlite3")
    db.init_db()

    from app.services import claude_service, pdf_parser
    monkeypatch.setattr(pdf_parser, "extract_text", lambda data: "Extrahierter Kurstext")
    monkeypatch.setattr(
        claude_service, "generate_script",
        lambda text, api_key, modulnummer=None: SAMPLE_SCRIPT,
    )

    from app import main
    main._RESULTS.clear()
    client = TestClient(main.app)
    client.__dict__["main_module"] = main
    return client


@pytest.fixture()
def logged_in(app_client):
    """Registriert und meldet einen Testnutzer an; Session-Cookie bleibt im Client."""
    r = app_client.post("/register", data={
        "email": "test@example.com", "password": "passwort123", "invite_code": INVITE,
    }, follow_redirects=False)
    assert r.status_code == 303, r.text
    return app_client
