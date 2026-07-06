
import pytest


@pytest.fixture()
def quota(tmp_path, monkeypatch):
    monkeypatch.setenv("QUOTA_DB", str(tmp_path / "q.sqlite3"))
    monkeypatch.setenv("FREE_GENERATIONS", "2")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-central")
    import importlib

    from app.services import quota as q
    importlib.reload(q)
    return q


def test_free_quota_then_own_key_required(quota):
    key, free = quota.resolve_api_key("u1", None)
    assert key == "sk-central" and free
    quota.consume("u1")
    quota.consume("u1")
    with pytest.raises(ValueError):
        quota.resolve_api_key("u1", None)
    key, free = quota.resolve_api_key("u1", "sk-own")
    assert key == "sk-own" and not free
