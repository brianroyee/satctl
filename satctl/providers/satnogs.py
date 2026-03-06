"""SatNOGS provider for signal intelligence and transmitter data."""

from __future__ import annotations
from typing import List, Tuple, Any
from satctl.domain.models import SatelliteRecord, TLERecord, TransmitterRecord, ObservationRecord
from satctl.providers.base import BaseProvider


class SatNOGSProvider(BaseProvider):
    """Provider for SatNOGS transmitter and observation metadata."""

    SOURCE_NAME = "satnogs"
    TRANSMITTERS_URL = "https://db.satnogs.org/api/transmitters/?format=json"
    OBSERVATIONS_URL = "https://network.satnogs.org/api/observations/?format=json"

    @property
    def name(self) -> str:
        return self.SOURCE_NAME

    def fetch(self) -> str:
        """Main fetch isn't used as we have specialized methods, but required by API."""
        return self.fetch_transmitters_raw()

    def fetch_transmitters_raw(self) -> str:
        return self.fetch_with_retry(self.TRANSMITTERS_URL, cache_name="satnogs_transmitters.json")

    def fetch_observations_raw(self) -> str:
        return self.fetch_with_retry(self.OBSERVATIONS_URL, cache_name="satnogs_observations.json")

    def parse(self, raw_data: str) -> List[Any]:
        import json
        try:
            return json.loads(raw_data)
        except Exception:
            return []

    def normalize(self, provider_records: List[Any]) -> Tuple[List[SatelliteRecord], List[TLERecord]]:
        # SatNOGS isn't a primary source for Sat/TLE in our system
        return [], []

    def fetch_transmitters(self) -> List[TransmitterRecord]:
        """Fetch known satellite transmitters."""
        raw = self.fetch_transmitters_raw()
        records = self.parse(raw)
        
        normalized = []
        for r in records:
            try:
                nid = r.get("norad_cat_id")
                if not nid: continue
                
                # Frequencies are in Hz
                normalized.append(TransmitterRecord(
                    norad_id=int(nid),
                    name=r.get("description", "Unknown"),
                    description=r.get("citation"),
                    downlink_freq_hz=r.get("downlink_low"),
                    uplink_freq_hz=r.get("uplink_low"),
                    mode=r.get("mode"),
                    bandwidth_hz=r.get("baud"),
                    source=self.name
                ))
            except Exception: continue
        return normalized

    def fetch_observations(self) -> List[ObservationRecord]:
        """Fetch latest signal observations."""
        raw = self.fetch_observations_raw()
        records = self.parse(raw)
        
        normalized = []
        for r in records:
            try:
                nid = r.get("satellite_norad_cat_id")
                if not nid: continue
                
                start_str = r.get("start")
                ts = datetime.utcnow()
                if start_str:
                    try: ts = datetime.strptime(start_str, "%Y-%m-%dT%H:%M:%SZ")
                    except ValueError: pass

                normalized.append(ObservationRecord(
                    ts=ts,
                    norad_id=int(nid),
                    tx_id=None, # Will be matched by SignalsEngine
                    source=self.name,
                    station_id=str(r.get("ground_station")),
                    region_tag=None, # Could be derived from station location
                    metadata={"status": r.get("status"), "obs_id": r.get("id")}
                ))
            except Exception: continue
        return normalized
