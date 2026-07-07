"""Registrierung/Login: bcrypt-Hashing, Invite-Code-Prüfung.

Bewusst schlanker Eigenbau (Projektentscheidung): bcrypt direkt statt passlib,
Session-Handling übernimmt Starlettes SessionMiddleware in main.py.
"""
import os

import bcrypt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Usage, User


class AuthError(ValueError):
    """Fachlicher Auth-Fehler mit nutzertauglicher Meldung."""


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:
        return False


def register_user(session: Session, email: str, password: str, invite_code: str) -> User:
    expected = os.getenv("INVITE_CODE", "")
    if not expected:
        raise AuthError("Registrierung ist derzeit deaktiviert (kein Invite-Code konfiguriert).")
    if invite_code.strip() != expected:
        raise AuthError("Ungültiger Invite-Code.")

    email = email.strip().lower()
    if not email or "@" not in email:
        raise AuthError("Bitte eine gültige E-Mail-Adresse angeben.")
    if len(password) < 8:
        raise AuthError("Passwort muss mindestens 8 Zeichen lang sein.")
    if session.scalar(select(User).where(User.email == email)):
        raise AuthError("Diese E-Mail-Adresse ist bereits registriert.")

    user = User(email=email, password_hash=hash_password(password))
    session.add(user)
    session.flush()  # user.id verfügbar machen
    session.add(Usage(user_id=user.id, count=0))
    session.commit()
    return user


def authenticate(session: Session, email: str, password: str) -> User:
    user = session.scalar(select(User).where(User.email == email.strip().lower()))
    # Bewusst identische Meldung für "unbekannte E-Mail" und "falsches Passwort",
    # um keine Information preiszugeben, welche Konten existieren.
    if not user or not user.is_active or not verify_password(password, user.password_hash):
        raise AuthError("E-Mail oder Passwort falsch.")
    return user
