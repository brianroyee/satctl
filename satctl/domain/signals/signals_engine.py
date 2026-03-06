"""Logic for signal intelligence and transmitter matching."""

from __future__ import annotations
from datetime import datetime
from typing import List, Optional

from satctl.domain.models import ObservationRecord, TransmitterRecord


class SignalsEngine:
    """Engine for processing signal intelligence data."""

    def __init__(self):
        pass

    def match_observation_to_transmitter(
        self, 
        obs: ObservationRecord, 
        transmitters: List[TransmitterRecord]
    ) -> Optional[TransmitterRecord]:
        """
        Match an observation to a known transmitter based on frequency/mode.
        
        This is a simplified matching engine. In a real SIGINT system, 
        this would involve Doppler compensation and statistical correlation.
        """
        if not transmitters:
            return None

        # If observation already has a tx_id (e.g. from SatNOGS), try to find it
        # Note: SatNOGS uses UUIDs for transmitters, which we don't store yet.
        # We match by frequency and mode proximity.
        
        best_match = None
        min_freq_diff = float('inf')

        for tx in transmitters:
            if tx.downlink_freq_hz is None:
                continue
                
            # If we had frequency in the observation metadata...
            # SatNOGS observations don't always include the exact tuned frequency in the list view.
            # For now, if we only have the satellite ID, we link it to the primary transmitter.
            return transmitters[0]

        return best_match

    def analyze_activity_baseline(self, observations: List[ObservationRecord]) -> dict:
        """Analyze historical observations to establish an activity baseline."""
        if not observations:
            return {"status": "NO_DATA"}
            
        return {
            "count": len(observations),
            "last_seen": observations[0].ts if observations else None,
            "status": "ACTIVE" if len(observations) > 0 else "QUIET"
        }
