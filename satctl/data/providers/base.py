"""Base provider interface for satellite OSINT sources."""

import abc
from typing import List, Tuple

from satctl.data.models import NormalizedSatelliteRecord, NormalizedTLERecord


class BaseProvider(abc.ABC):
    """Abstract base class for all satellite OSINT metadata providers."""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Provider identifier name (e.g. 'celestrak', 'spacetrack')."""
        pass

    @abc.abstractmethod
    def fetch(self) -> any:
        """Fetch raw data from the provider's upstream source."""
        pass

    @abc.abstractmethod
    def parse(self, raw_data: any) -> List[any]:
        """Parse raw data into a list of individual provider records."""
        pass

    @abc.abstractmethod
    def normalize(self, provider_records: List[any]) -> Tuple[List[NormalizedSatelliteRecord], List[NormalizedTLERecord]]:
        """
        Convert provider records into unified 'NormalizedSatelliteRecord' and 'NormalizedTLERecord' formats.
        
        Returns:
            Tuple containing ([Satellite records], [TLE records]).
            Either list can be empty if the provider only supplies one type of data.
        """
        pass

    def run_pipeline(self) -> Tuple[List[NormalizedSatelliteRecord], List[NormalizedTLERecord]]:
        """Run the full fetch -> parse -> normalize pipeline."""
        raw = self.fetch()
        parsed = self.parse(raw)
        return self.normalize(parsed)
