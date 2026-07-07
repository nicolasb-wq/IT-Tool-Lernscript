"""Datenmodell: Nutzerkonten + Freikontingent-Zähler pro Konto."""
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), nullable=False
    )


class Usage(Base):
    __tablename__ = "usage"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
