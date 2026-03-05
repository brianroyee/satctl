"""CelesTrak client for downloading TLE data."""

from __future__ import annotations

import httpx
from dataclasses import dataclass
from typing import Iterator

from satctl.sync.tle_parser import TLEData, parse_tle_file


# CelesTrak catalog URLs
CATALOG_URLS = {
    "active": "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle",
    "analyst": "https://celestrak.org/NORAD/elements/gp.php?GROUP=analyst&FORMAT=tle",
    "visual": "https://celestrak.org/NORAD/elements/gp.php?GROUP=visual&FORMAT=tle",
    "stations": "https://celestrak.org/NORAD/elements/gp.php?GROUP=stations&FORMAT=tle",
    "weather": "https://celestrak.org/NORAD/elements/gp.php?GROUP=weather&FORMAT=tle",
    "noaa": "https://celestrak.org/NORAD/elements/gp.php?GROUP=noaa&FORMAT=tle",
    "goes": "https://celestrak.org/NORAD/elements/gp.php?GROUP=goes&FORMAT=tle",
    "resource": "https://celestrak.org/NORAD/elements/gp.php?GROUP=resource&FORMAT=tle",
    "sarsat": "https://celestrak.org/NORAD/elements/gp.php?GROUP=sarsat&FORMAT=tle",
    "dmc": "https://celestrak.org/NORAD/elements/gp.php?GROUP=dmc&FORMAT=tle",
    "tdrss": "https://celestrak.org/NORAD/elements/gp.php?GROUP=tdrss&FORMAT=tle",
    "gps": "https://celestrak.org/NORAD/elements/gp.php?GROUP=gps-ops&FORMAT=tle",
    "glo": "https://celestrak.org/NORAD/elements/gp.php?GROUP=glo-ops&FORMAT=tle",
    "galileo": "https://celestrak.org/NORAD/elements/gp.php?GROUP=galileo&FORMAT=tle",
    "beidou": "https://celestrak.org/NORAD/elements/gp.php?GROUP=beidou&FORMAT=tle",
    "irnss": "https://celestrak.org/NORAD/elements/gp.php?GROUP=irnss&FORMAT=tle",
    "sbas": "https://celestrak.org/NORAD/elements/gp.php?GROUP=sbas&FORMAT=tle",
    "misc": "https://celestrak.org/NORAD/elements/gp.php?GROUP=misc&FORMAT=tle",
    "tle-new": "https://celestrak.org/NORAD/elements/gp.php?GROUP=tle-new&FORMAT=tle",
}


@dataclass
class SyncResult:
    """Result of a sync operation."""

    catalog_name: str
    satellites_found: int
    error: str | None = None


class CelesTrakClient:
    """Client for downloading TLE data from CelesTrak."""

    def __init__(self, timeout: float = 30.0):
        """Initialize the client.

        Args:
            timeout: HTTP request timeout in seconds.
        """
        self.timeout = timeout

    async def fetch_catalog(
        self, catalog_name: str
    ) -> tuple[Iterator[TLEData] | None, str | None]:
        """Fetch TLE data from a specific catalog.

        Args:
            catalog_name: Name of the catalog to fetch.

        Returns:
            Tuple of (iterator of TLE data, error message).
        """
        if catalog_name not in CATALOG_URLS:
            return None, f"Unknown catalog: {catalog_name}"

        url = CATALOG_URLS[catalog_name]

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                response.raise_for_status()

                content = response.text

                # Check if we got an error page
                if "No data found" in content or len(content) < 100:
                    return None, f"No data found in catalog: {catalog_name}"

                # Parse TLE data
                tle_iter = parse_tle_file(content)
                return tle_iter, None

        except httpx.TimeoutException:
            return None, f"Timeout fetching catalog: {catalog_name}"
        except httpx.HTTPError as e:
            return None, f"HTTP error fetching catalog {catalog_name}: {e}"
        except Exception as e:
            return None, f"Error fetching catalog {catalog_name}: {e}"

    async def fetch_all_catalogs(
        self, catalogs: list[str] | None = None
    ) -> list[SyncResult]:
        """Fetch TLE data from multiple catalogs.

        Args:
            catalogs: List of catalog names to fetch. If None, fetch all.

        Returns:
            List of sync results.
        """
        if catalogs is None:
            catalogs = list(CATALOG_URLS.keys())

        results = []

        for catalog_name in catalogs:
            tle_iter, error = await self.fetch_catalog(catalog_name)

            if error:
                results.append(
                    SyncResult(
                        catalog_name=catalog_name,
                        satellites_found=0,
                        error=error,
                    )
                )
            else:
                count = 0
                if tle_iter:
                    for _ in tle_iter:
                        count += 1

                results.append(
                    SyncResult(
                        catalog_name=catalog_name,
                        satellites_found=count,
                        error=None,
                    )
                )

        return results


def get_available_catalogs() -> list[str]:
    """Get list of available CelesTrak catalogs.

    Returns:
        List of catalog names.
    """
    return list(CATALOG_URLS.keys())
