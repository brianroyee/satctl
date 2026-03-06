"""Base provider interface for SIGINT-first satellite OSINT sources."""

from __future__ import annotations
import abc
from typing import List, Tuple, Any

from satctl.domain.models import SatelliteRecord, TLERecord, TransmitterRecord, ObservationRecord


class BaseProvider(abc.ABC):
    """Abstract base class for all satellite intelligence providers."""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Provider identifier name."""
        pass

    @abc.abstractmethod
    def fetch(self) -> str:
        """Fetch raw data from upstream."""
        pass

    def fetch_with_retry(self, url: str, cache_name: str | None = None) -> str:
        """Fetch URL with retries and local cache fallback."""
        import time
        import requests
        import click
        from satctl.config import get_config
        
        config = get_config()
        cache_path = config.cache_dir / cache_name if cache_name else None

        for attempt in range(5):
            try:
                # 120s timeout as suggested by user
                resp = requests.get(url, timeout=(10, 120), headers={'User-Agent': 'satctl/1.0'})
                resp.raise_for_status()
                data = resp.text
                
                if cache_path:
                    cache_path.write_text(data, encoding='utf-8')
                return data
            except Exception as e:
                if attempt == 4:
                    if cache_path and cache_path.exists():
                        click.secho(f"  Fetch failed: {e}. Using cached data.", fg="yellow")
                        return cache_path.read_text(encoding='utf-8')
                    raise e
                
                wait = 2 ** attempt
                click.echo(f"  Fetch failed ({e}). Retrying in {wait}s...")
                time.sleep(wait)
        return ""

    @abc.abstractmethod
    def parse(self, raw_data: str) -> List[Any]:
        """Parse raw data into provider-specific records."""
        pass

    @abc.abstractmethod
    def normalize(self, provider_records: List[Any]) -> Tuple[List[SatelliteRecord], List[TLERecord]]:
        """Convert to unified domain models."""
        pass

    def run_pipeline(self) -> Tuple[List[SatelliteRecord], List[TLERecord]]:
        raw = self.fetch()
        parsed = self.parse(raw)
        return self.normalize(parsed)
