"""Controller for the satellite intelligence ingestion pipeline."""

import logging
from typing import List, Dict, Tuple
from datetime import datetime

from satctl.data.providers.base import BaseProvider
from satctl.data.models import NormalizedSatelliteRecord, NormalizedTLERecord
from satctl.database.repository import SatelliteRepository, TLERepository, SourceRepository, CatalogEventRepository

logger = logging.getLogger(__name__)

class IngestionPipeline:
    """Orchestrates the fetch -> normalize -> deduplicate -> store pipeline."""

    def __init__(
        self, 
        satellite_repo: SatelliteRepository, 
        tle_repo: TLERepository,
        source_repo: SourceRepository,
        event_repo: CatalogEventRepository
    ):
        self.satellite_repo = satellite_repo
        self.tle_repo = tle_repo
        self.source_repo = source_repo
        self.event_repo = event_repo
        self.providers: List[BaseProvider] = []
        
        # Priority map for deduplication (lower is higher priority)
        self.priority = {
            "spacetrack": 1,
            "satcat": 2,
            "ucs": 3,
            "celestrak": 4
        }

    def register_provider(self, provider: BaseProvider):
        """Register a data provider."""
        self.providers.append(provider)

    def run(self) -> Dict[str, int]:
        """Run the full sync across all registered providers."""
        all_sats: Dict[int, List[NormalizedSatelliteRecord]] = {}
        all_tles: List[NormalizedTLERecord] = []
        
        summary = {
            "total_objects": 0,
            "new_satellites": 0,
            "tle_records": 0,
            "providers": {}
        }

        # 1. Fetch from all providers
        import click
        for provider in self.providers:
            click.echo(f"Processing Provider: {provider.name}")
            try:
                sats, tles = provider.run_pipeline()
                click.echo(f"  Received {len(sats):,} satellites and {len(tles):,} TLEs.")
                
                summary["providers"][provider.name] = len(sats)
                
                for sat in sats:
                    if sat.norad_id not in all_sats:
                        all_sats[sat.norad_id] = []
                    all_sats[sat.norad_id].append(sat)
                
                all_tles.extend(tles)
                
                # Update source tracking
                self.source_repo.upsert_source(provider.name, len(sats))
                
            except Exception as e:
                click.secho(f"  Error running provider {provider.name}: {e}", fg="red")

        # 2. Deduplicate and Merge Satellites
        click.echo("Merging and deduplicating records...")
        merged_sats = self._merge_satellites(all_sats)
        summary["total_objects"] = len(merged_sats)

        # 3. Detect New Satellites
        click.echo("Checking for new satellite discoveries...")
        # Load all existing NORAD IDs to check for new ones
        existing_norads = set()
        try:
            # Efficiently get all IDs (could be 30k, so we just want the IDs)
            # For simplicity, we'll use get_all_satellites and map ID
            # In a very large DB, we'd add a get_all_norad_ids method
            existing = self.satellite_repo.get_all_satellites()
            existing_norads = {s.norad_id for s in existing}
        except Exception as e:
            logger.error(f"Error loading existing satellites: {e}")

        new_objects = []
        to_upsert = []
        for norad_id, sat in merged_sats.items():
            to_upsert.append(sat)
            if norad_id not in existing_norads:
                new_objects.append(sat)
                self.event_repo.record_event(norad_id, "NEW_OBJECT", sat.source)
        
        summary["new_satellites"] = len(new_objects)

        # 4. Batch Store
        click.echo(f"Updating database catalog ({len(to_upsert):,} objects)...")
        self.satellite_repo.batch_upsert(to_upsert)
        
        click.echo(f"Ingesting latest orbital elements ({len(all_tles):,} TLEs)...")
        summary["tle_records"] = self.tle_repo.batch_upsert(all_tles)

        return summary

    def _merge_satellites(self, all_sats: Dict[int, List[NormalizedSatelliteRecord]]) -> Dict[int, NormalizedSatelliteRecord]:
        """Merge metadata from multiple sources based on priority."""
        merged: Dict[int, NormalizedSatelliteRecord] = {}
        
        for norad_id, records in all_sats.items():
            # Sort records by provider priority
            records.sort(key=lambda x: self.priority.get(x.source, 99))
            
            # Start with the highest priority record
            base = records[0]
            
            # Merge fields from other records if they are missing in base
            for extra in records[1:]:
                if not base.object_type: base.object_type = extra.object_type
                if not base.owner_country: base.owner_country = extra.owner_country
                if not base.operator: base.operator = extra.operator
                if not base.launch_date: base.launch_date = extra.launch_date
                if not base.launch_vehicle: base.launch_vehicle = extra.launch_vehicle
                if not base.purpose: base.purpose = extra.purpose
                if not base.mass: base.mass = extra.mass
            
            merged[norad_id] = base
            
        return merged
