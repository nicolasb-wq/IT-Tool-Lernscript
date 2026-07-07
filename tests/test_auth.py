"""Tests: Registrierung, Login, Zugriffsschutz."""
from tests.conftest import INVITE, pdf_file


def test_register_with_valid_invite_logs_in(app_client):
    r = app_client.post("/register", data={
        "email": "neu@example.com", "password": "passwort123", "invite_code": INVITE,
    }, follow_redirects=False)
    assert r.status_code == 303
    # Danach ist die Startseite erreichbar (kein Redirect zu /login)
    r2 = app_client.get("/", follow_redirects=False)
    assert r2.status_code == 200


def test_register_with_wrong_invite_rejected(app_client):
    r = app_client.post("/register", data={
        "email": "neu@example.com", "password": "passwort123", "invite_code": "falsch",
    })
    assert r.status_code == 400
    assert "Invite-Code" in r.text


def test_register_duplicate_email_rejected(logged_in):
    r = logged_in.post("/register", data={
        "email": "test@example.com", "password": "passwort123", "invite_code": INVITE,
    })
    assert r.status_code == 400
    assert "bereits registriert" in r.text


def test_register_short_password_rejected(app_client):
    r = app_client.post("/register", data={
        "email": "neu@example.com", "password": "kurz", "invite_code": INVITE,
    })
    assert r.status_code == 400


def test_login_wrong_password_generic_error(logged_in):
    logged_in.post("/logout")
    r = logged_in.post("/login", data={"email": "test@example.com", "password": "falsch"})
    assert r.status_code == 401
    assert "E-Mail oder Passwort falsch" in r.text


def test_login_unknown_email_same_error_message(app_client):
    r = app_client.post("/login", data={"email": "wer@example.com", "password": "egal1234"})
    assert r.status_code == 401
    assert "E-Mail oder Passwort falsch" in r.text


def test_index_redirects_to_login_when_anonymous(app_client):
    r = app_client.get("/", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/login"


def test_generate_requires_login(app_client):
    r = app_client.post("/generate", files=[pdf_file("a.pdf")])
    assert r.status_code == 401


def test_download_requires_login(app_client):
    r = app_client.get("/download/irgendeine-id")
    assert r.status_code == 401


def test_logout_ends_session(logged_in):
    logged_in.post("/logout", follow_redirects=False)
    r = logged_in.get("/", follow_redirects=False)
    assert r.status_code == 303
