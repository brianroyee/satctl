"""Propagation models and types."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


# Orbital class thresholds (in km)
GEO_ALTITUDE = 35786  # Geostationous orbit altitude


@dataclass
class SatellitePosition:
    """Satellite position data."""

    norad_id: int
    name: str
    latitude: float  # degrees
    longitude: float  # degrees
    altitude: float  # km above Earth surface
    timestamp: datetime
    tle_age_days: float
    orbital_class: str  # LEO, MEO, GEO, or GTO
    velocity: float  # km/s

    @property
    def lat_lon_format(self) -> tuple[str, str, str]:
        """Format latitude, longitude for display."""
        lat = f"{abs(self.latitude):.4f}°{'N' if self.latitude >= 0 else 'S'}"
        lon = f"{abs(self.longitude):.4f}°{'E' if self.longitude >= 0 else 'W'}"
        alt = f"{self.altitude:.1f} km"
        return lat, lon, alt


def classify_orbit(altitude: float) -> str:
    """Classify orbit based on altitude.

    Args:
        altitude: Altitude above Earth surface in km.

    Returns:
        Orbital class: LEO, MEO, GEO, or GTO.
    """
    if altitude < 2000:
        return "LEO"
    elif altitude < GEO_ALTITUDE:
        return "MEO"
    elif altitude < GEO_ALTITUDE + 500:
        return "GEO"
    else:
        return "GTO"  # Beyond GEO
