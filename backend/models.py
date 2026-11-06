import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from database import Base


def utcnow():
    return datetime.now(timezone.utc)


class ApiSession(Base):
    __tablename__ = "api_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_github_id: Mapped[int] = mapped_column(Integer, index=True)
    user_login: Mapped[str] = mapped_column(String(128), index=True)
    csrf_token: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CalculationRun(Base):
    __tablename__ = "calculation_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_github_id: Mapped[int] = mapped_column(Integer, index=True)
    user_login: Mapped[str] = mapped_column(String(128), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    status: Mapped[str] = mapped_column(String(32))
    inputs: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    uncertainty: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    data_version: Mapped[str | None] = mapped_column(String(256), nullable=True)
    calculation_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    provenance: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
