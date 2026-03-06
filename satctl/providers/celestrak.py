"""CelesTrak provider with retry and cache fallback."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from pathlib import Path

import httpx

from satctl.normalization import TLERecord
from satctl.sync.tle_parser import parse_tle_file

CATALOG_URLS = {
    "active": "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle",
    "stations": "https://celestrak.org/NORAD/elements/gp.php?GROUP=stations&FORMAT=tle",
    "weather": "https://celestrak.org/NORAD/elements/gp.php?GROUP=weather&FORMAT=tle",
    "gps": "https://celestrak.org/NORAD/elements/gp.php?GROUP=gps-ops&FORMAT=tle",
    "glo": "https://celestrak.org/NORAD/elements/gp.php?GROUP=glo-ops&FORMAT=tle",
    "galileo": "https://celestrak.org/NORAD/elements/gp.php?GROUP=galileo&FORMAT=tle",
    "beidou": "https://celestrak.org/NORAD/elements/gp.php?GROUP=beidou&FORMAT=tle",
}


class CelesTrakProvider:
    def __init__(self, timeout: float = 30.0, retries: int = 2, cache_dir: Path | None = None):
        self.timeout = timeout
        self.retries = retries
        self.cache_dir = cache_dir
        if cache_dir:
            cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, catalog: str) -> Path | None:
        if not self.cache_dir:
            return None
        return self.cache_dir / f"celestrak_{catalog}.tle"

    def _read_cache(self, catalog: str, max_age_hours: int = 24) -> str | None:
        path = self._cache_path(catalog)
        if not path or not path.exists():
            return None
        modified = datetime.utcfromtimestamp(path.stat().st_mtime)
        if datetime.utcnow() - modified > timedelta(hours=max_age_hours):
            return None
        return path.read_text(encoding="utf-8")

    def _write_cache(self, catalog: str, content: str) -> None:
        path = self._cache_path(catalog)
        if path:
            path.write_text(content, encoding="utf-8")

    async def fetch_catalog(self, catalog: str) -> tuple[list[TLERecord], str | None]:
        if catalog not in CATALOG_URLS:
            return [], f"Unknown catalog: {catalog}"

        url = CATALOG_URLS[catalog]
        last_error: str | None = None

        for attempt in range(self.retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(url)
                    response.raise_for_status()
                    content = response.text
                    if "No data found" in content or len(content) < 100:
                        raise ValueError(f"No data found in catalog: {catalog}")
                    self._write_cache(catalog, content)
                    tles = [
                        TLERecord(
                            norad_id=item.norad_id,
                            name=item.name,
                            line1=item.line1,
                            line2=item.line2,
                            epoch=item.epoch,
                            source=f"celestrak:{catalog}",
                        )
                        for item in parse_tle_file(content)
                    ]
                    return tles, None
            except Exception as exc:  # Provider failure should never crash sync.
                last_error = str(exc)
                if attempt < self.retries:
                    await asyncio.sleep(0.3 * (attempt + 1))

        cached = self._read_cache(catalog)
        if cached:
            tles = [
                TLERecord(
                    norad_id=item.norad_id,
                    name=item.name,
                    line1=item.line1,
                    line2=item.line2,
                    epoch=item.epoch,
                    source=f"celestrak:{catalog}:cache",
                )
                for item in parse_tle_file(cached)
            ]
            return tles, f"Using cached CelesTrak data for {catalog} after error: {last_error}"

        return [], f"Failed to fetch CelesTrak {catalog}: {last_error}"
