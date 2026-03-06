"""Domain behavior models for SIGINT-first architecture."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any


@dataclass
class SatelliteRecord:
    """Consolidated satellite record from domain engines."""
    norad_id: int
    name: str
    source: str
    object_type: Optional[str] = None
    owner_code: Optional[str] = None
    owner_name: Optional[str] = None
    operator: Optional[str] = None
    orbit_class: Optional[str] = None
    launch_date: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None


@dataclass
class TLERecord:
    """Satellite orbital elements."""
    norad_id: int
    line1: str
    line2: str
    epoch: datetime
    source: str


@dataclass
class TransmitterRecord:
    """Signal intelligence transmitter metadata."""
    norad_id: Optional[int]
    name: Optional[str]
    description: Optional[str] = None
    downlink_freq_hz: Optional[float] = None
    uplink_freq_hz: Optional[float] = None
    mode: Optional[str] = None
    bandwidth_hz: Optional[float] = None
    source: str = "satnogs"


@dataclass
class ObservationRecord:
    """A signal observation event."""
    ts: datetime
    norad_id: Optional[int]
    tx_id: Optional[int]
    source: str
    station_id: Optional[str] = None
    region_tag: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AnomalyRecord:
    """A detected anomaly."""
    ts: datetime
    severity: str # LOW, MED, HIGH
    type: str # RF_APPEAR, NEW_OBJECT, etc
    title: str
    norad_id: Optional[int] = None
    tx_id: Optional[int] = None
    details: Dict[str, Any] = field(default_factory=dict)
    fingerprint: str = ""
