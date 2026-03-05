"""Data access layer for satctl database."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterator

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from satctl.database.models import Satellite, TLE, SyncLog
from satctl.database.schema import get_session


class SatelliteRepository:
    """Repository for satellite data operations."""

    def __init__(self, db_path: Path):
        """Initialize the repository.

        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = db_path

    def _get_session(self) -> Session:
        """Get a new database session."""
        return get_session(self.db_path)

    def get_all_satellites(self) -> list[Satellite]:
        """Get all satellites from the database."""
        with self._get_session() as session:
            stmt = select(Satellite)
            return list(session.execute(stmt).scalars().all())

    def get_satellite(self, norad_id: int) -> Satellite | None:
        """Get a satellite by NORAD ID."""
        with self._get_session() as session:
            stmt = select(Satellite).where(Satellite.norad_id == norad_id)
            return session.execute(stmt).scalar_one_or_none()

    def get_satellites_by_name(self, name_pattern: str, limit: int = 100) -> list[Satellite]:
        """Search satellites by name pattern."""
        with self._get_session() as session:
            stmt = (
                select(Satellite)
                .where(Satellite.name.ilike(f"%{name_pattern}%"))
                .limit(limit)
            )
            return list(session.execute(stmt).scalars().all())

    def get_satellite_count(self) -> int:
        """Get the total count of satellites."""
        with self._get_session() as session:
            stmt = select(func.count()).select_from(Satellite)
            return session.execute(stmt).scalar_one()

    def upsert_satellite(self, norad_id: int, name: str, source: str | None = None) -> Satellite:
        """Insert or update a satellite."""
        with self._get_session() as session:
            stmt = select(Satellite).where(Satellite.norad_id == norad_id)
            satellite = session.execute(stmt).scalar_one_or_none()

            if satellite:
                satellite.name = name
                satellite.source = source
                satellite.updated_at = datetime.utcnow()
            else:
                satellite = Satellite(
                    norad_id=norad_id,
                    name=name,
                    source=source,
                )
                session.add(satellite)

            session.commit()
            session.refresh(satellite)
            return satellite


class TLERepository:
    """Repository for TLE data operations."""

    def __init__(self, db_path: Path):
        """Initialize the repository.

        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = db_path

    def _get_session(self) -> Session:
        """Get a new database session."""
        return get_session(self.db_path)

    def get_latest_tle(self, norad_id: int) -> TLE | None:
        """Get the latest TLE for a satellite."""
        with self._get_session() as session:
            stmt = (
                select(TLE)
                .where(TLE.norad_id == norad_id)
                .order_by(TLE.epoch.desc())
                .limit(1)
            )
            return session.execute(stmt).scalar_one_or_none()

    def get_latest_tles(self, norad_ids: list[int]) -> dict[int, TLE]:
        """Get the latest TLE for multiple satellites."""
        if not norad_ids:
            return {}

        with self._get_session() as session:
            # Subquery to get max epoch per norad_id
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

    def get_all_latest_tles(self) -> list[TLE]:
        """Get the latest TLE for all satellites."""
        with self._get_session() as session:
            # Subquery to get max epoch per norad_id
            subquery = (
                select(TLE.norad_id, func.max(TLE.epoch).label("max_epoch"))
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

            return list(session.execute(stmt).scalars().all())

    def upsert_tle(
        self, norad_id: int, epoch: datetime, line1: str, line2: str
    ) -> TLE:
        """Insert or update a TLE record."""
        with self._get_session() as session:
            tle = TLE(
                norad_id=norad_id,
                epoch=epoch,
                line1=line1,
                line2=line2,
            )
            session.add(tle)
            session.commit()
            session.refresh(tle)
            return tle

    def get_tle_count(self) -> int:
        """Get the total count of TLE records."""
        with self._get_session() as session:
            stmt = select(func.count()).select_from(TLE)
            return session.execute(stmt).scalar_one()


class SyncLogRepository:
    """Repository for sync log operations."""

    def __init__(self, db_path: Path):
        """Initialize the repository.

        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = db_path

    def _get_session(self) -> Session:
        """Get a new database session."""
        return get_session(self.db_path)

    def create_sync(self) -> SyncLog:
        """Create a new sync log entry."""
        with self._get_session() as session:
            sync = SyncLog(started_at=datetime.utcnow())
            session.add(sync)
            session.commit()
            session.refresh(sync)
            return sync

    def complete_sync(
        self,
        sync_id: int,
        satellites_added: int = 0,
        satellites_updated: int = 0,
        error_message: str | None = None,
    ) -> SyncLog:
        """Complete a sync log entry."""
        with self._get_session() as session:
            sync = session.get(SyncLog, sync_id)
            if sync:
                sync.completed_at = datetime.utcnow()
                sync.satellites_added = satellites_added
                sync.satellites_updated = satellites_updated
                sync.error_message = error_message
                session.commit()
                session.refresh(sync)
            return sync

    def get_last_sync(self) -> SyncLog | None:
        """Get the last completed sync."""
        with self._get_session() as session:
            stmt = (
                select(SyncLog)
                .where(SyncLog.completed_at.isnot(None))
                .order_by(SyncLog.completed_at.desc())
                .limit(1)
            )
            return session.execute(stmt).scalar_one_or_none()
