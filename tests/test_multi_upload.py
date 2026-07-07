"""Tests für Multi-PDF-Upload mit Konto-gebundener Quota."""
import pytest

from tests.conftest import pdf_file


def test_batch_creates_one_script_per_file(logged_in):
    r = logged_in.post(
        "/generate",
        data={"modulnummer": "NEINT1"},
        files=[pdf_file("a.pdf"), pdf_file("b.pdf"), pdf_file("c.pdf")],
    )
    assert r.status_code == 200
    results = r.json()["results"]
    assert len(results) == 3
    assert len({item["filename"] for item in results}) == 3


def test_each_result_downloadable_exactly_once(logged_in):
    r = logged_in.post("/generate", files=[pdf_file("a.pdf")])
    result_id = r.json()["results"][0]["id"]
    first = logged_in.get(f"/download/{result_id}")
    assert first.status_code == 200
    assert first.content.startswith(b"%PDF")
    assert logged_in.get(f"/download/{result_id}").status_code == 404


@pytest.mark.parametrize("app_client", ["1"], indirect=True)
def test_batch_rejected_when_quota_insufficient(logged_in):
    r = logged_in.post(
        "/generate",
        files=[pdf_file("a.pdf"), pdf_file("b.pdf"), pdf_file("c.pdf")],
    )
    assert r.status_code == 402
    assert "Freikontingent reicht nicht" in r.json()["detail"]


@pytest.mark.parametrize("app_client", ["1"], indirect=True)
def test_rejected_batch_produces_no_results(logged_in):
    logged_in.post("/generate", files=[pdf_file("a.pdf"), pdf_file("b.pdf")])
    assert len(logged_in.main_module._RESULTS) == 0


@pytest.mark.parametrize("app_client", ["0"], indirect=True)
def test_own_api_key_bypasses_quota(logged_in):
    r = logged_in.post(
        "/generate",
        data={"user_api_key": "sk-own-key"},
        files=[pdf_file("a.pdf"), pdf_file("b.pdf")],
    )
    assert r.status_code == 200
    assert len(r.json()["results"]) == 2


@pytest.mark.parametrize("app_client", ["2"], indirect=True)
def test_quota_counts_per_generated_script(logged_in):
    """2 freie Generierungen: erst 2 Dateien OK, danach ist das Kontingent leer."""
    r1 = logged_in.post("/generate", files=[pdf_file("a.pdf"), pdf_file("b.pdf")])
    assert r1.status_code == 200
    r2 = logged_in.post("/generate", files=[pdf_file("c.pdf")])
    assert r2.status_code == 402


def test_quota_is_per_account_not_per_session(app_client):
    """Kern des Login-Umbaus: Abmelden+Anmelden setzt das Kontingent NICHT zurück."""
    from tests.conftest import INVITE
    app_client.post("/register", data={
        "email": "user@example.com", "password": "passwort123", "invite_code": INVITE,
    }, follow_redirects=False)
    app_client.post("/generate", files=[pdf_file("a.pdf")])
    app_client.post("/logout")
    app_client.post("/login", data={"email": "user@example.com", "password": "passwort123"},
                    follow_redirects=False)
    r = app_client.get("/")
    assert "noch <b>4</b>" in r.text  # 5 - 1 = 4, trotz neuer Session


def test_non_pdf_rejected(logged_in):
    r = logged_in.post("/generate", files=[("files", ("a.txt", b"x", "text/plain"))])
    assert r.status_code == 400


def test_total_size_limit(logged_in):
    big = b"0" * (26 * 1024 * 1024)
    r = logged_in.post("/generate", files=[("files", ("big.pdf", big, "application/pdf"))])
    assert r.status_code == 400
    assert "25 MB" in r.json()["detail"]


def test_download_of_other_users_result_denied(app_client):
    """Nutzer B darf das Ergebnis von Nutzer A nicht abrufen."""
    from tests.conftest import INVITE
    app_client.post("/register", data={
        "email": "a@example.com", "password": "passwort123", "invite_code": INVITE,
    }, follow_redirects=False)
    r = app_client.post("/generate", files=[pdf_file("a.pdf")])
    result_id = r.json()["results"][0]["id"]
    app_client.post("/logout")
    app_client.post("/register", data={
        "email": "b@example.com", "password": "passwort123", "invite_code": INVITE,
    }, follow_redirects=False)
    assert app_client.get(f"/download/{result_id}").status_code == 404
