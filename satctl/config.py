"""Configuration management for satctl."""

from __future__ import annotations

import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    """satctl configuration."""

    data_dir: Path = Path.home() / ".local" / "share" / "satctl"
    database_path: Path = Path.home() / ".local" / "share" / "satctl" / "satctl.db"

    # Default values
    default_refresh_rate: float = 1.5
    default_limit: int = 500

    @classmethod
    def default(cls) -> Config:
        """Create default configuration."""
        data_dir = Path.home() / ".local" / "share" / "satctl"
        return cls(
            data_dir=data_dir,
            database_path=data_dir / "satctl.db",
        )

    @classmethod
    def from_env(cls) -> Config:
        """Create configuration from environment variables."""
        data_dir = os.environ.get("SATCTL_DATA_DIR")
        if data_dir:
            data_dir = Path(data_dir)
        else:
            data_dir = Path.home() / ".local" / "share" / "satctl"

        return cls(
            data_dir=data_dir,
            database_path=data_dir / "satctl.db",
        )

    def ensure_data_dir(self) -> None:
        """Ensure the data directory exists."""
        self.data_dir.mkdir(parents=True, exist_ok=True)


# Global configuration instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config


def set_config(config: Config) -> None:
    """Set the global configuration instance."""
    global _config
    _config = config
