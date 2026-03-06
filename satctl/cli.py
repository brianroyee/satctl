"""Command-line interface for satctl."""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime

import click

from satctl import __version__
from satctl.config import Config, get_config
from satctl.database.repository import (
    AnomalyRepository,
    SatelliteRepository,
    SignalRepository,
    SyncLogRepository,
    TLERepository,
)
from satctl.database.schema import create_database
from satctl.providers import (
    CelesTrakProvider,
    SatcatProvider,
    SatnogsObservationProvider,
    SatnogsTransmitterProvider,
)


@click.group()
@click.version_option(__version__)
@click.pass_context
def cli(ctx: click.Context) -> None:
    """satctl - Satellite signal intelligence CLI."""
    ctx.ensure_object(Config)
    ctx.obj = get_config()


@cli.command()
@click.option("--force", is_flag=True, help="Force reinitialize if database exists")
@click.pass_obj
def init(config: Config, force: bool) -> None:
    """Initialize satctl environment."""
    config.ensure_data_dir()
    config.ensure_cache_dir()

    if config.database_path.exists() and force:
        config.database_path.unlink()

    create_database(config.database_path)
    click.echo(f"Database created at: {config.database_path}")


@cli.command()
@click.option("--catalogs", default="active,stations,weather,gps,glo,galileo,beidou", help="Comma-separated catalogs")
@click.option("--timeout", default=30.0, help="HTTP timeout in seconds")
@click.option("--retries", default=2, help="Request retries per provider")
@click.pass_obj
def sync(config: Config, catalogs: str, timeout: float, retries: int) -> None:
    """Sync satellite intelligence data."""
    config.ensure_data_dir()
    config.ensure_cache_dir()
    if not config.database_path.exists():
        create_database(config.database_path)

    sat_repo = SatelliteRepository(config.database_path)
    tle_repo = TLERepository(config.database_path)
    signal_repo = SignalRepository(config.database_path)
    anomaly_repo = AnomalyRepository(config.database_path)
    sync_repo = SyncLogRepository(config.database_path)

    sync_log = sync_repo.create_sync()
    catalog_list = [c.strip() for c in catalogs.split(",") if c.strip()]
    previous_tle_map = {tle.norad_id: tle for tle in tle_repo.get_all_latest_tles()}

    satellites_added = 0
    satellites_updated = 0
    errors: list[str] = []

    async def do_sync() -> None:
        nonlocal satellites_added, satellites_updated

        celestrak = CelesTrakProvider(timeout=timeout, retries=retries, cache_dir=config.cache_dir)
        satnogs_tx = SatnogsTransmitterProvider(timeout=timeout, retries=retries)
        satnogs_obs = SatnogsObservationProvider(timeout=timeout, retries=retries)
        satcat = SatcatProvider()

        for catalog in catalog_list:
            click.echo(f"Fetching CelesTrak catalog: {catalog}...")
            records, error = await celestrak.fetch_catalog(catalog)
            if error:
                click.echo(f"  {error}")
                if "Using cached" not in error:
                    errors.append(error)

            for record in records:
                sat_repo.upsert_satellite(record.norad_id, record.name, source=record.source)
                existing_tle = previous_tle_map.get(record.norad_id)
                if existing_tle is None:
                    satellites_added += 1
                    anomaly_repo.create_anomaly(
                        anomaly_type="NEW_OBJECT",
                        description=f"New object detected in catalog: NORAD {record.norad_id}",
                        severity="low",
                        norad_id=record.norad_id,
                    )
                elif existing_tle.epoch < record.epoch:
                    satellites_updated += 1
                else:
                    continue

                tle_repo.upsert_tle(
                    norad_id=record.norad_id,
                    epoch=record.epoch,
                    line1=record.line1,
                    line2=record.line2,
                    source=record.source,
                )

                if existing_tle and existing_tle.line1 != record.line1:
                    anomaly_repo.create_anomaly(
                        anomaly_type="ORBIT_SHIFT",
                        description=f"TLE changed for NORAD {record.norad_id}.",
                        severity="medium",
                        norad_id=record.norad_id,
                    )

        tx_records, tx_error = await satnogs_tx.fetch_transmitters(limit=3000)
        if tx_error:
            errors.append(tx_error)
        for tx in tx_records:
            existing_tx = signal_repo.get_transmitter(tx.tx_id)
            signal_repo.upsert_transmitter(
                tx_id=tx.tx_id,
                norad_id=tx.norad_id,
                frequency=tx.frequency,
                mode=tx.mode,
                bandwidth=tx.bandwidth,
                source=tx.source,
                confidence=tx.confidence,
            )
            if existing_tx is None:
                anomaly_repo.create_anomaly(
                    anomaly_type="RF_APPEAR",
                    description=f"New transmitter {tx.tx_id} for NORAD {tx.norad_id}.",
                    severity="low",
                    norad_id=tx.norad_id,
                    tx_id=tx.tx_id,
                )

        obs_records, obs_error = await satnogs_obs.fetch_recent_observations(limit=1000)
        if obs_error:
            errors.append(obs_error)
        for obs in obs_records:
            signal_repo.add_observation(
                norad_id=obs.norad_id,
                tx_id=obs.tx_id,
                region=obs.region,
                station_id=obs.station_id,
                source=obs.source,
                metadata=obs.metadata,
            )

        _, satcat_error = await satcat.fetch_metadata()
        if satcat_error:
            errors.append(satcat_error)

    asyncio.run(do_sync())

    activity = signal_repo.get_signal_activity(hours=1)
    if activity and activity[0][1] > 100:
        anomaly_repo.create_anomaly(
            anomaly_type="TRAFFIC_SPIKE",
            description=f"Elevated signal activity detected: {activity[0][1]} observations/hour.",
            severity="high",
            region="GLOBAL",
        )

    sync_repo.complete_sync(
        sync_log.id,
        satellites_added=satellites_added,
        satellites_updated=satellites_updated,
        error_message="; ".join(errors) if errors else None,
    )

    click.echo("\nSync complete")
    click.echo(f"  Satellites added: {satellites_added}")
    click.echo(f"  Satellites updated: {satellites_updated}")
    click.echo(f"  Total in database: {sat_repo.get_satellite_count()}")
    if errors:
        click.echo(f"  Provider errors: {len(errors)}")


@cli.command()
@click.option("--region", default=None, help="Region name (e.g. india)")
@click.option("--refresh", default=1.5, help="Refresh rate in seconds")
@click.option("--limit", default=500, help="Maximum satellites to display")
@click.pass_obj
def monitor(config: Config, region: str | None, refresh: float, limit: int) -> None:
    """Launch the intelligence dashboard."""
    if not config.database_path.exists():
        click.echo("No satellite data available. Run satctl sync.")
        sys.exit(1)

    group = None
    if region:
        group = f"region:{region.strip().lower()}"
    from satctl.tui.app import run_tui

    run_tui(config=config, refresh_rate=refresh, limit=limit, group=group)


@cli.command(name="catalog")
@click.option("--limit", default=50, help="Maximum rows")
@click.pass_obj
def catalog_cmd(config: Config, limit: int) -> None:
    """Show satellite catalog with signal counts."""
    if not config.database_path.exists():
        click.echo("No satellite data available. Run satctl sync.")
        sys.exit(1)

    sat_repo = SatelliteRepository(config.database_path)
    signal_repo = SignalRepository(config.database_path)
    signal_counts = dict(signal_repo.get_signal_activity(hours=24))
    sats = sat_repo.get_all_satellites()[:limit]

    header = f"{'NORAD':<8} {'NAME':<28} {'OWNER':<8} {'ORBIT':<6} {'LAST SEEN':<17} {'SIGNALS':<7}"
    click.echo(header)
    click.echo("-" * len(header))
    for sat in sats:
        seen = sat.last_seen_at.strftime("%Y-%m-%d %H:%M") if sat.last_seen_at else "-"
        click.echo(
            f"{sat.norad_id:<8} {sat.name[:28]:<28} {(sat.owner_code or '-'):<8} {(sat.orbit_class or '-'):<6} {seen:<17} {signal_counts.get(sat.norad_id, 0):<7}"
        )


@cli.command(name="anomalies")
@click.option("--limit", default=50, help="Maximum anomalies to show")
@click.option("--status", default=None, help="Filter by status")
@click.pass_obj
def anomalies_cmd(config: Config, limit: int, status: str | None) -> None:
    """Show anomaly intelligence feed."""
    if not config.database_path.exists():
        click.echo("No satellite data available. Run satctl sync.")
        sys.exit(1)

    anomalies = AnomalyRepository(config.database_path).list_recent(limit=limit, status=status)
    if not anomalies:
        click.echo("No anomalies recorded yet. Run satctl sync to generate intelligence.")
        return

    header = f"{'TIME (UTC)':<20} {'TYPE':<14} {'SEV':<6} {'NORAD':<8} DESCRIPTION"
    click.echo(header)
    click.echo("-" * len(header))
    for item in anomalies:
        norad = str(item.norad_id) if item.norad_id else "-"
        click.echo(
            f"{item.timestamp.strftime('%Y-%m-%d %H:%M'):<20} {item.type:<14} {item.severity.upper():<6} {norad:<8} {item.description}"
        )


@cli.command()
@click.pass_obj
def status(config: Config) -> None:
    """Show satctl status."""
    if not config.database_path.exists():
        click.echo("Database not initialized. Run 'satctl sync' first.")
        sys.exit(1)

    sat_repo = SatelliteRepository(config.database_path)
    sync_repo = SyncLogRepository(config.database_path)
    sat_count = sat_repo.get_satellite_count()
    last_sync = sync_repo.get_last_sync()

    click.echo(f"satctl v{__version__}")
    click.echo(f"Catalog: {sat_count:,} satellites")
    click.echo(f"Database: {config.database_path}")
    if last_sync and last_sync.completed_at:
        age = datetime.utcnow() - last_sync.completed_at
        click.echo(f"Last sync: {last_sync.completed_at.strftime('%Y-%m-%d %H:%M:%S')} UTC ({age.seconds // 3600}h ago)")


def main() -> None:
    cli(obj=None)


if __name__ == "__main__":
    main()
