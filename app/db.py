"""SQLAlchemy-Setup mit Laufzeit-Konfiguration.

DATABASE_URL aus ENV, Default: lokale SQLite-Datei. configure() kann die Engine
jederzeit neu aufbauen (Tests, spätere Postgres-Migration beim Deployment).
"""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


_engine = None
_session_factory = None


def configure(url: str | None = None) -> None:
    """(Re-)Initialisiert Engine + Session-Factory. Ohne Argument: ENV/Default."""
    global _engine, _session_factory
    url = url or os.getenv("DATABASE_URL", "sqlite:///./lernscript.sqlite3")
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    if _engine is not None:
        _engine.dispose()
    _engine = create_engine(url, connect_args=connect_args)
    _session_factory = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    if _engine is None:
        configure()
    from app import models  # noqa: F401 — Modelle bei Base registrieren
    Base.metadata.create_all(_engine)


def get_session() -> Session:
    if _session_factory is None:
        configure()
    return _session_factory()
