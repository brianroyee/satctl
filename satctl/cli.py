"""Command-line interface for satctl."""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime

import click

from satctl import __version__
from satctl.config import Config, get_config
from satctl.database.schema import create_database
from satctl.database.repository import (
    SatelliteRepository,
    TLERepository,
    SyncLogRepository,
    SignalRepository,
    AnomalyRepository,
)
from satctl.sync.celestrak import CelesTrakClient
from satctl.tui.app import run_tui
from satctl.app.cli_sync_service import CliSyncService


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
    client = CelesTrakClient(timeout=timeout, retries=retries, cache_dir=config.cache_dir)

    service = CliSyncService(
        sat_repo=sat_repo,
        tle_repo=tle_repo,
        signal_repo=signal_repo,
        anomaly_repo=anomaly_repo,
        sync_repo=sync_repo,
    )

    for catalog in catalog_list:
        click.echo(f"Fetching {catalog}...")
    summary = asyncio.run(service.run(client=client, catalogs=catalog_list))

    sync_repo.complete_sync(
        sync_log.id,
        satellites_added=summary.satellites_added,
        satellites_updated=summary.satellites_updated,
        error_message="; ".join(summary.errors) if summary.errors else None,
    )

    click.echo("\nSync complete")
    click.echo(f"  Satellites added: {summary.satellites_added}")
    click.echo(f"  Satellites updated: {summary.satellites_updated}")
    click.echo(f"  Total in database: {sat_repo.get_satellite_count()}")
    if summary.errors:
        click.echo(f"  Provider errors: {len(summary.errors)}")


@cli.command()
@click.option("--region", default=None, help="Region name (e.g. india)")
@click.option("--refresh", default=1.5, help="Refresh rate in seconds")
@click.option("--limit", default=500, help="Maximum satellites to display")
@click.pass_obj
def monitor(config: Config, region: str | None, refresh: float, limit: int) -> None:
    """Launch the intelligence dashboard (default global traffic)."""
    if not config.database_path.exists():
        click.echo("No satellite data available. Run satctl sync.")
        sys.exit(1)

    group = None
    if region:
        normalized = region.strip().lower()
        group = f"region:{normalized}"
    run_tui(config=config, refresh_rate=refresh, limit=limit, group=group)


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
            f"{sat.norad_id:<8} {sat.name[:28]:<28} {(sat.owner_code or '-'): <8} {(sat.orbit_class or '-'):<6} {seen:<17} {signal_counts.get(sat.norad_id, 0):<7}"
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


@cli.command(hidden=True)
@click.option("--refresh", default=1.5)
@click.option("--limit", default=500)
@click.option("--group", default=None)
@click.pass_obj
def tui(config: Config, refresh: float, limit: int, group: str | None) -> None:
    """Backward-compatible alias for monitor."""
    run_tui(config=config, refresh_rate=refresh, limit=limit, group=group)


def main() -> None:
    cli(obj=None)


if __name__ == "__main__":
    main()
