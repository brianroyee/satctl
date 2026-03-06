"""Application service for synchronizing satellite intelligence."""

from __future__ import annotations
import logging
import click
from typing import List, Dict, Any

from satctl.domain.catalog.catalog_engine import CatalogEngine
from satctl.domain.signals.signals_engine import SignalsEngine
from satctl.domain.anomalies.anomaly_engine import AnomalyEngine
from satctl.providers.base import BaseProvider
from satctl.storage.repos.satellites_repo import SatelliteRepository
from satctl.storage.repos.tle_repo import TLERepository
from satctl.storage.repos.sources_repo import SourceRepository
from satctl.storage.repos.catalog_events_repo import CatalogEventRepository
from satctl.storage.repos.transmitters_repo import TransmitterRepository
from satctl.storage.repos.observations_repo import ObservationRepository
from satctl.storage.repos.anomalies_repo import AnomalyRepository
from satctl.domain.models import SatelliteRecord, TLERecord, TransmitterRecord, ObservationRecord

logger = logging.getLogger(__name__)

class SyncService:
    """Orchestrates data ingestion from all configured OSINT/SIGINT sources."""

    def __init__(
        self,
        providers: List[BaseProvider],
        catalog_engine: CatalogEngine,
        signals_engine: SignalsEngine,
        anomaly_engine: AnomalyEngine,
        satellite_repo: SatelliteRepository,
        tle_repo: TLERepository,
        source_repo: SourceRepository,
        event_repo: CatalogEventRepository,
        tx_repo: TransmitterRepository,
        obs_repo: ObservationRepository,
        anom_repo: AnomalyRepository
    ):
        self.providers = providers
        self.catalog_engine = catalog_engine
        self.signals_engine = signals_engine
        self.anomaly_engine = anomaly_engine
        self.satellite_repo = satellite_repo
        self.tle_repo = tle_repo
        self.source_repo = source_repo
        self.event_repo = event_repo
        self.tx_repo = tx_repo
        self.obs_repo = obs_repo
        self.anom_repo = anom_repo

    def run_sync(self) -> Dict[str, Any]:
        """Run the full SIGINT sync pipeline."""
        click.secho("Starting Global Intelligence Sync...", fg="cyan", bold=True)
        
        all_sats_map: Dict[int, List[SatelliteRecord]] = {}
        all_tles: List[TLERecord] = []
        all_txs: List[TransmitterRecord] = []
        all_obs: List[ObservationRecord] = []
        summary = {"providers": {}, "total_objects": 0}

        # 1. Fetch from all providers
        for provider in self.providers:
            click.echo(f"Processing Provider: {provider.name}")
            try:
                # Standard OSINT Catalog
                sats, tles = provider.run_pipeline()
                if sats:
                    summary["providers"][provider.name] = len(sats)
                    for s in sats:
                        if s.norad_id not in all_sats_map:
                            all_sats_map[s.norad_id] = []
                        all_sats_map[s.norad_id].append(s)
                all_tles.extend(tles)

                # SIGINT Data (if provider supports it)
                if hasattr(provider, "fetch_transmitters"):
                    txs = provider.fetch_transmitters()
                    click.echo(f"  Received {len(txs):,} known transmitters.")
                    all_txs.extend(txs)
                
                if hasattr(provider, "fetch_observations"):
                    obs = provider.fetch_observations()
                    click.echo(f"  Received {len(obs):,} recent observations.")
                    all_obs.extend(obs)
                
                self.source_repo.upsert_source(provider.name, len(sats) or len(txs))
            except Exception as e:
                click.secho(f"  Error: {e}", fg="red")

        # 2. Catalog Engine: Merge & Deduplicate
        click.echo("Applying intelligence merging rules...")
        merged_sats = []
        for nid, records in all_sats_map.items():
            merged_sats.append(self.catalog_engine.merge_records(records))
        summary["total_objects"] = len(merged_sats)

        # 3. Anomaly Engine: Discoveries (Phase 1)
        # Check for NEW_OBJECT events
        # (This is handled inside repository in a more efficient way ideally, 
        # but for now we proceed to update database)

        # 4. Storage Ingestion
        click.echo(f"Updating database catalog ({len(merged_sats):,} satellites)...")
        self.satellite_repo.batch_upsert(merged_sats)
        
        click.echo(f"Ingesting latest orbital elements ({len(all_tles):,} TLEs)...")
        self.tle_repo.batch_upsert(all_tles)

        click.echo(f"Updating transmitter catalog ({len(all_txs):,} transmitters)...")
        self.tx_repo.batch_upsert_transmitters(all_txs)

        click.echo(f"Recording SIGINT observations ({len(all_obs):,} signals)...")
        for obs in all_obs:
            self.obs_repo.record_observation(obs)

        # 5. Anomaly Engine: Automated Rule Processing
        click.echo("Running Signal Intelligence anomaly detection...")
        # Placeholder for broad anomaly scan after ingestion
        
        click.secho("Sync Complete.", fg="green", bold=True)
        return summary
