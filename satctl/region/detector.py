"""Region pass detection for satctl."""

from __future__ import annotations

from typing import Iterable, Any

from satctl.propagation.skyfield_engine import SatellitePosition
from satctl.region.region import Region


class PassDetector:
    """Detects satellite passes entering or leaving a region."""

    def __init__(self, region: Region):
        """Initialize the region pass detector.

        Args:
            region: The Region to monitor.
        """
        self.region = region
        self.previous_inside: dict[int, bool] = {}

    def update(self, positions: Iterable[SatellitePosition]) -> list[dict[str, Any]]:
        """Update detector with new positions and emit events.

        Args:
            positions: Iterable of current satellite positions.

        Returns:
            List of event dictionaries: {"type": "enter"|"exit", "satellite": SatellitePosition}.
        """
        events = []

        for pos in positions:
            norad_id = pos.norad_id
            inside = self.region.contains(pos.latitude, pos.longitude)
            
            was_inside = self.previous_inside.get(norad_id, False)

            if inside and not was_inside:
                events.append({"type": "enter", "satellite": pos})
            elif not inside and was_inside:
                events.append({"type": "exit", "satellite": pos})

            self.previous_inside[norad_id] = inside

        return events

    def get_inside_count(self) -> int:
        """Get the number of satellites currently inside the region."""
        return sum(1 for v in self.previous_inside.values() if v)
