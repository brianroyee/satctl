"""UCS provider for enriched satellite metadata."""

from __future__ import annotations
from typing import List, Tuple, Any
from satctl.domain.models import SatelliteRecord, TLERecord
from satctl.providers.base import BaseProvider


class UCSProvider(BaseProvider):
    """Placeholder for Union of Concerned Scientists (UCS) database."""

    SOURCE_NAME = "ucs"

    @property
    def name(self) -> str:
        return self.SOURCE_NAME

    def fetch(self) -> str:
        # UCS typically requires Excel or complex CSV parsing
        return ""

    def parse(self, raw_data: str) -> List[Any]:
        return []

    def normalize(self, provider_records: List[Any]) -> Tuple[List[SatelliteRecord], List[TLERecord]]:
        # TODO: Implement once a stable CSV/JSON is identified
        return [], []
