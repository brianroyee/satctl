"""SatNOGS observations provider (best-effort)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

import httpx

from satctl.normalization import ObservationRecord

SATNOGS_OBS_URL = "https://network.satnogs.org/api/observations/"


class SatnogsObservationProvider:
    def __init__(self, timeout: float = 30.0, retries: int = 1):
        self.timeout = timeout
        self.retries = retries

    async def fetch_recent_observations(self, limit: int = 500) -> tuple[list[ObservationRecord], str | None]:
        params = {
            "format": "json",
            "status": "good",
            "start": (datetime.utcnow() - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        last_error: str | None = None
        for attempt in range(self.retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(SATNOGS_OBS_URL, params=params)
                    response.raise_for_status()
                    payload = response.json()
                    records: list[ObservationRecord] = []
                    for row in payload[:limit]:
                        norad = row.get("norad_cat_id")
                        if norad is None:
                            continue
                        records.append(
                            ObservationRecord(
                                norad_id=int(norad),
                                tx_id=str(row.get("transmitter_uuid")) if row.get("transmitter_uuid") else None,
                                source="satnogs:observations",
                                station_id=str(row.get("ground_station")) if row.get("ground_station") else None,
                                metadata=f"observation_id={row.get('id')}",
                            )
                        )
                    return records, None
            except Exception as exc:
                last_error = str(exc)
                if attempt < self.retries:
                    await asyncio.sleep(0.3 * (attempt + 1))
        return [], f"Failed to fetch SatNOGS observations: {last_error}"
