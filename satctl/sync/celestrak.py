"""CelesTrak client for downloading TLE data with cache/retry support."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterator

import httpx

from satctl.sync.tle_parser import TLEData, parse_tle_file

CATALOG_URLS = {
    "active": "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle",
    "stations": "https://celestrak.org/NORAD/elements/gp.php?GROUP=stations&FORMAT=tle",
    "weather": "https://celestrak.org/NORAD/elements/gp.php?GROUP=weather&FORMAT=tle",
    "gps": "https://celestrak.org/NORAD/elements/gp.php?GROUP=gps-ops&FORMAT=tle",
    "glo": "https://celestrak.org/NORAD/elements/gp.php?GROUP=glo-ops&FORMAT=tle",
    "galileo": "https://celestrak.org/NORAD/elements/gp.php?GROUP=galileo&FORMAT=tle",
    "beidou": "https://celestrak.org/NORAD/elements/gp.php?GROUP=beidou&FORMAT=tle",
}


@dataclass
class SyncResult:
    catalog_name: str
    satellites_found: int
    error: str | None = None


class CelesTrakClient:
    def __init__(self, timeout: float = 30.0, retries: int = 2, cache_dir: Path | None = None):
        self.timeout = timeout
        self.retries = retries
        self.cache_dir = cache_dir
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, catalog_name: str) -> Path | None:
        if not self.cache_dir:
            return None
        return self.cache_dir / f"{catalog_name}.tle"

    def _read_cache(self, catalog_name: str, max_age_hours: int = 24) -> str | None:
        path = self._cache_path(catalog_name)
        if not path or not path.exists():
            return None
        modified = datetime.utcfromtimestamp(path.stat().st_mtime)
        if datetime.utcnow() - modified > timedelta(hours=max_age_hours):
            return None
        return path.read_text(encoding="utf-8")

    def _write_cache(self, catalog_name: str, content: str) -> None:
        path = self._cache_path(catalog_name)
        if path:
            path.write_text(content, encoding="utf-8")

    async def fetch_catalog(self, catalog_name: str) -> tuple[Iterator[TLEData] | None, str | None]:
        if catalog_name not in CATALOG_URLS:
            return None, f"Unknown catalog: {catalog_name}"

        url = CATALOG_URLS[catalog_name]
        last_error = None

        for attempt in range(self.retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(url)
                    response.raise_for_status()
                    content = response.text
                    if "No data found" in content or len(content) < 100:
                        raise ValueError(f"No data found in catalog: {catalog_name}")
                    self._write_cache(catalog_name, content)
                    return parse_tle_file(content), None
            except Exception as exc:
                last_error = str(exc)
                if attempt < self.retries:
                    await asyncio.sleep(0.25 * (attempt + 1))

        cached = self._read_cache(catalog_name)
        if cached:
            return parse_tle_file(cached), f"Using cached data for {catalog_name} after error: {last_error}"

        return None, f"Error fetching catalog {catalog_name}: {last_error}"


def get_available_catalogs() -> list[str]:
    return list(CATALOG_URLS.keys())
