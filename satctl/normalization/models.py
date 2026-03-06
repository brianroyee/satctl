"""Normalized internal data models for provider outputs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class SatelliteRecord:
    norad_id: int
    name: str
    source: str


@dataclass(frozen=True)
class TLERecord:
    norad_id: int
    name: str
    line1: str
    line2: str
    epoch: datetime
    source: str


@dataclass(frozen=True)
class TransmitterRecord:
    tx_id: str
    norad_id: int
    frequency: float
    mode: str | None
    bandwidth: float | None
    source: str
    confidence: float = 0.8


@dataclass(frozen=True)
class ObservationRecord:
    norad_id: int
    tx_id: str | None
    source: str
    region: str | None = None
    station_id: str | None = None
    metadata: str | None = None
