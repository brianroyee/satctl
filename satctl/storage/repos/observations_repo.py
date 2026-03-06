"""Repository for signal observations."""

from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from satctl.storage.models import Observation
from satctl.storage.db import get_session
from satctl.domain.models import ObservationRecord


class ObservationRepository:
    """Repository for signal observation data."""

    def __init__(self, db_path: Path):
        self.db_path = db_path

    def _get_session(self) -> Session:
        return get_session(self.db_path)

    def get_count(self) -> int:
        with self._get_session() as session:
            return session.execute(select(func.count()).select_from(Observation)).scalar_one()

    def record_observation(self, obs: ObservationRecord) -> None:
        """Log a new signal observation."""
        with self._get_session() as session:
            db_obs = Observation(
                ts=obs.ts,
                norad_id=obs.norad_id,
                tx_id=obs.tx_id,
                source=obs.source,
                station_id=obs.station_id,
                region_tag=obs.region_tag,
                metadata_json=json.dumps(obs.metadata) if obs.metadata else None
            )
            session.add(db_obs)
            session.commit()

    def get_recent(self, limit: int = 50) -> list[Observation]:
        with self._get_session() as session:
            stmt = select(Observation).order_by(Observation.ts.desc()).limit(limit)
            return list(session.execute(stmt).scalars().all())

    def get_for_satellite(self, norad_id: int, limit: int = 50) -> list[Observation]:
        with self._get_session() as session:
            stmt = (
                select(Observation)
                .where(Observation.norad_id == norad_id)
                .order_by(Observation.ts.desc())
                .limit(limit)
            )
            return list(session.execute(stmt).scalars().all())
