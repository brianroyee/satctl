"""TLE (Two-Line Element) parser for satctl."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterator


@dataclass
class TLEData:
    """Parsed TLE data."""

    name: str
    norad_id: int
    line1: str
    line2: str
    epoch: datetime
    inclination: float  # degrees
    eccentricity: float
    raan: float  # right ascension of ascending node, degrees
    argument_of_perigee: float  # degrees
    mean_anomaly: float  # degrees
    mean_motion: float  # revolutions per day
    orbit_number: int  # revolution number at epoch

    @property
    def tle_age_days(self) -> float:
        """Calculate TLE age in days from epoch to now."""
        return (datetime.utcnow() - self.epoch).total_seconds() / 86400.0


def parse_tle_line(line1: str, line2: str) -> tuple[int, datetime]:
    """Parse NORAD ID and epoch from TLE lines.

    Args:
        line1: First TLE line.
        line2: Second TLE line.

    Returns:
        Tuple of (norad_id, epoch).
    """
    # Extract NORAD catalog number from line 1 (positions 2-7)
    norad_id = int(line1[2:7])

    # Extract epoch from line 1 (positions 18-20 for year, 21-32 for day)
    # Format: YYYY-DDD.DDDDDDDD (day of year)
    year_char = line1[18]
    year = int(year_char)
    year = 2000 + year if year < 50 else 1900 + year

    day_of_year = float(line1[20:32])
    epoch = datetime(year, 1, 1) + timedelta(days=day_of_year - 1)

    return norad_id, epoch


def parse_tle(line1: str, line2: str, name: str) -> TLEData:
    """Parse TLE data into a structured object.

    Args:
        line1: First TLE line.
        line2: Second TLE line.
        name: Satellite name.

    Returns:
        Parsed TLE data.
    """
    norad_id, epoch = parse_tle_line(line1, line2)

    # Parse line 2
    inclination = float(line2[8:16])  # degrees
    raan = float(line2[17:25])  # right ascension of ascending node
    eccentricity = float("0." + line2[26:33])  # decimal point assumed
    argument_of_perigee = float(line2[34:42])  # degrees
    mean_anomaly = float(line2[43:51])  # degrees
    mean_motion = float(line2[52:63])  # revolutions per day
    orbit_number = int(line2[63:68])

    return TLEData(
        name=name,
        norad_id=norad_id,
        line1=line1,
        line2=line2,
        epoch=epoch,
        inclination=inclination,
        eccentricity=eccentricity,
        raan=raan,
        argument_of_perigee=argument_of_perigee,
        mean_anomaly=mean_anomaly,
        mean_motion=mean_motion,
        orbit_number=orbit_number,
    )


def parse_tle_file(content: str) -> Iterator[TLEData]:
    """Parse TLE data from a file or string.

    TLE format:
    NAME
    LINE1
    LINE2

    Args:
        content: TLE file content.

    Yields:
        Parsed TLE data.
    """
    lines = content.strip().split("\n")

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Skip empty lines
        if not line:
            i += 1
            continue

        # Check if this is a name line (not starting with '1' or '2')
        if not line[0] in ("1", "2"):
            name = line.strip()
            if i + 2 < len(lines):
                line1 = lines[i + 1].strip()
                line2 = lines[i + 2].strip()

                # Validate TLE lines
                if line1.startswith("1") and line2.startswith("2"):
                    try:
                        tle = parse_tle(line1, line2, name)
                        yield tle
                        i += 3
                    except (ValueError, IndexError):
                        i += 1
                else:
                    i += 1
            else:
                i += 1
        else:
            i += 1


def validate_tle_line(line: str, expected_line_number: int) -> bool:
    """Validate a TLE line checksum.

    Args:
        line: TLE line to validate.
        expected_line_number: 1 or 2.

    Returns:
        True if checksum is valid.
    """
    if len(line) < 69:
        return False

    # Extract characters to check (everything except the checksum character)
    chars = line[:68]

    # Calculate checksum
    checksum = 0
    for char in chars:
        if char.isdigit():
            checksum += int(char)
        elif char == "-":
            checksum += 1

    # Mod 10 of checksum should equal the last character
    expected = int(line[68])
    return checksum % 10 == expected
