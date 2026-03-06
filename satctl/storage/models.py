"""SQLAlchemy models for satctl SIGINT-first database."""

from __future__ import annotations

from datetime import datetime
from typing import Optional, List
from sqlalchemy import Integer, String, DateTime, Text, Index, ForeignKey, Float
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class Satellite(Base):
    """Core satellite catalog table."""

    __tablename__ = "satellites"

    norad_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    object_type: Mapped[str | None] = mapped_column(String(50), nullable=True) # PAYLOAD, DEBRIS, etc
    owner_code: Mapped[str | None] = mapped_column(String(10), nullable=True) # US, IND, etc
    owner_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    operator: Mapped[str | None] = mapped_column(String(255), nullable=True)
    orbit_class: Mapped[str | None] = mapped_column(String(50), nullable=True) # LEO, MEO, etc
    launch_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    tle_records: Mapped[List[TLE]] = relationship(
        "TLE", back_populates="satellite", cascade="all, delete-orphan"
    )
    transmitters: Mapped[List[Transmitter]] = relationship(
        "Transmitter", back_populates="satellite"
    )
    observations: Mapped[List[Observation]] = relationship(
        "Observation", back_populates="satellite"
    )
    anomalies: Mapped[List[Anomaly]] = relationship(
        "Anomaly", back_populates="satellite"
    )

    def __repr__(self) -> str:
        return f"<Satellite(norad_id={self.norad_id}, name={self.name!r})>"


class TLE(Base):
    """TLE history table."""

    __tablename__ = "tle"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    norad_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("satellites.norad_id"), nullable=False
    )
    epoch: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    line1: Mapped[str] = mapped_column(String(130), nullable=False)
    line2: Mapped[str] = mapped_column(String(130), nullable=False)
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    # Relationship to Satellite
    satellite: Mapped[Satellite] = relationship("Satellite", back_populates="tle_records")

    __table_args__ = (
        Index("idx_tle_norad_epoch", "norad_id", "epoch"),
        Index("idx_tle_epoch_desc", "epoch"),
    )

    def __repr__(self) -> str:
        return f"<TLE(norad_id={self.norad_id}, epoch={self.epoch})>"


class Transmitter(Base):
    """SIGINT metadata (transmitters)."""

    __tablename__ = "transmitters"

    tx_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    norad_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("satellites.norad_id"), nullable=True
    )
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    downlink_freq_hz: Mapped[float | None] = mapped_column(Float, nullable=True)
    uplink_freq_hz: Mapped[float | None] = mapped_column(Float, nullable=True)
    mode: Mapped[str | None] = mapped_column(String(50), nullable=True)
    bandwidth_hz: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)

    # Relationships
    satellite: Mapped[Satellite] = relationship("Satellite", back_populates="transmitters")
    observations: Mapped[List[Observation]] = relationship("Observation", back_populates="transmitter")

    def __repr__(self) -> str:
        return f"<Transmitter(id={self.tx_id}, name={self.name!r})>"


class Observation(Base):
    """Time-series of observed signals."""

    __tablename__ = "observations"

    obs_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    norad_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("satellites.norad_id"), nullable=True)
    tx_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("transmitters.tx_id"), nullable=True)
    source: Mapped[str] = mapped_column(String(100), nullable=False) # e.g. SatNOGS
    station_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    region_tag: Mapped[str | None] = mapped_column(String(50), nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    satellite: Mapped[Satellite] = relationship("Satellite", back_populates="observations")
    transmitter: Mapped[Transmitter] = relationship("Transmitter", back_populates="observations")

    __table_args__ = (
        Index("idx_obs_ts_desc", "ts"),
        Index("idx_obs_norad_ts", "norad_id", "ts"),
        Index("idx_obs_tx_ts", "tx_id", "ts"),
    )


class Anomaly(Base):
    """Generated anomaly events."""

    __tablename__ = "anomalies"

    anom_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    severity: Mapped[str] = mapped_column(String(20), nullable=False) # LOW, MED, HIGH
    type: Mapped[str] = mapped_column(String(50), nullable=False) # RF_APPEAR, etc
    norad_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("satellites.norad_id"), nullable=True)
    tx_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("transmitters.tx_id"), nullable=True)
    region_tag: Mapped[str | None] = mapped_column(String(50), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    details_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    fingerprint: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(20), default="OPEN") # OPEN, ACK, RESOLVED

    # Relationships
    satellite: Mapped[Satellite] = relationship("Satellite", back_populates="anomalies")

    __table_args__ = (
        Index("idx_anom_ts_desc", "ts"),
        Index("idx_anom_type_ts", "type", "ts"),
        Index("idx_anom_norad_ts", "norad_id", "ts"),
    )


class Source(Base):
    """Track last sync per provider."""

    __tablename__ = "sources"

    source_name: Mapped[str] = mapped_column(String(100), primary_key=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    record_count: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

class CatalogEvent(Base):
    """Track catalog changes and new discoveries."""

    __tablename__ = "catalog_events"

    event_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    norad_id: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False) # NEW_OBJECT, REENTRY, etc
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<CatalogEvent(id={self.event_id}, type={self.event_type}, norad={self.norad_id})>"
