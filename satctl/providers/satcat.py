"""Satcat provider for global satellite catalog metadata."""

from __future__ import annotations
import csv
import io
import urllib.request
from datetime import datetime
from typing import List, Tuple, Any

from satctl.domain.models import SatelliteRecord, TLERecord
from satctl.providers.base import BaseProvider


class SatcatProvider(BaseProvider):
    """Provider for official satellite catalog intelligence."""

    SOURCE_NAME = "satcat"
    URL = "https://celestrak.org/pub/satcat.csv"

    @property
    def name(self) -> str:
        return self.SOURCE_NAME

    def fetch(self) -> str:
        return self.fetch_with_retry(self.URL, cache_name="satcat.csv")

    def parse(self, raw_data: str) -> List[dict]:
        if not raw_data: return []
        f = io.StringIO(raw_data)
        return list(csv.DictReader(f))

    def normalize(self, provider_records: List[dict]) -> Tuple[List[SatelliteRecord], List[TLERecord]]:
        sats = []
        for rec in provider_records:
            try:
                nid = int(rec.get("NORAD_CAT_ID", 0))
                if not nid: continue
                
                ld = None
                ld_str = rec.get("LAUNCH_DATE")
                if ld_str:
                    try: ld = datetime.strptime(ld_str, "%Y-%m-%d")
                    except ValueError: pass

                raw_type = rec.get("OBJECT_TYPE", "").upper()
                obj_type = "UNKNOWN"
                if "PAY" in raw_type: obj_type = "PAYLOAD"
                elif "R/B" in raw_type: obj_type = "ROCKET_BODY"
                elif "DEB" in raw_type: obj_type = "DEBRIS"

                sats.append(SatelliteRecord(
                    norad_id=nid,
                    name=rec.get("OBJECT_NAME", "Unknown"),
                    source=self.name,
                    object_type=obj_type,
                    owner_code=rec.get("COUNTRY"),
                    launch_date=ld
                ))
            except Exception: continue
        return sats, []
