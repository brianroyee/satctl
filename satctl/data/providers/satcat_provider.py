"""Satcat provider for satellite metadata using CelesTrak's public SATCAT CSV."""

import csv
import io
import urllib.request
from datetime import datetime
from typing import List, Tuple, Optional

from satctl.data.models import NormalizedSatelliteRecord, NormalizedTLERecord
from .base import BaseProvider


class SatcatProvider(BaseProvider):
    """Provider for CelesTrak's public SATCAT metadata."""

    SOURCE_NAME = "satcat"
    
    # Public SATCAT CSV from CelesTrak
    URL = "https://celestrak.org/pub/satcat.csv"

    @property
    def name(self) -> str:
        return self.SOURCE_NAME

    def fetch(self) -> str:
        """Fetch the public SATCAT CSV."""
        import click
        try:
            click.echo(f"  Fetching: {self.URL}...")
            req = urllib.request.Request(self.URL, headers={'User-Agent': 'satctl/1.0'})
            # Use a 20 second timeout to prevent hanging forever
            with urllib.request.urlopen(req, timeout=20) as resp:
                return resp.read().decode('utf-8')
        except Exception as e:
            click.secho(f"  Error fetching SATCAT from {self.URL}: {e}", fg="red")
            return ""

    def parse(self, raw_data: str) -> List[dict]:
        """Parse the SATCAT CSV data."""
        if not raw_data:
            return []
        
        f = io.StringIO(raw_data)
        reader = csv.DictReader(f)
        return list(reader)

    def normalize(self, provider_records: List[dict]) -> Tuple[List[NormalizedSatelliteRecord], List[NormalizedTLERecord]]:
        """Normalize SATCAT records into unified models."""
        sats = []
        # SATCAT doesn't provide TLEs
        tles = []
        
        for rec in provider_records:
            try:
                norad_id = int(rec.get("NORAD_CAT_ID", 0))
                if not norad_id:
                    continue
                
                # Parse launch date if available
                launch_date = None
                ld_str = rec.get("LAUNCH_DATE")
                if ld_str:
                    try:
                        launch_date = datetime.strptime(ld_str, "%Y-%m-%d")
                    except ValueError:
                        pass

                # Map object type
                # CelesTrak SATCAT uses 'PAY' for payload, 'R/B' for rocket body, 'DEB' for debris
                obj_type_raw = rec.get("OBJECT_TYPE", "").upper()
                obj_type = "other"
                if "PAY" in obj_type_raw:
                    obj_type = "payload"
                elif "R/B" in obj_type_raw:
                    obj_type = "rocket_body"
                elif "DEB" in obj_type_raw:
                    obj_type = "debris"

                sats.append(
                    NormalizedSatelliteRecord(
                        norad_id=norad_id,
                        name=rec.get("OBJECT_NAME", "Unknown"),
                        source=self.SOURCE_NAME,
                        object_type=obj_type,
                        owner_country=rec.get("COUNTRY"),
                        launch_date=launch_date,
                    )
                )
            except Exception:
                continue

        return sats, tles
