"""Tests für Multi-PDF-Upload (Punkt 1: getrennte Skripte, Quota pro Skript,
Batch-Ablehnung bei unzureichendem Freikontingent, Einzeldownloads)."""
import importlib

import pytest
from fastapi.testclient import TestClient

SAMPLE_SCRIPT = {
    "titel": "Test", "modul": "M",
    "kapitel": [{"titel": "K1", "bloecke": [{"typ": "text", "text": "Inhalt"}]}],
}


def _pdf_file(name: str) -> tuple:
    return ("files", (name, b"%PDF-1.4 dummy content", "application/pdf"))


@pytest.fixture()
def app_client(tmp_path, monkeypatch, request):
    """Frischer App-Zustand pro Test: eigene Quota-DB, gemockte externe Aufrufe.

    FREE_GENERATIONS wird VOR diesem Fixture über
    @pytest.mark.parametrize oder direkt per monkeypatch.setenv im Testkörper
    gesetzt — deshalb lesen wir es hier über eine indirekte Fixture-Variante neu ein
    (siehe _reload_quota-Helfer, den jeder Test bei Bedarf selbst aufruft).
    """
    monkeypatch.setenv("QUOTA_DB", str(tmp_path / "quota.sqlite3"))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-central-test")
    monkeypatch.setenv("FREE_GENERATIONS", getattr(request, "param", "5"))

    from app.services import quota as quota_module
    importlib.reload(quota_module)

    from app.services import claude_service, pdf_parser
    monkeypatch.setattr(pdf_parser, "extract_text", lambda data: "Extrahierter Kurstext")
    monkeypatch.setattr(
        claude_service, "generate_script",
        lambda text, api_key, modulnummer=None: SAMPLE_SCRIPT,
    )

    from app import main as main_module
    importlib.reload(main_module)
    main_module._RESULTS.clear()
    return TestClient(main_module.app)


def test_batch_creates_one_script_per_file(app_client):
    r = app_client.post(
        "/generate",
        data={"modulnummer": "NEINT1"},
        files=[_pdf_file("a.pdf"), _pdf_file("b.pdf"), _pdf_file("c.pdf")],
    )
    assert r.status_code == 200
    results = r.json()["results"]
    assert len(results) == 3
    # Jede Datei erzeugt ein eigenes, eindeutig benanntes Skript
    names = {item["filename"] for item in results}
    assert len(names) == 3
    assert all("NEINT1" in n for n in names)


def test_each_result_downloadable_exactly_once(app_client):
    r = app_client.post("/generate", files=[_pdf_file("a.pdf")])
    result_id = r.json()["results"][0]["id"]

    first = app_client.get(f"/download/{result_id}")
    assert first.status_code == 200
    assert first.content.startswith(b"%PDF")

    second = app_client.get(f"/download/{result_id}")
    assert second.status_code == 404


@pytest.mark.parametrize("app_client", ["1"], indirect=True)
def test_batch_rejected_when_quota_insufficient_for_all_files(app_client):
    """Randfall-Entscheidung: 3 Dateien, nur 1 freie Generierung → ganzer Batch abgelehnt."""
    r = app_client.post(
        "/generate",
        files=[_pdf_file("a.pdf"), _pdf_file("b.pdf"), _pdf_file("c.pdf")],
    )
    assert r.status_code == 402
    assert "Freikontingent reicht nicht" in r.json()["detail"]


@pytest.mark.parametrize("app_client", ["1"], indirect=True)
def test_batch_partial_quota_produces_no_results_at_all(app_client):
    """Wichtig: bei Ablehnung dürfen NICHT teilweise Skripte erzeugt worden sein."""
    app_client.post("/generate", files=[_pdf_file("a.pdf"), _pdf_file("b.pdf")])
    from app import main as main_module
    assert len(main_module._RESULTS) == 0


@pytest.mark.parametrize("app_client", ["0"], indirect=True)
def test_own_api_key_bypasses_quota_check(app_client):
    r = app_client.post(
        "/generate",
        data={"user_api_key": "sk-own-key"},
        files=[_pdf_file("a.pdf"), _pdf_file("b.pdf")],
    )
    assert r.status_code == 200
    assert len(r.json()["results"]) == 2


def test_non_pdf_file_rejected(app_client):
    r = app_client.post(
        "/generate",
        files=[("files", ("a.txt", b"hallo", "text/plain"))],
    )
    assert r.status_code == 400
    assert "keine PDF-Datei" in r.json()["detail"]


def test_total_size_limit_enforced(app_client):
    big = b"0" * (26 * 1024 * 1024)
    r = app_client.post(
        "/generate",
        files=[("files", ("big.pdf", big, "application/pdf"))],
    )
    assert r.status_code == 400
    assert "25 MB" in r.json()["detail"]
