"""Repository for anomaly event operations."""

from __future__ import annotations
from datetime import datetime, timedelta
from pathlib import Path
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from satctl.storage.models import Anomaly
from satctl.storage.db import get_session
from satctl.domain.models import AnomalyRecord


class AnomalyRepository:
    """Repository for generated anomalies."""

    def __init__(self, db_path: Path):
        self.db_path = db_path

    def _get_session(self) -> Session:
        return get_session(self.db_path)

    def record_anomaly(self, record: AnomalyRecord) -> None:
        """Store a new anomaly, deduplicating by fingerprint."""
        import json
        with self._get_session() as session:
            # Check for existing fingerprint
            stmt = select(Anomaly).where(Anomaly.fingerprint == record.fingerprint)
            existing = session.execute(stmt).scalar_one_or_none()
            
            if existing:
                # Update timestamp and details if already open
                if existing.status == "OPEN":
                    existing.ts = record.ts
                    existing.details_json = json.dumps(record.details) if record.details else None
                return

            anom = Anomaly(
                ts=record.ts,
                severity=record.severity,
                type=record.type,
                title=record.title,
                norad_id=record.norad_id,
                tx_id=record.tx_id,
                details_json=json.dumps(record.details) if record.details else None,
                fingerprint=record.fingerprint,
                status="OPEN"
            )
            session.add(anom)
            session.commit()

    def get_recent(self, hours: int = 48) -> list[Anomaly]:
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        with self._get_session() as session:
            stmt = (
                select(Anomaly)
                .where(Anomaly.ts >= cutoff)
                .order_by(Anomaly.ts.desc())
            )
            return list(session.execute(stmt).scalars().all())
