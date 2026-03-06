"""Configuration management for satctl."""

from __future__ import annotations

import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    """satctl configuration."""

    data_dir: Path = Path.home() / ".satctl"
    database_path: Path = Path.home() / ".satctl" / "satctl.db"
    cache_dir: Path = Path.home() / ".satctl" / "cache"

    default_refresh_rate: float = 1.5
    default_limit: int = 500

    @classmethod
    def from_env(cls) -> Config:
        data_dir = Path(os.environ.get("SATCTL_DATA_DIR", str(Path.home() / ".satctl")))
        return cls(data_dir=data_dir, database_path=data_dir / "satctl.db", cache_dir=data_dir / "cache")

    def ensure_data_dir(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def ensure_cache_dir(self) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)


_config: Optional[Config] = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config


def set_config(config: Config) -> None:
    global _config
    _config = config
