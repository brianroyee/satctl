"""Propagation module for satctl."""

try:
    from satctl.propagation.skyfield_engine import SkyfieldEngine, SatellitePosition
except ModuleNotFoundError:  # Optional dependency for minimal installs/tests
    SkyfieldEngine = None
    SatellitePosition = None

__all__ = ["SkyfieldEngine", "SatellitePosition"]
