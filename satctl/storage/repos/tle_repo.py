"""Repository for TLE data operations."""

from __future__ import annotations
from datetime import datetime
from pathlib import Path
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from satctl.storage.models import TLE
from satctl.storage.db import get_session
from satctl.domain.models import TLERecord


class TLERepository:
    """Repository for TLE data operations."""

    def __init__(self, db_path: Path):
        self.db_path = db_path

    def _get_session(self) -> Session:
        return get_session(self.db_path)

    def get_latest_tle(self, norad_id: int) -> TLE | None:
        with self._get_session() as session:
            stmt = (
                select(TLE)
                .where(TLE.norad_id == norad_id)
                .order_by(TLE.epoch.desc())
                .limit(1)
            )
            return session.execute(stmt).scalar_one_or_none()

    def get_latest_tles(self, norad_ids: list[int]) -> dict[int, TLE]:
        if not norad_ids:
            return {}
        with self._get_session() as session:
            subquery = (
                select(TLE.norad_id, func.max(TLE.epoch).label("max_epoch"))
                .where(TLE.norad_id.in_(norad_ids))
                .group_by(TLE.norad_id)
                .subquery()
            )
            stmt = (
                select(TLE)
                .join(
                    subquery,
                    (TLE.norad_id == subquery.c.norad_id)
                    & (TLE.epoch == subquery.c.max_epoch),
                )
            )
            results = session.execute(stmt).scalars().all()
            return {tle.norad_id: tle for tle in results}

    def get_count(self) -> int:
        with self._get_session() as session:
            return session.execute(select(func.count()).select_from(TLE)).scalar_one()

    def batch_upsert(self, records: list[TLERecord]) -> int:
        """Efficiently insert a batch of TLE records."""
        if not records:
            return 0
        
        count = 0
        with self._get_session() as session:
            chunk_size = 1000
            for i in range(0, len(records), chunk_size):
                chunk = records[i:i + chunk_size]
                for r in chunk:
                    tle = TLE(
                        norad_id=r.norad_id,
                        epoch=r.epoch,
                        line1=r.line1,
                        line2=r.line2,
                        source=r.source
                    )
                    session.add(tle)
                    count += 1
                session.commit()
        return count
