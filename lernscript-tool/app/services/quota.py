"""Hybrid-Kostenmodell: Freikontingent über zentralen Key, danach eigener Nutzer-Key.

MVP: SQLite-Zähler pro Nutzer. Bei Überschreitung muss der Nutzer
seinen eigenen Anthropic-API-Key im Formular mitgeben.
"""
import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.getenv("QUOTA_DB", "quota.sqlite3")
FREE_LIMIT = int(os.getenv("FREE_GENERATIONS", "3"))


@contextmanager
def _db():
    con = sqlite3.connect(DB_PATH)
    con.execute("CREATE TABLE IF NOT EXISTS usage (user_id TEXT PRIMARY KEY, count INTEGER NOT NULL)")
    try:
        yield con
        con.commit()
    finally:
        con.close()


def remaining(user_id: str) -> int:
    with _db() as con:
        row = con.execute("SELECT count FROM usage WHERE user_id=?", (user_id,)).fetchone()
    return max(0, FREE_LIMIT - (row[0] if row else 0))


def consume(user_id: str) -> None:
    with _db() as con:
        con.execute(
            "INSERT INTO usage(user_id,count) VALUES(?,1) "
            "ON CONFLICT(user_id) DO UPDATE SET count=count+1",
            (user_id,),
        )


def resolve_api_key(user_id: str, user_key: str | None) -> tuple[str, bool]:
    """Gibt (api_key, uses_free_quota) zurück oder wirft ValueError."""
    if user_key:
        return user_key, False
    if remaining(user_id) > 0:
        central = os.getenv("ANTHROPIC_API_KEY")
        if not central:
            raise ValueError("Zentraler API-Key nicht konfiguriert.")
        return central, True
    raise ValueError("Freikontingent aufgebraucht — bitte eigenen API-Key angeben.")
