"""Application service for anomaly intelligence and event management."""

from __future__ import annotations
import logging
from typing import List

from satctl.domain.anomalies.anomaly_engine import AnomalyEngine
from satctl.storage.repos.anomalies_repo import AnomalyRepository
from satctl.domain.models import AnomalyRecord

logger = logging.getLogger(__name__)

class AnomalyService:
    """Orchestrates anomaly detection and storage."""

    def __init__(self, engine: AnomalyEngine, repo: AnomalyRepository):
        self.engine = engine
        self.repo = repo

    def record_anomalies(self, anomalies: List[AnomalyRecord]):
        for anom in anomalies:
            self.repo.record_anomaly(anom)

    def get_recent_alerts(self, hours: int = 48) -> List[AnomalyRecord]:
        # Convert DB models back to domain records if needed, 
        # but for CLI it's fine to return models.
        return self.repo.get_recent(hours)
