"""Repository for catalog discovery events."""

from __future__ import annotations
from datetime import datetime, timedelta
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.orm import Session

from satctl.storage.models import CatalogEvent
from satctl.storage.db import get_session


class CatalogEventRepository:
    """Repository for tracking catalog changes and discoveries."""

    def __init__(self, db_path: Path):
        self.db_path = db_path

    def _get_session(self) -> Session:
        return get_session(self.db_path)

    def record_event(self, norad_id: int, event_type: str, source: str | None = None) -> None:
        """Record a new catalog event."""
        with self._get_session() as session:
            event = CatalogEvent(
                norad_id=norad_id,
                event_type=event_type,
                source=source,
                timestamp=datetime.utcnow()
            )
            session.add(event)
            session.commit()

    def get_recent_events(self, hours: int = 48) -> list[CatalogEvent]:
        """Retrieve recent catalog events."""
        since = datetime.utcnow() - timedelta(hours=hours)
        with self._get_session() as session:
            stmt = (
                select(CatalogEvent)
                .where(CatalogEvent.timestamp >= since)
                .order_by(CatalogEvent.timestamp.desc())
            )
            return list(session.execute(stmt).scalars().all())
