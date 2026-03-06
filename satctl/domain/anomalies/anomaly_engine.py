"""Domain engine for SIGINT anomaly detection."""

from __future__ import annotations
import logging
from datetime import datetime
from typing import List, Optional

from satctl.domain.models import AnomalyRecord, ObservationRecord, TransmitterRecord

logger = logging.getLogger(__name__)

class AnomalyEngine:
    """Rule-based anomaly detector (no ML initially)."""

    def detect_rf_appearance(self, 
        transmitter: TransmitterRecord, 
        observations: List[ObservationRecord]
    ) -> Optional[AnomalyRecord]:
        """Detect if a transmitter has appeared after long inactivity."""
        if not observations:
            return None
            
        # Simplest rule: if first observation ever recorded in our system
        # In a real system, we'd compare against a historical baseline.
        return AnomalyRecord(
            ts=observations[0].ts,
            severity="MED",
            type="RF_APPEAR",
            title=f"New signal activity: {transmitter.name or 'Unknown TX'}",
            norad_id=transmitter.norad_id,
            details={"source": observations[0].source},
            fingerprint=f"RF_APPEAR_{transmitter.norad_id}_{transmitter.name}_{observations[0].ts.date()}"
        )

    def detect_rf_disappear(self,
        transmitter: TransmitterRecord,
        last_obs: Optional[ObservationRecord]
    ) -> Optional[AnomalyRecord]:
        """Detect if an expected transmitter has gone quiet."""
        if not last_obs:
            return None
            
        # If last seen more than 7 days ago
        delta = datetime.utcnow() - last_obs.ts
        if delta.days > 7:
            return AnomalyRecord(
                ts=datetime.utcnow(),
                severity="HIGH",
                type="RF_DISAPPEAR",
                title=f"Transmitter Silent: {transmitter.name or 'Unknown'}",
                norad_id=transmitter.norad_id,
                details={"last_seen": last_obs.ts.isoformat()},
                fingerprint=f"RF_DISAPPEAR_{transmitter.norad_id}_{transmitter.name}"
            )
        return None

    def detect_orbit_shift(self, 
        norad_id: int, 
        current_tle: TLERecord, 
        previous_tle: Optional[TLERecord]
    ) -> Optional[AnomalyRecord]:
        """Detect sudden jumps in orbital elements (potential maneuver)."""
        if not previous_tle:
            return None
            
        # Placeholder for real TLE delta analysis
        # In a real system, we'd check Mean Motion or Inclination shifts.
        return None

    def detect_traffic_spike(self,
        region: str,
        current_count: int,
        average_count: float
    ) -> Optional[AnomalyRecord]:
        """Detect unusual number of passes over a region."""
        if current_count > (average_count * 2) and current_count > 5:
            return AnomalyRecord(
                ts=datetime.utcnow(),
                severity="HIGH",
                type="TRAFFIC_SPIKE",
                title=f"Abnormal Activity over {region}",
                details={"current": current_count, "average": average_count},
                fingerprint=f"TRAFFIC_SPIKE_{region}_{datetime.utcnow().date()}"
            )
        return None
