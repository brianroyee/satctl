"""Coordinate utilities for satctl."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class Coordinate:
    """Geographic coordinate."""

    latitude: float  # degrees, -90 to 90
    longitude: float  # degrees, -180 to 180

    def is_valid(self) -> bool:
        """Check if coordinate is valid."""
        return -90 <= self.latitude <= 90 and -180 <= self.longitude <= 180


def geodesic_distance(coord1: Coordinate, coord2: Coordinate) -> float:
    """Calculate geodesic distance between two points using Haversine formula.

    Args:
        coord1: First coordinate.
        coord2: Second coordinate.

    Returns:
        Distance in kilometers.
    """
    R = 6371.0  # Earth radius in km

    lat1 = math.radians(coord1.latitude)
    lat2 = math.radians(coord2.latitude)
    dlat = math.radians(coord2.latitude - coord1.latitude)
    dlon = math.radians(coord2.longitude - coord1.longitude)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def is_in_bounding_box(
    coord: Coordinate,
    min_lat: float,
    max_lat: float,
    min_lon: float,
    max_lon: float,
) -> bool:
    """Check if coordinate is inside a bounding box.

    Args:
        coord: Coordinate to check.
        min_lat: Minimum latitude.
        max_lat: Maximum latitude.
        min_lon: Minimum longitude.
        max_lon: Maximum longitude.

    Returns:
        True if inside bounding box.
    """
    return min_lat <= coord.latitude <= max_lat and min_lon <= coord.longitude <= max_lon


def is_in_radius(
    coord: Coordinate,
    center: Coordinate,
    radius_km: float,
) -> bool:
    """Check if coordinate is within a radius of a center point.

    Args:
        coord: Coordinate to check.
        center: Center coordinate.
        radius_km: Radius in kilometers.

    Returns:
        True if within radius.
    """
    distance = geodesic_distance(coord, center)
    return distance <= radius_km


def format_latitude(lat: float) -> str:
    """Format latitude for display."""
    direction = "N" if lat >= 0 else "S"
    return f"{abs(lat):.4f}°{direction}"


def format_longitude(lon: float) -> str:
    """Format longitude for display."""
    direction = "E" if lon >= 0 else "W"
    return f"{abs(lon):.4f}°{direction}"


def format_altitude(alt: float) -> str:
    """Format altitude for display."""
    return f"{alt:.1f} km"


def format_distance(dist_km: float) -> str:
    """Format distance for display."""
    if dist_km < 1:
        return f"{dist_km * 1000:.0f} m"
    elif dist_km < 1000:
        return f"{dist_km:.1f} km"
    else:
        return f"{dist_km / 1000:.1f} thousand km"
