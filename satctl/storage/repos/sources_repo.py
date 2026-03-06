"""Repository for data source sync state."""

from __future__ import annotations
from datetime import datetime
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.orm import Session

from satctl.storage.models import Source
from satctl.storage.db import get_session


class SourceRepository:
    """Repository for synchronization source state."""

    def __init__(self, db_path: Path):
        self.db_path = db_path

    def _get_session(self) -> Session:
        return get_session(self.db_path)

    def upsert_source(self, name: str, record_count: int, status: str = "OK") -> None:
        """Update or create a source sync record."""
        with self._get_session() as session:
            stmt = select(Source).where(Source.source_name == name)
            source = session.execute(stmt).scalar_one_or_none()
            if source:
                source.last_sync_at = datetime.utcnow()
                source.record_count = record_count
                source.last_status = status
            else:
                source = Source(
                    source_name=name, 
                    last_sync_at=datetime.utcnow(), 
                    record_count=record_count,
                    last_status=status
                )
                session.add(source)
            session.commit()

    def get_all_sources(self) -> list[Source]:
        with self._get_session() as session:
            return list(session.execute(select(Source)).scalars().all())
