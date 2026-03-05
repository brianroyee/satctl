"""Region definitions for satctl."""

from __future__ import annotations

from abc import ABC, abstractmethod


class Region(ABC):
    """Base class for all regions."""

    @abstractmethod
    def contains(self, lat: float, lon: float) -> bool:
        """Check if a coordinate is inside the region.

        Args:
            lat: Latitude in degrees.
            lon: Longitude in degrees.

        Returns:
            True if inside, False otherwise.
        """
        pass


class BBoxRegion(Region):
    """Bounding box region."""

    def __init__(self, min_lat: float, max_lat: float, min_lon: float, max_lon: float):
        """Initialize bounding box region.

        Args:
            min_lat: Minimum latitude in degrees.
            max_lat: Maximum latitude in degrees.
            min_lon: Minimum longitude in degrees.
            max_lon: Maximum longitude in degrees.
        """
        self.min_lat = min_lat
        self.max_lat = max_lat
        self.min_lon = min_lon
        self.max_lon = max_lon

    def contains(self, lat: float, lon: float) -> bool:
        return self.min_lat <= lat <= self.max_lat and self.min_lon <= lon <= self.max_lon


class RadiusRegion(Region):
    """Circular radius region."""

    def __init__(self, center_lat: float, center_lon: float, radius_km: float):
        """Initialize radius region.

        Args:
            center_lat: Center latitude in degrees.
            center_lon: Center longitude in degrees.
            radius_km: Radius in kilometers.
        """
        self.center_lat = center_lat
        self.center_lon = center_lon
        self.radius_km = radius_km

    def contains(self, lat: float, lon: float) -> bool:
        from satctl.propagation.utils import Coordinate, geodesic_distance

        center = Coordinate(self.center_lat, self.center_lon)
        point = Coordinate(lat, lon)
        return geodesic_distance(center, point) <= self.radius_km


# Predefined bounding boxes for countries (simplified)
COUNTRY_BBOXES = {
    "india": (8.4, 37.6, 68.7, 97.25),
    "usa": (24.396308, 49.384358, -125.0, -66.93457),
    "uk": (49.8, 60.9, -8.6, 1.8),
    "australia": (-43.6, -10.1, 113.1, 153.6),
    "iran": (25.078, 39.713, 44.109, 63.316),
}


class CountryRegion(BBoxRegion):
    """Country region based on a predefined bounding box."""

    def __init__(self, country_name: str):
        """Initialize country region.

        Args:
            country_name: Name of the country (case-insensitive).
        """
        name = country_name.lower()
        if name not in COUNTRY_BBOXES:
            raise ValueError(f"Unknown country: {country_name}")
        
        min_lat, max_lat, min_lon, max_lon = COUNTRY_BBOXES[name]
        super().__init__(min_lat, max_lat, min_lon, max_lon)
        self.country_name = name

