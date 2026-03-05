"""Tests for SGP4 propagation engine."""

import pytest
from datetime import datetime, timedelta

from satctl.propagation.sgp4_engine import SGP4Engine, classify_orbit
from satctl.propagation.utils import (
    geodesic_distance,
    is_in_bounding_box,
    is_in_radius,
    Coordinate,
)


class TestSGP4Engine:
    """Tests for SGP4 propagation."""

    def test_classify_orbit(self):
        """Test orbital classification based on altitude."""
        assert classify_orbit(400) == "LEO"   # ISS altitude
        assert classify_orbit(2000) == "MEO"  # GPS altitude
        assert classify_orbit(35786) == "GEO"  # Geostationous
        assert classify_orbit(40000) == "GTO"  # Beyond GEO


class TestCoordinateUtils:
    """Tests for coordinate utilities."""

    def test_geodesic_distance(self):
        """Test geodesic distance calculation."""
        # New York to London (approximately)
        ny = Coordinate(40.7128, -74.0060)
        london = Coordinate(51.5074, -0.1278)

        distance = geodesic_distance(ny, london)

        # Should be approximately 5570 km
        assert 5500 < distance < 5700

    def test_is_in_bounding_box(self):
        """Test bounding box check."""
        coord = Coordinate(45.0, -75.0)

        # Inside box
        assert is_in_bounding_box(coord, 40, 50, -80, -70)

        # Outside box
        assert not is_in_bounding_box(coord, 40, 50, -70, -60)

    def test_is_in_radius(self):
        """Test radius check."""
        center = Coordinate(0.0, 0.0)
        coord = Coordinate(0.0, 0.0)  # Same point

        # Same point should be at distance 0
        assert is_in_radius(coord, center, 1000)

        # Point far away should not be in radius
        far_point = Coordinate(45.0, 45.0)
        assert not is_in_radius(far_point, center, 100)

    def test_coordinate_validation(self):
        """Test coordinate validation."""
        valid = Coordinate(45.0, -75.0)
        assert valid.is_valid()

        invalid_lat = Coordinate(100.0, 0.0)
        assert not invalid_lat.is_valid()

        invalid_lon = Coordinate(0.0, 200.0)
        assert not invalid_lon.is_valid()
