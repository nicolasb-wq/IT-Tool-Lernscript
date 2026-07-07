"""Tests für die kapitelweise Verarbeitung großer Module (ohne echte API-Calls)."""
from app.services import claude_service


def _fake_requests(monkeypatch):
    calls = []

    def fake(client, system, user_msg):
        calls.append({"system": system, "user": user_msg})
        i = len(calls)
        return {"titel": f"Teil {i}", "modul": "M",
                "kapitel": [{"titel": f"Kapitel aus Call {i}", "bloecke": []}]}

    monkeypatch.setattr(claude_service, "_request_json", fake)
    return calls


def test_small_text_single_call(monkeypatch):
    calls = _fake_requests(monkeypatch)
    monkeypatch.setenv("MAX_INPUT_CHARS", "1000")
    result = claude_service.generate_script("kurzer Text", "sk-x")
    assert len(calls) == 1
    assert "TEIL" not in calls[0]["system"]
    assert len(result["kapitel"]) == 1


def test_large_text_chunked_and_merged(monkeypatch):
    calls = _fake_requests(monkeypatch)
    monkeypatch.setenv("MAX_INPUT_CHARS", "100")
    text = "\n\n".join(f"Absatz {i} mit etwas Inhalt darin." for i in range(12))
    result = claude_service.generate_script(text, "sk-x")
    assert len(calls) > 1, "erwartet: mehrere API-Calls"
    # Alle Teil-Kapitel landen zusammengeführt im EINEN Ergebnis-Skript
    assert len(result["kapitel"]) == len(calls)
    assert result["titel"] == "Teil 1"
    # Teil-Hinweis steckt im System-Prompt jedes Chunk-Calls
    assert all("TEIL" in c["system"] for c in calls)


def test_split_respects_paragraph_boundaries():
    text = "\n\n".join(["A" * 40, "B" * 40, "C" * 40])
    chunks = claude_service._split_text(text, limit=100)
    assert len(chunks) == 2
    assert all(len(c) <= 100 for c in chunks)
    # kein Absatz wurde zerrissen
    assert chunks[0].count("A") == 40 and chunks[1].count("C") == 40


def test_split_handles_oversized_single_paragraph():
    chunks = claude_service._split_text("X" * 250, limit=100)
    assert [len(c) for c in chunks] == [100, 100, 50]
