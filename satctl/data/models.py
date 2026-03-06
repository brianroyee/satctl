"""Normalized data models for satellite OSINT records."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class NormalizedTLERecord:
    """Normalized Two-Line Element data."""
    norad_id: int
    line1: str
    line2: str
    epoch: datetime
    source: str


@dataclass
class NormalizedSatelliteRecord:
    """Normalized satellite metadata across all sources."""
    norad_id: int
    name: str
    source: str
    object_type: Optional[str] = None
    orbit_class: Optional[str] = None
    owner_country: Optional[str] = None
    operator: Optional[str] = None
    launch_date: Optional[datetime] = None
    launch_vehicle: Optional[str] = None
    purpose: Optional[str] = None
    mass: Optional[float] = None
