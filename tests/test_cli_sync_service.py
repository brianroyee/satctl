"""Tests for CLI sync service orchestration."""

from __future__ import annotations

import asyncio
import tempfile
from datetime import datetime
from pathlib import Path

from satctl.app.cli_sync_service import CliSyncService
from satctl.database.repository import (
    AnomalyRepository,
    SatelliteRepository,
    SignalRepository,
    SyncLogRepository,
    TLERepository,
)
from satctl.database.schema import create_database
from satctl.sync.tle_parser import TLEData


class FakeClient:
    def __init__(self, responses):
        self.responses = responses

    async def fetch_catalog(self, catalog_name: str):
        return self.responses[catalog_name]


def make_tle(norad_id: int, epoch: datetime, line1_suffix: str = "9993") -> TLEData:
    line1 = f"1 {norad_id:05d}U 98067A   24064.50000000  .00016717  00000-0  30000-3 0  {line1_suffix}"
    line2 = f"2 {norad_id:05d}  51.6400 208.9166 0006707  35.0742 325.0284 15.49820237440256"
    return TLEData(
        name=f"SAT-{norad_id}",
        norad_id=norad_id,
        line1=line1,
        line2=line2,
        epoch=epoch,
        inclination=51.64,
        eccentricity=0.0006707,
        raan=208.9166,
        argument_of_perigee=35.0742,
        mean_anomaly=325.0284,
        mean_motion=15.4982,
        orbit_number=44025,
    )


def test_sync_service_ingests_data_and_counts_changes():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        create_database(db_path)

        sat_repo = SatelliteRepository(db_path)
        tle_repo = TLERepository(db_path)
        signal_repo = SignalRepository(db_path)
        anomaly_repo = AnomalyRepository(db_path)
        sync_repo = SyncLogRepository(db_path)

        service = CliSyncService(
            sat_repo=sat_repo,
            tle_repo=tle_repo,
            signal_repo=signal_repo,
            anomaly_repo=anomaly_repo,
            sync_repo=sync_repo,
        )

        old_epoch = datetime(2024, 1, 1)
        new_epoch = datetime(2024, 2, 1)

        sat_repo.upsert_satellite(25544, "ISS", source="active")
        tle_repo.upsert_tle(25544, old_epoch, "1 25544U OLD", "2 25544 OLD", source="active")

        responses = {
            "active": ([make_tle(25544, new_epoch, "9991"), make_tle(40000, new_epoch)], None),
        }

        summary = asyncio.run(service.run(client=FakeClient(responses), catalogs=["active"]))

        assert summary.satellites_added == 1
        assert summary.satellites_updated == 1
        assert summary.errors == []
        assert sat_repo.get_satellite_count() == 2
        assert tle_repo.get_latest_tle(25544) is not None
        assert len(anomaly_repo.list_recent(limit=10)) == 1


def test_sync_service_ignores_cached_errors_and_tracks_real_errors():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        create_database(db_path)

        service = CliSyncService(
            sat_repo=SatelliteRepository(db_path),
            tle_repo=TLERepository(db_path),
            signal_repo=SignalRepository(db_path),
            anomaly_repo=AnomalyRepository(db_path),
            sync_repo=SyncLogRepository(db_path),
        )

        responses = {
            "active": ([], "Using cached data for active after error: timeout"),
            "weather": (None, "Error fetching catalog weather: timeout"),
        }

        summary = asyncio.run(service.run(client=FakeClient(responses), catalogs=["active", "weather"]))

        assert summary.errors == ["weather: Error fetching catalog weather: timeout"]
