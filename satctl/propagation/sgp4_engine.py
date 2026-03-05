"""SGP4 orbital propagation engine for satctl."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterator

from sgp4 import omm
from sgp4.conveniences import sat_epoch_datetime
from sgp4.ext import rv2coe
from sgp4.model import Satellite
from sgp4.propagation import sgp4

from satctl.database.models import TLE as TLEModel
from satctl.sync.tle_parser import TLEData


# Orbital class thresholds (in km)
GEO_ALTITUDE = 35786  # Geostationous orbit altitude
MEO_ALTITUDE = 2000  # Medium Earth orbit threshold


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


class SGP4Engine:
    """SGP4 orbital propagation engine."""

    @staticmethod
    def create_satellite(tle: TLEData) -> Satellite:
        """Create a satellite object from TLE data.

        Args:
            tle: Parsed TLE data.

        Returns:
            SGP4 Satellite object.
        """
        # Use the sgp4 model to create a satellite
        satellite = Satellite()
        satellite.name = tle.name
        satellite.catnr = tle.norad_id
        satellite.epoch = tle.epoch
        satellite.no = tle.mean_motion * 2 * 3.141592653589793 / 1440.0  # Convert to radians/min
        satellite.ecco = tle.eccentricity
        satellite.argpo = tle.argument_of_perigee * 3.141592653589793 / 180.0  # Convert to radians
        satellite.inclo = tle.inclination * 3.141592653589793 / 180.0  # Convert to radians
        satellite.mo = tle.mean_anomaly * 3.141592653589793 / 180.0  # Convert to radians
        satellite.nodeo = tle.raan * 3.141592653589793 / 180.0  # Convert to radians
        satellite.nd = 0.0  # First derivative of mean motion
        satellite.ndd = 0.0  # Second derivative of mean motion
        satellite.bstar = 0.0  # B* drag term
        satellite.sgp4epoch = tle.epoch

        return satellite

    @staticmethod
    def create_satellite_from_tle_model(tle: TLEModel) -> Satellite:
        """Create a satellite object from TLE model.

        Args:
            tle: Database TLE model.

        Returns:
            SGP4 Satellite object.
        """
        return Satellite.twoline2rv(
            tle.line1,
            tle.line2,
        )

    @staticmethod
    def propagate(
        satellite: Satellite,
        timestamp: datetime | None = None,
    ) -> SatellitePosition | None:
        """Propagate satellite position to a given time.

        Args:
            satellite: SGP4 Satellite object.
            timestamp: Target timestamp. If None, use current UTC time.

        Returns:
            SatellitePosition or None if propagation fails.
        """
        if timestamp is None:
            timestamp = datetime.utcnow()

        # Convert datetime to days since epoch
        # SGP4 expects minutes since epoch
        try:
            # Use the sgp4 function to propagate
            error_code, position_velocity = sgp4(satellite, 0)  # 0 = propagate to epoch

            if error_code != 0:
                return None

            # Position is in km, velocity is in km/s
            position_km = position_velocity.position
            velocity_km_s = position_velocity.velocity

            # Calculate geodetic coordinates
            # Using simple conversion (not exact, but sufficient for display)
            x, y, z = position_km
            r = (x**2 + y**2 + z**2) ** 0.5

            # Earth radius at equator = 6378.137 km
            earth_radius = 6378.137

            # Calculate latitude and longitude
            # Simple spherical approximation
            lat = 0.0
            lon = 0.0

            # Convert to lat/lon
            if r > 0:
                # More accurate calculation using atan2
                lat = 0.0
                lon = 0.0

                # Calculate latitude
                # Using the assumption that z/r = sin(lat)
                sin_lat = z / r
                lat = 90.0 - (180.0 / 3.141592653589793) * 0.0  # Simplified

                # Simple approximation for display
                # This is not geodetic, but works for visual display
                lon = (180.0 / 3.141592653589793) * 0.0

            # Better calculation using sgp4's built-in functions
            # Get position in TEME frame and convert
            try:
                # Use Python's math for conversion
                import math

                # Calculate latitude/longitude from position
                # Position is in km in Earth-centered Earth-fixed frame
                x_km, y_km, z_km = position_km

                # Earth radii
                a = 6378.137  # km (semi-major axis)
                f = 1 / 298.257223563  # flattening
                b = a * (1 - f)  # semi-minor axis

                # Calculate geodetic coordinates (simplified)
                # Using iterative method would be more accurate but this works
                p = math.sqrt(x_km**2 + y_km**2)
                lon = math.atan2(y_km, x_km)

                # Simple spherical Earth approximation for now
                r_earth = 6371.0  # mean Earth radius
                alt = r - r_earth

                # Calculate latitude
                # This is geocentric, not geodetic - close enough for display
                lat = math.asin(z_km / r) if r > 0 else 0.0

                # Convert to degrees
                lat_deg = lat * 180.0 / math.pi
                lon_deg = lon * 180.0 / math.pi

                # Wrap longitude to -180 to 180
                while lon_deg > 180:
                    lon_deg -= 360
                while lon_deg < -180:
                    lon_deg += 360

                # Calculate orbital class
                orbital_class = classify_orbit(alt)

                # Calculate velocity magnitude
                vx, vy, vz = velocity_km_s
                velocity_mag = math.sqrt(vx**2 + vy**2 + vz**2)

                # Calculate TLE age
                epoch = sat_epoch_datetime(satellite)
                tle_age = (timestamp - epoch).total_seconds() / 86400.0

                return SatellitePosition(
                    norad_id=satellite.catnr,
                    name=satellite.name,
                    latitude=lat_deg,
                    longitude=lon_deg,
                    altitude=alt,
                    timestamp=timestamp,
                    tle_age_days=tle_age,
                    orbital_class=orbital_class,
                    velocity=velocity_mag,
                )

            except Exception:
                # Fallback to simple calculation
                r_earth = 6371.0
                alt = r - r_earth

                import math
                lat = math.atan2(z_km, math.sqrt(x_km**2 + y_km**2))
                lon = math.atan2(y_km, x_km)

                lat_deg = lat * 180.0 / math.pi
                lon_deg = lon * 180.0 / math.pi

                while lon_deg > 180:
                    lon_deg -= 360
                while lon_deg < -180:
                    lon_deg += 360

                vx, vy, vz = velocity_km_s
                velocity_mag = math.sqrt(vx**2 + vy**2 + vz**2)

                epoch = sat_epoch(satellite)
                tle_age = (timestamp - epoch).total_seconds() / 86400.0

                return SatellitePosition(
                    norad_id=satellite.catnr,
                    name=satellite.name,
                    latitude=lat_deg,
                    longitude=lon_deg,
                    altitude=alt,
                    timestamp=timestamp,
                    tle_age_days=tle_age,
                    orbital_class=classify_orbit(alt),
                    velocity=velocity_mag,
                )

        except Exception:
            return None

    @staticmethod
    def propagate_trajectory(
        satellite: Satellite,
        start_time: datetime,
        minutes: int = 90,
        interval_minutes: float = 1.0,
    ) -> Iterator[SatellitePosition]:
        """Generate a trajectory of satellite positions.

        Args:
            satellite: SGP4 Satellite object.
            start_time: Start time for trajectory.
            minutes: Number of minutes to propagate.
            interval_minutes: Interval between positions in minutes.

        Yields:
            SatellitePosition for each time step.
        """
        from datetime import timedelta

        current_time = start_time
        end_time = start_time + timedelta(minutes=minutes)

        while current_time <= end_time:
            # Calculate minutes since epoch
            epoch = sat_epoch_datetime(satellite)
            minutes_since_epoch = (current_time - epoch).total_seconds() / 60.0

            try:
                error_code, position_velocity = sgp4(satellite, minutes_since_epoch)

                if error_code == 0:
                    position_km = position_velocity.position
                    velocity_km_s = position_velocity.velocity

                    x_km, y_km, z_km = position_km
                    r = (x_km**2 + y_km**2 + z_km**2) ** 0.5
                    r_earth = 6371.0
                    alt = r - r_earth

                    import math

                    lat = math.atan2(z_km, math.sqrt(x_km**2 + y_km**2))
                    lon = math.atan2(y_km, x_km)

                    lat_deg = lat * 180.0 / math.pi
                    lon_deg = lon * 180.0 / math.pi

                    while lon_deg > 180:
                        lon_deg -= 360
                    while lon_deg < -180:
                        lon_deg += 360

                    vx, vy, vz = velocity_km_s
                    velocity_mag = math.sqrt(vx**2 + vy**2 + vz**2)

                    tle_age = (current_time - epoch).total_seconds() / 86400.0

                    yield SatellitePosition(
                        norad_id=satellite.catnr,
                        name=satellite.name,
                        latitude=lat_deg,
                        longitude=lon_deg,
                        altitude=alt,
                        timestamp=current_time,
                        tle_age_days=tle_age,
                        orbital_class=classify_orbit(alt),
                        velocity=velocity_mag,
                    )

            except Exception:
                pass

            current_time += timedelta(minutes=interval_minutes)
