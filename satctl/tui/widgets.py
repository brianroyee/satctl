"""Custom TUI widgets for satctl."""

from __future__ import annotations

from typing import Optional

from rich.console import RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from textual.widgets import Static

from satctl.propagation.models import SatellitePosition


class HeaderBar(Static):
    """Top bar showing situational awareness stats."""

    def __init__(self, region_name: str = "Global", total_count: int = 0, **kwargs):
        super().__init__(**kwargs)
        self.region_name = region_name
        self.sat_count = 0
        self.total_count = total_count
        self.update_rate = 1.0

    def on_mount(self) -> None:
        self.update(self._render_header())

    def update_stats(self, sat_count: int, total_count: int):
        self.sat_count = sat_count
        self.total_count = total_count
        self.update(self._render_header())

    def set_region(self, name: str):
        self.region_name = name
        self.update(self._render_header())

    def _render_header(self) -> RenderableType:
        return Text.assemble(
            (" SATCTL ", "bold reverse cyan"),
            " ",
            ("Region: ", "bold"), (f"{self.region_name}", "cyan"),
            (" │ ", "dim"),
            ("In Region: ", "bold"), (f"{self.sat_count}", "green"),
            (" │ ", "dim"),
            ("Total: ", "bold"), (f"{self.total_count}", "white"),
            (" │ ", "dim"),
            ("Rate: ", "bold"), (f"{self.update_rate}s", "white"),
        )


class RegionMap(Static):
    """Minimap widget showing satellites in region."""

    def __init__(self, min_lat: float, max_lat: float, min_lon: float, max_lon: float, **kwargs):
        super().__init__(**kwargs)
        self.min_lat = min_lat
        self.max_lat = max_lat
        self.min_lon = min_lon
        self.max_lon = max_lon
        self.positions: list[SatellitePosition] = []
        self.selected_id: Optional[int] = None
        self.trail: list[tuple[float, float]] = []  # trail for selected sat

    def update_positions(self, positions: list[SatellitePosition], selected_id: Optional[int] = None):
        # Track trail for selected
        if selected_id and selected_id == self.selected_id:
            sel = next((p for p in positions if p.norad_id == selected_id), None)
            if sel:
                self.trail.append((sel.latitude, sel.longitude))
                self.trail = self.trail[-10:]  # keep last 10 ticks
        elif selected_id != self.selected_id:
            self.trail = []

        self.positions = positions
        self.selected_id = selected_id
        self.refresh()

    def render(self) -> RenderableType:
        w = max((self.size.width or 40) - 4, 10)  # account for panel border
        h = max((self.size.height or 12) - 3, 4)

        grid = [[" " for _ in range(w)] for _ in range(h)]

        lat_range = self.max_lat - self.min_lat
        lon_range = self.max_lon - self.min_lon
        if lat_range == 0 or lon_range == 0:
            return Panel("No region bounds", title="MAP", border_style="green")

        def to_xy(lat, lon):
            x = int((lon - self.min_lon) / lon_range * (w - 1))
            y = int((self.max_lat - lat) / lat_range * (h - 1))
            return max(0, min(x, w - 1)), max(0, min(y, h - 1))

        # Draw trail dots first
        for tlat, tlon in self.trail:
            tx, ty = to_xy(tlat, tlon)
            if grid[ty][tx] == " ":
                grid[ty][tx] = "trail"

        # Count satellites per cell for clustering
        cell_count: dict[tuple[int, int], list] = {}
        for pos in self.positions:
            x, y = to_xy(pos.latitude, pos.longitude)
            cell_count.setdefault((x, y), []).append(pos)

        # Draw satellites
        for y in range(h):
            for x in range(w):
                if (x, y) in cell_count:
                    sats = cell_count[(x, y)]
                    if any(s.norad_id == self.selected_id for s in sats):
                        grid[y][x] = "selected"
                    elif len(sats) > 1:
                        grid[y][x] = "cluster"
                    else:
                        grid[y][x] = "sat"
                elif grid[y][x] == " ":
                    # Draw subtle background grid
                    if y % 4 == 0 and x % 8 == 0:
                        grid[y][x] = "grid_cross"

        # Build output
        lines = []
        for row in grid:
            line = Text()
            for cell in row:
                if cell == "selected":
                    line.append("@", style="bold yellow")
                elif cell == "cluster":
                    line.append("+", style="bold magenta")
                elif cell == "sat":
                    line.append("*", style="bold cyan")
                elif cell == "trail":
                    line.append("·", style="bold yellow")
                elif cell == "grid_cross":
                    line.append("+", style="dim #30363d")
                else:
                    line.append(" ")
            lines.append(line)

        content = Text("\n").join(lines)

        # Legend
        legend = Text.assemble(
            ("@ ", "bold yellow"), ("sel ", "dim"),
            ("* ", "cyan"), ("sat ", "dim"),
            ("+ ", "bold magenta"), ("cluster ", "dim"),
            ("· ", "dim yellow"), ("trail", "dim"),
        )

        final = Text()
        final.append(content)
        final.append("\n")
        final.append(legend)

        return Panel(final, title="REGION MAP", border_style="green")


class SatelliteDetails(Static):
    """Panel showing detailed info for the selected satellite."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.position: Optional[SatellitePosition] = None
        self.metadata: dict = {}
        self.in_region: bool = False

    def update_details(self, position: Optional[SatellitePosition], metadata: dict = None, in_region: bool = False):
        self.position = position
        self.metadata = metadata or {}
        self.in_region = in_region
        self.update(self._render_details())

    def clear_details(self):
        self.position = None
        self.update(self._render_details())

    def _render_details(self) -> RenderableType:
        if not self.position:
            return Panel(
                Text("Select a satellite from the list", style="dim"),
                title="DETAILS",
                border_style="blue"
            )

        pos = self.position
        meta = self.metadata

        table = Table.grid(expand=True)
        table.add_column(style="bold cyan", width=14)
        table.add_column(style="white")

        table.add_row("Name:", pos.name)
        table.add_row("NORAD ID:", str(pos.norad_id))
        table.add_row("Country:", meta.get("country", "UNK"))
        table.add_row("Operator:", meta.get("operator", "Unknown"))
        table.add_row("Latitude:", f"{pos.latitude:+.4f}°")
        table.add_row("Longitude:", f"{pos.longitude:+.4f}°")
        table.add_row("Altitude:", f"{pos.altitude:.1f} km")
        table.add_row("Velocity:", f"{pos.velocity:.2f} km/s")
        table.add_row("Orbit:", pos.orbital_class)
        table.add_row("TLE Age:", f"{pos.tle_age_days:.1f} days")
        region_str = "[green]Yes[/green]" if self.in_region else "[red]No[/red]"
        table.add_row("In Region:", Text.from_markup(region_str))

        return Panel(table, title=f"DETAILS: {pos.name}", border_style="blue")
