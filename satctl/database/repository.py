"""Data access layer for satctl database."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from satctl.database.models import Satellite, TLE, SyncLog, Transmitter, Observation, Anomaly
from satctl.database.schema import get_session


class BaseRepository:
    def __init__(self, db_path: Path):
        self.db_path = db_path

    def _get_session(self) -> Session:
        return get_session(self.db_path)


class SatelliteRepository(BaseRepository):
    """Repository for satellite data operations."""

    def get_all_satellites(self) -> list[Satellite]:
        with self._get_session() as session:
            return list(session.execute(select(Satellite)).scalars().all())

    def get_satellite(self, norad_id: int) -> Satellite | None:
        with self._get_session() as session:
            return session.execute(select(Satellite).where(Satellite.norad_id == norad_id)).scalar_one_or_none()

    def get_satellites_by_name(self, name_pattern: str, limit: int = 100) -> list[Satellite]:
        with self._get_session() as session:
            stmt = select(Satellite).where(Satellite.name.ilike(f"%{name_pattern}%")).limit(limit)
            return list(session.execute(stmt).scalars().all())

    def get_satellite_count(self) -> int:
        with self._get_session() as session:
            return session.execute(select(func.count()).select_from(Satellite)).scalar_one()

    def upsert_satellite(self, norad_id: int, name: str, source: str | None = None) -> Satellite:
        with self._get_session() as session:
            satellite = session.execute(select(Satellite).where(Satellite.norad_id == norad_id)).scalar_one_or_none()
            if satellite:
                satellite.name = name
                satellite.source = source
                satellite.last_seen_at = datetime.utcnow()
                satellite.updated_at = datetime.utcnow()
            else:
                satellite = Satellite(norad_id=norad_id, name=name, source=source, last_seen_at=datetime.utcnow())
                session.add(satellite)

            session.commit()
            session.refresh(satellite)
            return satellite


class TLERepository(BaseRepository):
    """Repository for TLE data operations."""

    def get_latest_tle(self, norad_id: int) -> TLE | None:
        with self._get_session() as session:
            stmt = select(TLE).where(TLE.norad_id == norad_id).order_by(TLE.epoch.desc()).limit(1)
            return session.execute(stmt).scalar_one_or_none()

    def get_all_latest_tles(self) -> list[TLE]:
        with self._get_session() as session:
            subquery = select(TLE.norad_id, func.max(TLE.epoch).label("max_epoch")).group_by(TLE.norad_id).subquery()
            stmt = select(TLE).join(subquery, (TLE.norad_id == subquery.c.norad_id) & (TLE.epoch == subquery.c.max_epoch))
            return list(session.execute(stmt).scalars().all())

    def upsert_tle(self, norad_id: int, epoch: datetime, line1: str, line2: str, source: str | None = None) -> TLE:
        with self._get_session() as session:
            tle = TLE(norad_id=norad_id, epoch=epoch, line1=line1, line2=line2, source=source)
            session.add(tle)
            session.commit()
            session.refresh(tle)
            return tle

    def get_tle_count(self) -> int:
        with self._get_session() as session:
            return session.execute(select(func.count()).select_from(TLE)).scalar_one()


class SignalRepository(BaseRepository):
    """Repository for signal intelligence operations."""

    def upsert_transmitter(
        self,
        tx_id: str,
        norad_id: int,
        frequency: float,
        mode: str | None = None,
        bandwidth: float | None = None,
        source: str = "derived",
        confidence: float = 0.5,
    ) -> Transmitter:
        now = datetime.utcnow()
        with self._get_session() as session:
            tx = session.get(Transmitter, tx_id)
            if tx:
                tx.frequency = frequency
                tx.mode = mode
                tx.bandwidth = bandwidth
                tx.last_seen = now
                tx.source = source
                tx.confidence = confidence
            else:
                tx = Transmitter(
                    tx_id=tx_id,
                    norad_id=norad_id,
                    frequency=frequency,
                    mode=mode,
                    bandwidth=bandwidth,
                    first_seen=now,
                    last_seen=now,
                    source=source,
                    confidence=confidence,
                )
                session.add(tx)
            session.commit()
            session.refresh(tx)
            return tx

    def add_observation(
        self,
        norad_id: int,
        tx_id: str | None,
        region: str | None,
        station_id: str | None = None,
        source: str = "derived",
        metadata: str | None = None,
    ) -> Observation:
        with self._get_session() as session:
            obs = Observation(
                norad_id=norad_id,
                tx_id=tx_id,
                region=region,
                station_id=station_id,
                source=source,
                raw_metadata=metadata,
            )
            session.add(obs)
            session.commit()
            session.refresh(obs)
            return obs

    def get_signal_activity(self, hours: int = 24) -> list[tuple[int, int]]:
        window_start = datetime.utcnow() - timedelta(hours=hours)
        with self._get_session() as session:
            stmt = (
                select(Observation.norad_id, func.count(Observation.obs_id).label("count"))
                .where(Observation.timestamp >= window_start)
                .group_by(Observation.norad_id)
                .order_by(func.count(Observation.obs_id).desc())
            )
            return [(row[0], row[1]) for row in session.execute(stmt).all()]


class AnomalyRepository(BaseRepository):
    def create_anomaly(
        self,
        anomaly_type: str,
        description: str,
        severity: str = "medium",
        norad_id: int | None = None,
        tx_id: str | None = None,
        region: str | None = None,
    ) -> Anomaly:
        with self._get_session() as session:
            anomaly = Anomaly(
                type=anomaly_type,
                description=description,
                severity=severity,
                norad_id=norad_id,
                tx_id=tx_id,
                region=region,
            )
            session.add(anomaly)
            session.commit()
            session.refresh(anomaly)
            return anomaly

    def list_recent(self, limit: int = 50, status: str | None = None) -> list[Anomaly]:
        with self._get_session() as session:
            stmt = select(Anomaly).order_by(Anomaly.timestamp.desc()).limit(limit)
            if status:
                stmt = stmt.where(Anomaly.status == status)
            return list(session.execute(stmt).scalars().all())


class SyncLogRepository(BaseRepository):
    def create_sync(self) -> SyncLog:
        with self._get_session() as session:
            sync = SyncLog(started_at=datetime.utcnow())
            session.add(sync)
            session.commit()
            session.refresh(sync)
            return sync

    def complete_sync(self, sync_id: int, satellites_added: int = 0, satellites_updated: int = 0, error_message: str | None = None) -> SyncLog | None:
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
        with self._get_session() as session:
            stmt = select(SyncLog).where(SyncLog.completed_at.isnot(None)).order_by(SyncLog.completed_at.desc()).limit(1)
            return session.execute(stmt).scalar_one_or_none()
