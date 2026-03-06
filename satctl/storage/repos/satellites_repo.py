"""Repository for satellite catalog operations."""

from __future__ import annotations
from datetime import datetime
from pathlib import Path
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from satctl.storage.models import Satellite
from satctl.storage.db import get_session
from satctl.domain.models import SatelliteRecord


class SatelliteRepository:
    """Repository for satellite catalog data."""

    def __init__(self, db_path: Path):
        self.db_path = db_path

    def _get_session(self) -> Session:
        return get_session(self.db_path)

    def get_all_satellites(self, limit: int | None = None) -> list[Satellite]:
        with self._get_session() as session:
            stmt = select(Satellite)
            if limit:
                stmt = stmt.limit(limit)
            return list(session.execute(stmt).scalars().all())

    def get_satellite(self, norad_id: int) -> Satellite | None:
        with self._get_session() as session:
            stmt = select(Satellite).where(Satellite.norad_id == norad_id)
            return session.execute(stmt).scalar_one_or_none()

    def get_satellites_by_name(self, name_pattern: str, limit: int = 100) -> list[Satellite]:
        with self._get_session() as session:
            stmt = (
                select(Satellite)
                .where(Satellite.name.ilike(f"%{name_pattern}%"))
                .limit(limit)
            )
            return list(session.execute(stmt).scalars().all())

    def get_count(self) -> int:
        with self._get_session() as session:
            return session.execute(select(func.count()).select_from(Satellite)).scalar_one()

    def batch_upsert(self, records: list[SatelliteRecord]) -> int:
        """Efficiently upsert a batch of satellites."""
        if not records:
            return 0
        
        updated_count = 0
        with self._get_session() as session:
            chunk_size = 1000
            for i in range(0, len(records), chunk_size):
                chunk = records[i:i + chunk_size]
                norad_ids = [r.norad_id for r in chunk]
                
                stmt = select(Satellite).where(Satellite.norad_id.in_(norad_ids))
                existing = {s.norad_id: s for s in session.execute(stmt).scalars().all()}
                
                for r in chunk:
                    if r.norad_id in existing:
                        s = existing[r.norad_id]
                        s.name = r.name
                        s.source = r.source
                        s.object_type = r.object_type
                        s.owner_code = r.owner_code
                        s.owner_name = r.owner_name
                        s.operator = r.operator
                        s.orbit_class = r.orbit_class
                        s.launch_date = r.launch_date
                        s.updated_at = datetime.utcnow()
                    else:
                        s = Satellite(
                            norad_id=r.norad_id,
                            name=r.name,
                            source=r.source,
                            object_type=r.object_type,
                            owner_code=r.owner_code,
                            owner_name=r.owner_name,
                            operator=r.operator,
                            orbit_class=r.orbit_class,
                            launch_date=r.launch_date
                        )
                        session.add(s)
                    updated_count += 1
                
                session.commit()
        return updated_count
