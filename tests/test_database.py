"""Tests for database functionality."""

import pytest
import tempfile
from datetime import datetime
from pathlib import Path

from satctl.database.models import Satellite, TLE
from satctl.database.schema import create_database, get_engine
from satctl.database.repository import SatelliteRepository, TLERepository


class TestDatabase:
    """Tests for database operations."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            create_database(db_path)
            yield db_path

    def test_create_database(self, temp_db):
        """Test database creation."""
        assert temp_db.exists()

    def test_satellite_repository(self, temp_db):
        """Test satellite repository operations."""
        repo = SatelliteRepository(temp_db)

        # Test upsert (create)
        sat = repo.upsert_satellite(
            norad_id=25544,
            name="ISS (ZARYA)",
            source="test",
        )

        assert sat.norad_id == 25544
        assert sat.name == "ISS (ZARYA)"

        # Test upsert (update)
        sat = repo.upsert_satellite(
            norad_id=25544,
            name="ISS",
            source="test",
        )

        assert sat.name == "ISS"

        # Test get
        sat = repo.get_satellite(25544)
        assert sat is not None
        assert sat.name == "ISS"

        # Test get all
        sats = repo.get_all_satellites()
        assert len(sats) == 1

        # Test count
        count = repo.get_satellite_count()
        assert count == 1

    def test_tle_repository(self, temp_db):
        """Test TLE repository operations."""
        sat_repo = SatelliteRepository(temp_db)
        tle_repo = TLERepository(temp_db)

        # Create satellite first
        sat_repo.upsert_satellite(25544, "ISS", "test")

        # Insert TLE
        epoch = datetime.utcnow()
        tle = tle_repo.upsert_tle(
            norad_id=25544,
            epoch=epoch,
            line1="1 25544U 98067A   24064.50000000  .00016717  00000-0  30000-3 0  9993",
            line2="2 25544  51.6400 208.9166 0006707  35.0742 325.0284 15.49820237440256",
        )

        assert tle.norad_id == 25544
        assert tle.epoch == epoch

        # Get latest TLE
        latest = tle_repo.get_latest_tle(25544)
        assert latest is not None
        assert latest.norad_id == 25544

    def test_search_by_name(self, temp_db):
        """Test satellite search by name."""
        repo = SatelliteRepository(temp_db)

        # Add satellites
        repo.upsert_satellite(25544, "ISS (ZARYA)", "test")
        repo.upsert_satellite(47401, "Starlink 1001", "test")
        repo.upsert_satellite(47402, "Starlink 1002", "test")

        # Search
        results = repo.get_satellites_by_name("starlink")
        assert len(results) == 2

        results = repo.get_satellites_by_name("iss")
        assert len(results) == 1
