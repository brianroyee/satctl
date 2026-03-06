"""Tests for sync command intelligence ingestion behavior."""

from __future__ import annotations

from datetime import datetime

from click.testing import CliRunner

from satctl.cli import cli
from satctl.database.repository import AnomalyRepository, SatelliteRepository
from satctl.normalization import ObservationRecord, TLERecord, TransmitterRecord


def test_sync_ingests_provider_records_and_avoids_duplicate_rf_appear(tmp_path, monkeypatch):
    """Sync should ingest provider data and create RF_APPEAR only for new transmitters."""

    async def fake_fetch_catalog(self, catalog):
        return [
            TLERecord(
                norad_id=25544,
                name="ISS (ZARYA)",
                line1="1 25544U 98067A   24064.50000000  .00016717  00000-0  30000-3 0  9993",
                line2="2 25544  51.6400 208.9166 0006707  35.0742 325.0284 15.49820237440256",
                epoch=datetime(2024, 3, 4, 12, 0, 0),
                source=f"celestrak:{catalog}",
            )
        ], None

    async def fake_fetch_transmitters(self, limit=500):
        return [
            TransmitterRecord(
                tx_id="tx-iss",
                norad_id=25544,
                frequency=145800000.0,
                mode="FM",
                bandwidth=25000.0,
                source="satnogs:transmitters",
            )
        ], None

    async def fake_fetch_observations(self, limit=500):
        return [
            ObservationRecord(
                norad_id=25544,
                tx_id="tx-iss",
                source="satnogs:observations",
                station_id="station-1",
            )
        ], None

    async def fake_fetch_metadata(self):
        return [], None

    monkeypatch.setattr("satctl.providers.celestrak.CelesTrakProvider.fetch_catalog", fake_fetch_catalog)
    monkeypatch.setattr(
        "satctl.providers.satnogs_transmitters.SatnogsTransmitterProvider.fetch_transmitters",
        fake_fetch_transmitters,
    )
    monkeypatch.setattr(
        "satctl.providers.satnogs_observations.SatnogsObservationProvider.fetch_recent_observations",
        fake_fetch_observations,
    )
    monkeypatch.setattr("satctl.providers.satcat.SatcatProvider.fetch_metadata", fake_fetch_metadata)

    runner = CliRunner()
    env = {"SATCTL_DATA_DIR": str(tmp_path)}

    first = runner.invoke(cli, ["sync", "--catalogs", "active", "--retries", "0"], env=env)
    assert first.exit_code == 0
    assert "Sync complete" in first.output

    sat_repo = SatelliteRepository(tmp_path / "satctl.db")
    assert sat_repo.get_satellite_count() == 1

    anom_repo = AnomalyRepository(tmp_path / "satctl.db")
    first_anomalies = anom_repo.list_recent(limit=20)
    assert any(a.type == "RF_APPEAR" for a in first_anomalies)

    second = runner.invoke(cli, ["sync", "--catalogs", "active", "--retries", "0"], env=env)
    assert second.exit_code == 0

    second_anomalies = anom_repo.list_recent(limit=50)
    rf_appear_count = sum(1 for a in second_anomalies if a.type == "RF_APPEAR")
    assert rf_appear_count == 1
