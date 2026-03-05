"""SQLAlchemy models for satctl database."""

from __future__ import annotations

from datetime import datetime
from sqlalchemy import Integer, String, DateTime, Text, Index, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class Satellite(Base):
    """Satellite metadata."""

    __tablename__ = "satellite"

    norad_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationship to TLE
    tle_records: Mapped[list[TLE]] = relationship(
        "TLE", back_populates="satellite", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Satellite(norad_id={self.norad_id}, name={self.name!r})>"


class TLE(Base):
    """Two-Line Element data."""

    __tablename__ = "tle"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    norad_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("satellite.norad_id"), nullable=False
    )
    epoch: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    line1: Mapped[str] = mapped_column(String(130), nullable=False)
    line2: Mapped[str] = mapped_column(String(130), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    # Relationship to Satellite
    satellite: Mapped[Satellite] = relationship("Satellite", back_populates="tle_records")

    __table_args__ = (
        Index("idx_tle_norad", "norad_id"),
        Index("idx_tle_epoch", "epoch"),
    )

    def __repr__(self) -> str:
        return f"<TLE(norad_id={self.norad_id}, epoch={self.epoch})>"


class SyncLog(Base):
    """Log of sync operations."""

    __tablename__ = "sync_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    satellites_added: Mapped[int] = mapped_column(Integer, default=0)
    satellites_updated: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<SyncLog(id={self.id}, started_at={self.started_at})>"
