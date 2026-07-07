"""Hybrid-Kostenmodell: Freikontingent pro NUTZERKONTO (nicht mehr pro Cookie),
danach eigener API-Key. Zähler liegt in der Usage-Tabelle (SQLAlchemy)."""
import os

from sqlalchemy.orm import Session

from app.models import Usage


def _free_limit() -> int:
    return int(os.getenv("FREE_GENERATIONS", "3"))


def remaining(session: Session, user_id: int) -> int:
    usage = session.get(Usage, user_id)
    used = usage.count if usage else 0
    return max(0, _free_limit() - used)


def consume(session: Session, user_id: int) -> None:
    usage = session.get(Usage, user_id)
    if usage is None:
        usage = Usage(user_id=user_id, count=0)
        session.add(usage)
    usage.count += 1
    session.commit()


def resolve_api_key(session: Session, user_id: int, user_key: str | None) -> tuple[str, bool]:
    """Gibt (api_key, uses_free_quota) zurück oder wirft ValueError."""
    if user_key:
        return user_key, False
    if remaining(session, user_id) > 0:
        central = os.getenv("ANTHROPIC_API_KEY")
        if not central:
            raise ValueError("Zentraler API-Key nicht konfiguriert.")
        return central, True
    raise ValueError("Freikontingent aufgebraucht — bitte eigenen API-Key angeben.")
