"""Command-line interface for satctl."""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime
from pathlib import Path

import click

from satctl import __version__
from satctl.config import Config, get_config
from satctl.database.schema import create_database
from satctl.database.repository import SatelliteRepository, TLERepository, SyncLogRepository
from satctl.sync.celestrak import CelesTrakClient
from satctl.propagation.sgp4_engine import SGP4Engine
from satctl.tui.app import run_tui


@click.group()
@click.version_option(__version__)
@click.pass_context
def cli(ctx: click.Context) -> None:
    """satctl - Terminal-native satellite OSINT tool."""
    ctx.ensure_object(Config)
    ctx.obj = get_config()


@cli.command()
@click.option("--force", is_flag=True, help="Force reinitialize if database exists")
@click.pass_obj
def init(config: Config) -> None:
    """Initialize satctl environment."""
    click.echo("Initializing satctl...")

    # Ensure data directory exists
    config.ensure_data_dir()

    # Create database
    create_database(config.database_path)

    click.echo(f"Database created at: {config.database_path}")
    click.echo("Run 'satctl sync' to download satellite data.")


@cli.command()
@click.option(
    "--catalogs",
    default="active,stations,weather,gps,glo,galileo,beidou",
    help="Comma-separated list of catalogs to sync",
)
@click.option("--timeout", default=30.0, help="HTTP timeout in seconds")
@click.pass_obj
def sync(config: Config, catalogs: str, timeout: float) -> None:
    """Sync satellite catalog from CelesTrak."""
    click.echo("Syncing satellite catalog...")

    # Ensure database exists
    if not config.database_path.exists():
        click.echo("Database not initialized. Run 'satctl init' first.")
        sys.exit(1)

    # Create repositories
    sat_repo = SatelliteRepository(config.database_path)
    tle_repo = TLERepository(config.database_path)
    sync_repo = SyncLogRepository(config.database_path)

    # Create sync log
    sync_log = sync_repo.create_sync()

    # Parse catalogs
    catalog_list = [c.strip() for c in catalogs.split(",")]

    # Create client
    client = CelesTrakClient(timeout=timeout)

    # Sync each catalog
    satellites_added = 0
    satellites_updated = 0
    errors = []

    async def do_sync():
        nonlocal satellites_added, satellites_updated, errors

        for catalog in catalog_list:
            click.echo(f"Fetching {catalog}...")

            tle_iter, error = await client.fetch_catalog(catalog)

            if error:
                click.echo(f"  Error: {error}")
                errors.append(f"{catalog}: {error}")
                continue

            if tle_iter is None:
                continue

            for tle_data in tle_iter:
                try:
                    # Upsert satellite
                    sat = sat_repo.upsert_satellite(
                        norad_id=tle_data.norad_id,
                        name=tle_data.name,
                        source=catalog,
                    )

                    # Check if this is a new TLE
                    existing_tle = tle_repo.get_latest_tle(tle_data.norad_id)

                    if existing_tle is None or existing_tle.epoch < tle_data.epoch:
                        # Insert new TLE
                        tle_repo.upsert_tle(
                            norad_id=tle_data.norad_id,
                            epoch=tle_data.epoch,
                            line1=tle_data.line1,
                            line2=tle_data.line2,
                        )

                        if existing_tle is None:
                            satellites_added += 1
                        else:
                            satellites_updated += 1

                except Exception as e:
                    errors.append(f"Error processing {tle_data.name}: {e}")

    # Run async sync
    asyncio.run(do_sync())

    # Complete sync log
    error_msg = "; ".join(errors) if errors else None
    sync_repo.complete_sync(
        sync_log.id,
        satellites_added=satellites_added,
        satellites_updated=satellites_updated,
        error_message=error_msg,
    )

    # Summary
    click.echo(f"\nSync complete!")
    click.echo(f"  Satellites added: {satellites_added}")
    click.echo(f"  Satellites updated: {satellites_updated}")
    click.echo(f"  Total in database: {sat_repo.get_satellite_count()}")

    if errors:
        click.echo(f"\nErrors: {len(errors)}")


@cli.command()
@click.pass_obj
def status(config: Config) -> None:
    """Show satctl status."""
    # Ensure database exists
    if not config.database_path.exists():
        click.echo("Database not initialized. Run 'satctl init' first.")
        sys.exit(1)

    # Get stats
    sat_repo = SatelliteRepository(config.database_path)
    sync_repo = SyncLogRepository(config.database_path)

    sat_count = sat_repo.get_satellite_count()
    last_sync = sync_repo.get_last_sync()

    click.echo(f"satctl v{__version__}")
    click.echo(f"Catalog: {sat_count:,} satellites")
    click.echo(f"Database: {config.database_path}")

    if last_sync and last_sync.completed_at:
        sync_time = last_sync.completed_at
        age = datetime.utcnow() - sync_time

        hours = age.seconds // 3600
        minutes = (age.seconds % 3600) // 60

        click.echo(f"Last sync: {sync_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        click.echo(f"Data age: {hours}h {minutes}m")
    else:
        click.echo("Never synced. Run 'satctl sync' to download data.")


@cli.command()
@click.argument("query")
@click.option("--limit", default=50, help="Maximum results to show")
@click.pass_obj
def search(config: Config, query: str, limit: int) -> None:
    """Search for satellites by name."""
    # Ensure database exists
    if not config.database_path.exists():
        click.echo("Database not initialized. Run 'satctl init' first.")
        sys.exit(1)

    # Search
    sat_repo = SatelliteRepository(config.database_path)
    results = sat_repo.get_satellites_by_name(query, limit=limit)

    if not results:
        click.echo(f"No satellites found matching '{query}'")
        return

    # Display results
    click.echo(f"Found {len(results)} satellites:\n")

    # Get latest TLE for each
    tle_repo = TLERepository(config.database_path)

    header = f"{'NORAD ID':<10} {'Name':<40} {'Epoch':<20}"
    click.echo(header)
    click.echo("-" * len(header))

    for sat in results:
        tle = tle_repo.get_latest_tle(sat.norad_id)
        epoch_str = tle.epoch.strftime("%Y-%m-%d") if tle else "N/A"
        click.echo(f"{sat.norad_id:<10} {sat.name[:38]:<40} {epoch_str:<20}")


@cli.command()
@click.option("--id", "norad_id", required=True, type=int, help="NORAD catalog ID")
@click.pass_obj
def now(config: Config, norad_id: int) -> None:
    """Show current position of a satellite."""
    # Ensure database exists
    if not config.database_path.exists():
        click.echo("Database not initialized. Run 'satctl init' first.")
        sys.exit(1)

    # Get satellite
    sat_repo = SatelliteRepository(config.database_path)
    sat = sat_repo.get_satellite(norad_id)

    if not sat:
        click.echo(f"Satellite with NORAD ID {norad_id} not found.")
        sys.exit(1)

    # Get latest TLE
    tle_repo = TLERepository(config.database_path)
    tle = tle_repo.get_latest_tle(norad_id)

    if not tle:
        click.echo(f"No TLE data found for {sat.name}.")
        sys.exit(1)

    # Calculate position
    sgp4 = SGP4Engine()
    satellite = sgp4.create_satellite_from_tle_model(tle)
    position = sgp4.propagate(satellite, datetime.utcnow())

    if not position:
        click.echo(f"Failed to calculate position for {sat.name}.")
        sys.exit(1)

    # Display
    click.echo(f"{sat.name} - NORAD {norad_id}")
    click.echo("=" * 40)

    lat, lon, alt = position.lat_lon_format

    click.echo(f"\nPosition ({position.timestamp.strftime('%Y-%m-%d %H:%M:%S')} UTC):")
    click.echo(f"  Latitude:  {lat}")
    click.echo(f"  Longitude: {lon}")
    click.echo(f"  Altitude:  {alt}")

    click.echo(f"\nOrbital:")
    click.echo(f"  Class: {position.orbital_class}")
    click.echo(f"  Velocity: {position.velocity:.2f} km/s")

    click.echo(f"\nTLE Age: {position.tle_age_days:.2f} days")
    click.echo(f"TLE Epoch: {tle.epoch.strftime('%Y-%m-%d %H:%M:%S')}")


@cli.command()
@click.option("--refresh", default=1.5, help="Refresh rate in seconds")
@click.option("--limit", default=500, help="Maximum satellites to display")
@click.option("--group", default=None, help="Initial group filter")
@click.pass_obj
def tui(config: Config, refresh: float, limit: int, group: str | None) -> None:
    """Launch the interactive TUI dashboard."""
    # Ensure database exists
    if not config.database_path.exists():
        click.echo("Database not initialized. Run 'satctl init' first.")
        sys.exit(1)

    # Run TUI
    run_tui(
        config=config,
        refresh_rate=refresh,
        limit=limit,
        group=group,
    )


def main() -> None:
    """Main entry point."""
    cli(obj=None)


if __name__ == "__main__":
    main()
