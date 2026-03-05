"""Skyfield orbital propagation engine for satctl."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from skyfield.api import EarthSatellite, load, wgs84

from satctl.database.models import TLE as TLEModel


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


class SkyfieldEngine:
    """Skyfield orbital propagation engine."""

    def __init__(self):
        """Initialize the Skyfield engine."""
        self.ts = load.timescale()

    def create_satellite_from_tle_model(self, tle: TLEModel) -> EarthSatellite:
        """Create a satellite object from TLE model.

        Args:
            tle: Database TLE model.

        Returns:
            EarthSatellite object.
        """
        try:
            name = getattr(tle, "satellite", None) and tle.satellite.name or f"SAT-{tle.norad_id}"
        except Exception:
            name = f"SAT-{tle.norad_id}"
            
        return EarthSatellite(tle.line1, tle.line2, name, self.ts)

    def propagate(
        self,
        satellite: EarthSatellite,
        timestamp: datetime | None = None,
    ) -> SatellitePosition | None:
        """Propagate satellite position to a given time.

        Args:
            satellite: EarthSatellite object.
            timestamp: Target timestamp. If None, use current UTC time.

        Returns:
            SatellitePosition or None if propagation fails.
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        
        # Ensure timestamp has timezone for skyfield, if naive assume UTC
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)

        t = self.ts.from_datetime(timestamp)
        
        try:
            # Compute position
            geocentric = satellite.at(t)
            
            # Ground position
            subpoint = wgs84.subpoint(geocentric)
            
            latitude = subpoint.latitude.degrees
            longitude = subpoint.longitude.degrees
            altitude = subpoint.elevation.km
            
            # Velocity
            vx, vy, vz = geocentric.velocity.km_per_s
            velocity_mag = (vx**2 + vy**2 + vz**2) ** 0.5
            
            # Calculate TLE age
            tle_age = t - satellite.epoch
            
            return SatellitePosition(
                norad_id=satellite.model.satnum,
                name=satellite.name,
                latitude=latitude,
                longitude=longitude,
                altitude=altitude,
                timestamp=timestamp.replace(tzinfo=None),
                tle_age_days=tle_age,
                orbital_class=classify_orbit(altitude),
                velocity=velocity_mag,
            )
        except Exception:
            return None
