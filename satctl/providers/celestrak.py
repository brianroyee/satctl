"""Celestrak provider for satellite orbital data."""

from __future__ import annotations
import urllib.request
from datetime import datetime
from typing import List, Tuple, Any

from satctl.domain.models import SatelliteRecord, TLERecord
from satctl.providers.base import BaseProvider


class CelesTrakProvider(BaseProvider):
    """Provider for CelesTrak public tracking elements."""

    SOURCE_NAME = "celestrak"
    URLS = [
        "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle"
    ]

    @property
    def name(self) -> str:
        return self.SOURCE_NAME

    def fetch(self) -> str:
        raw_data = ""
        for i, url in enumerate(self.URLS):
            # Cache name based on url index
            cache_name = f"celestrak_active_{i}.tle"
            raw_data += self.fetch_with_retry(url, cache_name=cache_name) + "\n"
        return raw_data

    def parse(self, raw_data: str) -> List[Tuple[str, str, str]]:
        lines = [line.strip() for line in raw_data.split('\n') if line.strip()]
        records = []
        for i in range(0, len(lines) - 2, 3):
            name, l1, l2 = lines[i], lines[i+1], lines[i+2]
            if l1.startswith("1 ") and l2.startswith("2 "):
                records.append((name, l1, l2))
        return records

    def normalize(self, provider_records: List[Tuple[str, str, str]]) -> Tuple[List[SatelliteRecord], List[TLERecord]]:
        sats, tles = [], []
        now = datetime.utcnow()
        seen = set()
        for name, l1, l2 in provider_records:
            try:
                nid = int(l1[2:7])
                if nid in seen: continue
                seen.add(nid)

                sats.append(SatelliteRecord(norad_id=nid, name=name.strip(), source=self.name))
                tles.append(TLERecord(norad_id=nid, line1=l1, line2=l2, epoch=now, source=self.name))
            except ValueError: continue
        return sats, tles
