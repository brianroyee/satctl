"""Database schema and initialization."""

from __future__ import annotations

from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from satctl.database.models import Base


def create_database(db_path: Path) -> None:
    """Create the database and tables.

    Args:
        db_path: Path to the SQLite database file.
    """
    # Ensure parent directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Create engine
    engine = create_engine(f"sqlite:///{db_path}", echo=False)

    # Create all tables
    Base.metadata.create_all(engine)


def get_engine(db_path: Path):
    """Create and return a SQLAlchemy engine.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        SQLAlchemy engine.
    """
    return create_engine(f"sqlite:///{db_path}", echo=False)


def get_session(db_path: Path) -> Session:
    """Create and return a SQLAlchemy session.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        SQLAlchemy session.
    """
    engine = get_engine(db_path)
    Session = sessionmaker(bind=engine)
    return Session()
