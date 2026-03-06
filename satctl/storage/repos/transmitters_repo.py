"""Repository for SIGINT transmitter and observation operations."""

from __future__ import annotations
from datetime import datetime
from pathlib import Path
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from satctl.storage.models import Transmitter, Observation
from satctl.storage.db import get_session
from satctl.domain.models import TransmitterRecord, ObservationRecord


class TransmitterRepository:
    """Repository for transmitter and observation data."""

    def __init__(self, db_path: Path):
        self.db_path = db_path

    def _get_session(self) -> Session:
        return get_session(self.db_path)

    def get_count(self) -> int:
        with self._get_session() as session:
            return session.execute(select(func.count()).select_from(Transmitter)).scalar_one()

    def get_all(self, limit: int | None = None) -> list[Transmitter]:
        with self._get_session() as session:
            stmt = select(Transmitter)
            if limit:
                stmt = stmt.limit(limit)
            return list(session.execute(stmt).scalars().all())

    def get_transmitters_for_satellite(self, norad_id: int) -> list[Transmitter]:
        with self._get_session() as session:
            stmt = select(Transmitter).where(Transmitter.norad_id == norad_id)
            return list(session.execute(stmt).scalars().all())
        """Upsert transmitter metadata."""
        if not records:
            return 0
        
        count = 0
        with self._get_session() as session:
            for r in records:
                # Deduplicate by norad_id + freq + mode if possible, 
                # but for now, simple upsert by norad_id + name
                stmt = select(Transmitter).where(
                    (Transmitter.norad_id == r.norad_id) & 
                    (Transmitter.name == r.name)
                )
                existing = session.execute(stmt).scalar_one_or_none()
                
                if existing:
                    existing.downlink_freq_hz = r.downlink_freq_hz
                    existing.uplink_freq_hz = r.uplink_freq_hz
                    existing.mode = r.mode
                    existing.bandwidth_hz = r.bandwidth_hz
                    existing.source = r.source
                else:
                    tx = Transmitter(
                        norad_id=r.norad_id,
                        name=r.name,
                        description=r.description,
                        downlink_freq_hz=r.downlink_freq_hz,
                        uplink_freq_hz=r.uplink_freq_hz,
                        mode=r.mode,
                        bandwidth_hz=r.bandwidth_hz,
                        source=r.source
                    )
                    session.add(tx)
                count += 1
            session.commit()
        return count
