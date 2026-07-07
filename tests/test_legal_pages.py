"""Tests: Impressum/Datenschutz sind öffentlich (ohne Login) erreichbar
und enthalten die Pflichtangaben."""


def test_impressum_reachable_without_login(app_client):
    r = app_client.get("/impressum")
    assert r.status_code == 200
    assert "Nicolas Max Bauer" in r.text
    assert "Sandesneben" in r.text
    assert "nicolas_b@outlook.de" in r.text


def test_datenschutz_reachable_without_login(app_client):
    r = app_client.get("/datenschutz")
    assert r.status_code == 200
    assert "Verantwortlicher" in r.text
    assert "Anthropic" in r.text
    assert "Hetzner" in r.text


def test_login_page_links_to_legal_pages(app_client):
    r = app_client.get("/login")
    assert '/impressum' in r.text
    assert '/datenschutz' in r.text
