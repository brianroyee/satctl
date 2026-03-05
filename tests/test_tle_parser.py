"""Tests for TLE parser."""

import pytest
from datetime import datetime

from satctl.sync.tle_parser import (
    parse_tle_line,
    parse_tle,
    parse_tle_file,
    validate_tle_line,
)


class TestTLEParser:
    """Tests for TLE parsing functions."""

    def test_parse_tle_line(self):
        """Test parsing NORAD ID and epoch from TLE lines."""
        # ISS TLE (sample)
        line1 = "1 25544U 98067A   24064.50000000  .00016717  00000-0  30000-3 0  9999"
        line2 = "2 25544  51.6400 208.9166 0006707  35.0742 325.0284 15.49820237440251"

        norad_id, epoch = parse_tle_line(line1, line2)

        assert norad_id == 25544
        assert isinstance(epoch, datetime)

    def test_parse_tle(self):
        """Test parsing complete TLE data."""
        line1 = "1 25544U 98067A   24064.50000000  .00016717  00000-0  30000-3 0  9993"
        line2 = "2 25544  51.6400 208.9166 0006707  35.0742 325.0284 15.49820237440256"
        name = "ISS (ZARYA)"

        tle = parse_tle(line1, line2, name)

        assert tle.norad_id == 25544
        assert tle.name == "ISS (ZARYA)"
        assert tle.inclination == 51.6400
        assert tle.eccentricity == 0.0006707
        assert tle.mean_motion == 15.49820237

    def test_parse_tle_file(self):
        """Test parsing TLE file content."""
        content = """ISS (ZARYA)
1 25544U 98067A   24064.50000000  .00016717  00000-0  30000-3 0  9993
2 25544  51.6400 208.9166 0006707  35.0742 325.0284 15.49820237440256

STARLINK-1001
1 47401U 21001A   24064.50000000  .00000000  00000-0  00000+0 0  9991
2 47401  53.0550 100.0000 0001000   0.0000 100.0000 15.75000000000000
"""
        tles = list(parse_tle_file(content))

        assert len(tles) == 2
        assert tles[0].name == "ISS (ZARYA)"
        assert tles[1].name == "STARLINK-1001"

    def test_validate_tle_line(self):
        """Test TLE checksum validation."""
        # Valid TLE line with correct checksum
        line1 = "1 25544U 98067A   24064.50000000  .00016717  00000-0  30000-3 0  9999"
        line2 = "2 25544  51.6400 208.9166 0006707  35.0742 325.0284 15.49820237440251"

        assert validate_tle_line(line1, 1)
        assert validate_tle_line(line2, 2)
        assert not validate_tle_line(line1, 2)

    def test_tle_age(self):
        """Test TLE age calculation."""
        line1 = "1 25544U 98067A   24064.50000000  .00016717  00000-0  30000-3 0  9993"
        line2 = "2 25544  51.6400 208.9166 0006707  35.0742 325.0284 15.49820237440256"
        name = "ISS (ZARYA)"

        tle = parse_tle(line1, line2, name)

        # TLE should have age property
        assert hasattr(tle, 'tle_age_days')
        assert tle.tle_age_days >= 0
