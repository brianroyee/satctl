"""SATCAT provider placeholder.

This module exists to satisfy the architecture contract and future expansion.
"""

from __future__ import annotations


class SatcatProvider:
    async def fetch_metadata(self) -> tuple[list[dict], str | None]:
        """Return empty metadata until SATCAT integration is implemented."""
        return [], "SATCAT provider not yet wired; continuing with available sources."
