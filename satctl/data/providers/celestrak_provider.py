"""Celestrak provider for satellite OSINT records."""

import urllib.request
from datetime import datetime
from typing import List, Tuple

from satctl.data.models import NormalizedSatelliteRecord, NormalizedTLERecord
from .base import BaseProvider


class CelesTrakProvider(BaseProvider):
    """Provider for CelesTrak public satellite tracking elements."""

    SOURCE_NAME = "celestrak"
    
    # Active satellites gives ~10,000+ objects
    URLS = [
        "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle"
    ]

    @property
    def name(self) -> str:
        return self.SOURCE_NAME

    def fetch(self) -> str:
        """Fetch active satellite TLEs directly from CelesTrak."""
        import click
        raw_data = ""
        for url in self.URLS:
            try:
                click.echo(f"  Fetching: {url}...")
                req = urllib.request.Request(url, headers={'User-Agent': 'satctl/1.0'})
                # Use a 20 second timeout to prevent hanging forever
                with urllib.request.urlopen(req, timeout=20) as resp:
                    raw_data += resp.read().decode('utf-8') + "\n"
            except Exception as e:
                click.secho(f"  Error fetching from {url}: {e}", fg="red")
        return raw_data

    def parse(self, raw_data: str) -> List[Tuple[str, str, str]]:
        """Parse raw TLE text into 3-line blocks (name, line1, line2)."""
        lines = [line.strip() for line in raw_data.split('\n') if line.strip()]
        records = []
        for i in range(0, len(lines) - 2, 3):
            name = lines[i]
            line1 = lines[i+1]
            line2 = lines[i+2]
            # Ensure it looks like TLE
            if line1.startswith("1 ") and line2.startswith("2 "):
                records.append((name, line1, line2))
        return records

    def normalize(self, provider_records: List[Tuple[str, str, str]]) -> Tuple[List[NormalizedSatelliteRecord], List[NormalizedTLERecord]]:
        """Normalize into Satellite and TLE models."""
        sats = []
        tles = []
        now = datetime.utcnow()
        seen_norads = set()

        for name, line1, line2 in provider_records:
            try:
                # Parse NORAD ID from line 1
                norad_id = int(line1[2:7])
                
                # Prevent duplicates within CelesTrak if we fetched multiple groups
                if norad_id in seen_norads:
                    continue
                seen_norads.add(norad_id)

                # Create Satellite Metadata
                sats.append(
                    NormalizedSatelliteRecord(
                        norad_id=norad_id,
                        name=name.strip(),
                        source=self.SOURCE_NAME
                    )
                )
                
                # Create TLE data
                tles.append(
                    NormalizedTLERecord(
                        norad_id=norad_id,
                        line1=line1,
                        line2=line2,
                        epoch=now, # Simplified: we assign current time as fetch epoch
                        source=self.SOURCE_NAME
                    )
                )
            except ValueError:
                continue

        return sats, tles
