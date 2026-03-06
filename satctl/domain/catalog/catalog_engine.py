"""Domain engine for satellite catalog intelligence."""

from __future__ import annotations
import logging
from typing import List, Dict, Optional
from satctl.domain.models import SatelliteRecord, AnomalyRecord

logger = logging.getLogger(__name__)

class CatalogEngine:
    """Handles metadata merging, deduplication, and discovery rules."""

    # Section 4.2 Priority Rules
    PRIORITY = {
        "spacetrack": 1,
        "satcat": 2,
        "ucs": 3,
        "celestrak": 4
    }

    def merge_records(self, records: List[SatelliteRecord]) -> SatelliteRecord:
        """Merge conflicting records for a single NORAD ID based on source priority."""
        if not records:
            raise ValueError("Cannot merge empty record list")

        # Sort records by priority (lower number is higher priority)
        sorted_records = sorted(
            records, 
            key=lambda x: self.PRIORITY.get(x.source.lower(), 99)
        )

        # Start with the highest priority as base
        base = sorted_records[0]
        
        # Merge-in missing fields from lower priority sources
        merged = SatelliteRecord(
            norad_id=base.norad_id,
            name=base.name,
            source=base.source,
            object_type=base.object_type,
            owner_code=base.owner_code,
            owner_name=base.owner_name,
            operator=base.operator,
            orbit_class=base.orbit_class,
            launch_date=base.launch_date,
            last_seen_at=base.last_seen_at
        )

        for other in sorted_records[1:]:
            if merged.object_type is None: merged.object_type = other.object_type
            if merged.owner_code is None: merged.owner_code = other.owner_code
            if merged.owner_name is None: merged.owner_name = other.owner_name
            if merged.operator is None: merged.operator = other.operator
            if merged.orbit_class is None: merged.orbit_class = other.orbit_class
            if merged.launch_date is None: merged.launch_date = other.launch_date
            if merged.last_seen_at is None: merged.last_seen_at = other.last_seen_at

        # Resolve Unknowns
        if not merged.owner_code:
            merged.owner_code = "UNK"
        if not merged.owner_name:
            merged.owner_name = "Unknown"

        return merged

    def detect_discoveries(self, new_norad_ids: List[int], source: str) -> List[AnomalyRecord]:
        """Generate NEW_OBJECT anomalies for previously unseen NORAD IDs."""
        anomalies = []
        import datetime
        now = datetime.datetime.utcnow()
        
        for nid in new_norad_ids:
            # Severity depends on volume - if it's a huge batch, maybe MED. 
            # If individual, LOW/MED.
            severity = "MED" if len(new_norad_ids) < 5 else "LOW"
            
            anomalies.append(AnomalyRecord(
                ts=now,
                severity=severity,
                type="NEW_OBJECT",
                title=f"New object discovered: NORAD {nid}",
                norad_id=nid,
                details={"source": source, "discovery_batch_size": len(new_norad_ids)},
                fingerprint=f"NEW_OBJECT_{nid}"
            ))
        return anomalies
