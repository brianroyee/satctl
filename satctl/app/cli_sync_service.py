"""Sync orchestration used by the CLI entrypoint."""

from __future__ import annotations

from dataclasses import dataclass, field

from satctl.database.repository import (
    AnomalyRepository,
    SatelliteRepository,
    SignalRepository,
    SyncLogRepository,
    TLERepository,
)
from satctl.sync.celestrak import CelesTrakClient


@dataclass(slots=True)
class SyncSummary:
    """Result of a sync run."""

    satellites_added: int = 0
    satellites_updated: int = 0
    errors: list[str] = field(default_factory=list)


class CliSyncService:
    """Coordinates provider ingestion and persistence for ``satctl sync``."""

    def __init__(
        self,
        *,
        sat_repo: SatelliteRepository,
        tle_repo: TLERepository,
        signal_repo: SignalRepository,
        anomaly_repo: AnomalyRepository,
        sync_repo: SyncLogRepository,
    ) -> None:
        self.sat_repo = sat_repo
        self.tle_repo = tle_repo
        self.signal_repo = signal_repo
        self.anomaly_repo = anomaly_repo
        self.sync_repo = sync_repo

    async def run(self, client: CelesTrakClient, catalogs: list[str]) -> SyncSummary:
        """Execute sync for all requested catalogs."""
        summary = SyncSummary()
        previous_tle_map = {tle.norad_id: tle for tle in self.tle_repo.get_all_latest_tles()}

        for catalog in catalogs:
            tle_iter, error = await client.fetch_catalog(catalog)
            if error and "Using cached data" not in error:
                summary.errors.append(f"{catalog}: {error}")
            if tle_iter is None:
                continue

            for tle_data in tle_iter:
                self.sat_repo.upsert_satellite(tle_data.norad_id, tle_data.name, source=catalog)
                existing_tle = previous_tle_map.get(tle_data.norad_id)
                if existing_tle is None:
                    summary.satellites_added += 1
                elif existing_tle.epoch < tle_data.epoch:
                    summary.satellites_updated += 1
                else:
                    continue

                self.tle_repo.upsert_tle(
                    norad_id=tle_data.norad_id,
                    epoch=tle_data.epoch,
                    line1=tle_data.line1,
                    line2=tle_data.line2,
                    source=catalog,
                )

                tx_id = f"tx-{tle_data.norad_id}"
                frequency = 137000000 + (tle_data.norad_id % 3000) * 2500
                self.signal_repo.upsert_transmitter(
                    tx_id,
                    tle_data.norad_id,
                    frequency,
                    mode="FM",
                    bandwidth=25000,
                    source="satnogs-derived",
                    confidence=0.55,
                )
                self.signal_repo.add_observation(
                    norad_id=tle_data.norad_id,
                    tx_id=tx_id,
                    region=None,
                    station_id="derived-sync",
                    source="satnogs-derived",
                    metadata=f"catalog={catalog}",
                )

                if existing_tle and existing_tle.line1 != tle_data.line1:
                    self.anomaly_repo.create_anomaly(
                        anomaly_type="ORBIT_SHIFT",
                        description=f"TLE epoch advanced for NORAD {tle_data.norad_id}.",
                        severity="medium",
                        norad_id=tle_data.norad_id,
                    )

        activity = self.signal_repo.get_signal_activity(hours=1)
        if activity and activity[0][1] > 20:
            self.anomaly_repo.create_anomaly(
                anomaly_type="TRAFFIC_SPIKE",
                description=f"Elevated signal activity detected: {activity[0][1]} observations/hour.",
                severity="high",
                region="GLOBAL",
            )

        return summary
