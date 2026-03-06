"""Backward-compatible CelesTrak sync client.

New code should use `satctl.providers.celestrak.CelesTrakProvider` directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from satctl.providers.celestrak import CATALOG_URLS, CelesTrakProvider
from satctl.sync.tle_parser import TLEData


@dataclass
class SyncResult:
    catalog_name: str
    satellites_found: int
    error: str | None = None


class CelesTrakClient:
    def __init__(self, timeout: float = 30.0, retries: int = 2, cache_dir: Path | None = None):
        self.provider = CelesTrakProvider(timeout=timeout, retries=retries, cache_dir=cache_dir)

    async def fetch_catalog(self, catalog_name: str) -> tuple[Iterator[TLEData] | None, str | None]:
        records, error = await self.provider.fetch_catalog(catalog_name)
        tles = (
            TLEData(
                name=rec.name,
                norad_id=rec.norad_id,
                line1=rec.line1,
                line2=rec.line2,
                epoch=rec.epoch,
            )
            for rec in records
        )
        return tles, error


def get_available_catalogs() -> list[str]:
    return list(CATALOG_URLS.keys())
