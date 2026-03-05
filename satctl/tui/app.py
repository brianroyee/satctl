"""Main TUI application for satctl."""

from __future__ import annotations

import asyncio
from datetime import datetime
from enum import Enum
from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.driver import Driver
from textual.widgets import Header, Footer, Static

from satctl.config import Config, get_config
from satctl.database.repository import SatelliteRepository, TLERepository, SyncLogRepository
from satctl.propagation.sgp4_engine import SGP4Engine, SatellitePosition
from satctl.propagation.utils import Coordinate


class RegionMode(str, Enum):
    """Region filtering modes."""

    GLOBAL = "GLOBAL"
    BBOX = "BBOX"
    RADIUS = "RADIUS"


class OrbitFilter(str, Enum):
    """Orbit type filters."""

    ALL = "ALL"
    LEO = "LEO"
    MEO = "MEO"
    GEO = "GEO"


class GroupFilter(str, Enum):
    """Catalog group filters."""

    ALL = "ALL"
    ACTIVE = "active"
    STATIONS = "stations"
    WEATHER = "weather"
    GPS = "GPS"
    STARLINK = "starlink"


class SatTUIApp(App):
    """Main TUI application for satctl."""

    CSS = """
    Screen {
        background: $surface;
    }

    #main {
        height: 100%;
        layout: grid;
        grid-size: 3 1;
        grid-columns: 1fr 3fr 1fr;
    }

    #header-bar {
        height: 3;
        background: $primary;
        color: $text;
        content-align: center middle;
    }

    #sidebar {
        width: 20;
        background: $panel;
        border-right: solid $border;
        padding: 1;
    }

    #content {
        background: $surface;
    }

    #details {
        width: 25;
        background: $panel;
        border-left: solid $border;
        padding: 1;
    }

    .filter-label {
        text-style: bold;
        color: $text-muted;
    }

    .filter-value {
        color: $text;
    }

    .sat-row {
        height: 1;
    }

    .sat-id {
        width: 8;
    }

    .sat-name {
        width: 30;
    }

    .sat-lat {
        width: 12;
    }

    .sat-lon {
        width: 12;
    }

    .sat-alt {
        width: 10;
    }

    .sat-class {
        width: 6;
    }

    .detail-label {
        text-style: bold;
        color: $text-muted;
    }

    .detail-value {
        color: $text;
    }

    #footer-bar {
        height: 3;
        background: $panel;
        content-align: center middle;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("r", "refresh", "Refresh"),
        Binding("s", "sync_catalog", "Sync"),
        Binding("/", "focus_search", "Search"),
        Binding("g", "cycle_group", "Group"),
        Binding("o", "cycle_orbit", "Orbit"),
        Binding("m", "cycle_region", "Region"),
        Binding("escape", "clear_selection", "Clear"),
        Binding("?", "show_help", "Help"),
    ]

    def __init__(
        self,
        config: Config | None = None,
        refresh_rate: float = 1.5,
        limit: int = 500,
        **kwargs,
    ):
        """Initialize the TUI application.

        Args:
            config: Configuration instance.
            refresh_rate: Refresh rate in seconds.
            limit: Maximum number of satellites to display.
        """
        super().__init__(**kwargs)
        self.config = config or get_config()

        # Refresh settings
        self.refresh_rate = refresh_rate
        self.limit = limit

        # Filter state
        self.region_mode = RegionMode.GLOBAL
        self.orbit_filter = OrbitFilter.ALL
        self.group_filter = GroupFilter.ALL
        self.search_query = ""

        # Region parameters (for BBOX and RADIUS modes)
        self.bbox = (-90, 90, -180, 180)  # min_lat, max_lat, min_lon, max_lon
        self.radius_center = Coordinate(0.0, 0.0)
        self.radius_km = 1000.0

        # Data
        self.positions: list[SatellitePosition] = []
        self.selected_position: Optional[SatellitePosition] = None

        # Repositories
        self.satellite_repo = SatelliteRepository(self.config.database_path)
        self.tle_repo = TLERepository(self.config.database_path)
        self.sync_repo = SyncLogRepository(self.config.database_path)

        # Refresh timer
        self._refresh_task: Optional[asyncio.Task] = None

        # SGP4 engine
        self.sgp4 = SGP4Engine()

    def compose(self) -> ComposeResult:
        """Compose the UI."""
        # Header
        yield Header(show_clock=True)

        # Main content
        with Container(id="main"):
            # Sidebar (filters)
            with Vertical(id="sidebar"):
                yield Static("Filters", classes="filter-label")
                yield Static(f"Group: {self.group_filter.value}", id="filter-group")
                yield Static(f"Orbit: {self.orbit_filter.value}", id="filter-orbit")
                yield Static(f"Region: {self.region_mode.value}", id="filter-region")
                yield Static(f"Search: {self.search_query or '(none)'}", id="filter-search")
                yield Static(f"Limit: {self.limit}", id="filter-limit")

            # Content (satellite table)
            with Vertical(id="content"):
                yield Static("Satellites", classes="filter-label")
                yield Static("Loading...", id="sat-table")

            # Details panel
            with Vertical(id="details"):
                yield Static("Details", classes="filter-label")
                yield Static("Select a satellite", id="detail-content")

        # Footer
        yield Footer()

    def on_mount(self) -> None:
        """Handle mount event."""
        self.update_header()
        self.set_timer(self.refresh_rate, self._do_refresh)

    def update_header(self) -> None:
        """Update the header with current status."""
        # Get catalog stats
        sat_count = self.satellite_repo.get_satellite_count()
        last_sync = self.sync_repo.get_last_sync()

        if last_sync and last_sync.completed_at:
            sync_age = datetime.utcnow() - last_sync.completed_at
            sync_str = f"Sync {sync_age.seconds // 3600}h ago"
        else:
            sync_str = "Never synced"

        header_text = f" satctl v0.1 | UTC {datetime.utcnow().strftime('%H:%M:%S')} | Catalog {sat_count} | {sync_str} "
        self.query_one("#header-bar", Static).update(header_text)

    async def _do_refresh(self) -> None:
        """Perform the refresh operation."""
        self.refresh_positions()
        self.update_header()
        self.set_timer(self.refresh_rate, self._do_refresh)

    def refresh_positions(self) -> None:
        """Refresh satellite positions."""
        try:
            # Get all latest TLEs
            tles = self.tle_repo.get_all_latest_tles()

            # Limit for performance
            tles = tles[: self.limit]

            # Calculate positions
            positions = []
            now = datetime.utcnow()

            for tle in tles:
                try:
                    sat = self.sgp4.create_satellite_from_tle_model(tle)
                    pos = self.sgp4.propagate(sat, now)

                    if pos:
                        # Apply filters
                        if self._passes_filters(pos):
                            positions.append(pos)

                except Exception:
                    continue

            self.positions = positions
            self.update_sat_table()

        except Exception as e:
            self.query_one("#sat-table", Static).update(f"Error: {e}")

    def _passes_filters(self, pos: SatellitePosition) -> bool:
        """Check if a position passes all active filters."""
        # Orbit filter
        if self.orbit_filter != OrbitFilter.ALL:
            if pos.orbital_class != self.orbit_filter.value:
                return False

        # Region filter
        if self.region_mode == RegionMode.BBOX:
            from satctl.propagation.utils import is_in_bounding_box

            min_lat, max_lat, min_lon, max_lon = self.bbox
            coord = Coordinate(pos.latitude, pos.longitude)
            if not is_in_bounding_box(coord, min_lat, max_lat, min_lon, max_lon):
                return False

        elif self.region_mode == RegionMode.RADIUS:
            from satctl.propagation.utils import is_in_radius

            coord = Coordinate(pos.latitude, pos.longitude)
            if not is_in_radius(coord, self.radius_center, self.radius_km):
                return False

        # Search filter
        if self.search_query:
            query = self.search_query.lower()
            name = pos.name.lower()
            if query not in name and str(pos.norad_id) != query:
                return False

        return True

    def update_sat_table(self) -> None:
        """Update the satellite table display."""
        if not self.positions:
            self.query_one("#sat-table", Static).update("No satellites")
            return

        # Build table
        lines = []
        header = f"{'NORAD':<8} {'Name':<30} {'Lat':<12} {'Lon':<12} {'Alt':<10} {'Class':<6}"
        lines.append(header)
        lines.append("-" * len(header))

        for pos in self.positions[:50]:  # Show max 50 in table
            lat = f"{pos.latitude:+.4f}°"
            lon = f"{pos.longitude:+.4f}°"
            alt = f"{pos.altitude:.1f} km"

            line = f"{pos.norad_id:<8} {pos.name[:28]:<30} {lat:<12} {lon:<12} {alt:<10} {pos.orbital_class:<6}"
            lines.append(line)

        # Show count
        if len(self.positions) > 50:
            lines.append(f"... and {len(self.positions) - 50} more")

        self.query_one("#sat-table", Static).update("\n".join(lines))

    def update_details(self) -> None:
        """Update the details panel."""
        if not self.selected_position:
            self.query_one("#detail-content", Static).update("Select a satellite")
            return

        pos = self.selected_position

        lines = []
        lines.append(f"Name: {pos.name}")
        lines.append(f"NORAD: {pos.norad_id}")
        lines.append(f"")
        lines.append("Position:")
        lines.append(f"  Lat:  {pos.latitude:+.4f}°")
        lines.append(f"  Lon:  {pos.longitude:+.4f}°")
        lines.append(f"  Alt:  {pos.altitude:.1f} km")
        lines.append(f"")
        lines.append("Orbital:")
        lines.append(f"  Class: {pos.orbital_class}")
        lines.append(f"  Vel:   {pos.velocity:.2f} km/s")
        lines.append(f"")
        lines.append(f"TLE Age: {pos.tle_age_days:.2f} days")
        lines.append(f"")
        lines.append(f"Time: {pos.timestamp.strftime('%Y-%m-%d %H:%M:%S')} UTC")

        self.query_one("#detail-content", Static).update("\n".join(lines))

    def action_refresh(self) -> None:
        """Refresh positions manually."""
        self.refresh_positions()
        self.update_header()

    def action_sync_catalog(self) -> None:
        """Sync the catalog."""
        self.query_one("#sat-table", Static).update("Syncing...")

    def action_focus_search(self) -> None:
        """Focus the search input."""
        # Could implement a modal input here
        pass

    def action_cycle_group(self) -> None:
        """Cycle through group filters."""
        groups = list(GroupFilter)
        current_idx = groups.index(self.group_filter)
        self.group_filter = groups[(current_idx + 1) % len(groups)]
        self.query_one("#filter-group", Static).update(f"Group: {self.group_filter.value}")
        self.refresh_positions()

    def action_cycle_orbit(self) -> None:
        """Cycle through orbit filters."""
        orbits = list(OrbitFilter)
        current_idx = orbits.index(self.orbit_filter)
        self.orbit_filter = orbits[(current_idx + 1) % len(orbits)]
        self.query_one("#filter-orbit", Static).update(f"Orbit: {self.orbit_filter.value}")
        self.refresh_positions()

    def action_cycle_region(self) -> None:
        """Cycle through region modes."""
        regions = list(RegionMode)
        current_idx = regions.index(self.region_mode)
        self.region_mode = regions[(current_idx + 1) % len(regions)]
        self.query_one("#filter-region", Static).update(f"Region: {self.region_mode.value}")
        self.refresh_positions()

    def action_clear_selection(self) -> None:
        """Clear the selected satellite."""
        self.selected_position = None
        self.update_details()

    def action_show_help(self) -> None:
        """Show help."""
        help_text = """
Keybindings:
  q - Quit
  r - Refresh positions
  s - Sync catalog
  / - Search
  g - Cycle group
  o - Cycle orbit
  m - Cycle region
  Esc - Clear selection
  ? - This help
        """.strip()
        self.query_one("#detail-content", Static).update(help_text)


def run_tui(
    config: Config | None = None,
    refresh_rate: float = 1.5,
    limit: int = 500,
    group: str | None = None,
) -> None:
    """Run the TUI application.

    Args:
        config: Configuration instance.
        refresh_rate: Refresh rate in seconds.
        limit: Maximum number of satellites.
        group: Initial group filter.
    """
    app = SatTUIApp(
        config=config,
        refresh_rate=refresh_rate,
        limit=limit,
    )

    if group:
        try:
            app.group_filter = GroupFilter(group)
        except ValueError:
            pass

    app.run()
