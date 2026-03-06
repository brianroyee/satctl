"""SatNOGS transmitter provider."""

from __future__ import annotations

import asyncio
from pathlib import Path

import httpx

from satctl.normalization import TransmitterRecord

SATNOGS_TX_URL = "https://db.satnogs.org/api/transmitters/"


class SatnogsTransmitterProvider:
    def __init__(self, timeout: float = 30.0, retries: int = 1):
        self.timeout = timeout
        self.retries = retries

    async def fetch_transmitters(self, limit: int = 500) -> tuple[list[TransmitterRecord], str | None]:
        params = {"format": "json", "alive": "true"}
        last_error: str | None = None
        for attempt in range(self.retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(SATNOGS_TX_URL, params=params)
                    response.raise_for_status()
                    payload = response.json()
                    records: list[TransmitterRecord] = []
                    for row in payload[:limit]:
                        norad = row.get("norad_cat_id")
                        tx_uuid = row.get("uuid")
                        freq = row.get("downlink_low") or row.get("downlink_high")
                        if norad is None or tx_uuid is None or freq is None:
                            continue
                        records.append(
                            TransmitterRecord(
                                tx_id=str(tx_uuid),
                                norad_id=int(norad),
                                frequency=float(freq),
                                mode=row.get("mode"),
                                bandwidth=float(row["baud"]) if row.get("baud") else None,
                                source="satnogs:transmitters",
                                confidence=0.95,
                            )
                        )
                    return records, None
            except Exception as exc:
                last_error = str(exc)
                if attempt < self.retries:
                    await asyncio.sleep(0.3 * (attempt + 1))
        return [], f"Failed to fetch SatNOGS transmitters: {last_error}"
