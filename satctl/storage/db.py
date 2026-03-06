"""Database engine and session management for SIGINT-first architecture."""

from __future__ import annotations

from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from satctl.storage.models import Base


def create_database(db_path: Path) -> None:
    """Create the database and tables.
    
    Ensures all SIGINT-first tables and columns are present, handling
    migrations from legacy 'satctl' versions.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 1. Run structural migrations before SQLAlchemy takes over
    _migrate_database(db_path)
    
    # 2. Create/Update tables using SQLAlchemy
    # Use absolute posix path for standard sqlite URI format
    uri = f"sqlite:///{db_path.absolute().as_posix()}"
    engine = create_engine(uri, echo=False)
    Base.metadata.create_all(engine)


def _migrate_database(db_path: Path) -> None:
    """Manually handle structural migrations for legacy database versions."""
    if not db_path.exists():
        return

    import sqlite3
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get existing tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}

    # 1. Rename 'satellite' (old) to 'satellites' (new)
    if "satellite" in tables and "satellites" not in tables:
        cursor.execute("ALTER TABLE satellite RENAME TO satellites")
        tables.remove("satellite")
        tables.add("satellites")

    # 2. Migrate 'satellites' columns
    if "satellites" in tables:
        cursor.execute("PRAGMA table_info(satellites)")
        cols = {row[1] for row in cursor.fetchall()}
        
        # Renames
        if "country_code" in cols and "owner_code" not in cols:
            cursor.execute("ALTER TABLE satellites RENAME COLUMN country_code TO owner_code")
            cols.remove("country_code")
            cols.add("owner_code")
        if "orbit_type" in cols and "orbit_class" not in cols:
            cursor.execute("ALTER TABLE satellites RENAME COLUMN orbit_type TO orbit_class")
            cols.remove("orbit_type")
            cols.add("orbit_class")
        
        # New Additions
        for col_name, col_type in [
            ("owner_name", "VARCHAR(255)"),
            ("operator", "VARCHAR(255)"),
            ("object_type", "VARCHAR(50)"),
            ("orbit_class", "VARCHAR(50)"),
            ("launch_date", "DATETIME"),
            ("last_seen_at", "DATETIME"),
            ("source", "VARCHAR(100)"),
        ]:
            if col_name not in cols:
                cursor.execute(f"ALTER TABLE satellites ADD COLUMN {col_name} {col_type}")

    # 3. Migrate 'sources' columns
    if "sources" in tables:
        cursor.execute("PRAGMA table_info(sources)")
        src_cols = {row[1] for row in cursor.fetchall()}
        
        if "name" in src_cols and "source_name" not in src_cols:
            cursor.execute("ALTER TABLE sources RENAME COLUMN name TO source_name")
            src_cols.remove("name")
            src_cols.add("source_name")
        if "last_sync" in src_cols and "last_sync_at" not in src_cols:
            cursor.execute("ALTER TABLE sources RENAME COLUMN last_sync TO last_sync_at")
            src_cols.remove("last_sync")
            src_cols.add("last_sync_at")
            
        for col_name, col_type in [
            ("last_status", "VARCHAR(50)"),
            ("record_count", "INTEGER DEFAULT 0"),
            ("notes", "TEXT"),
        ]:
            if col_name not in src_cols:
                cursor.execute(f"ALTER TABLE sources ADD COLUMN {col_name} {col_type}")

    # 4. Handle TLE column 'fetched_at' -> 'ingested_at'
    if "tle" in tables:
        cursor.execute("PRAGMA table_info(tle)")
        tle_cols = {row[1] for row in cursor.fetchall()}
        if "fetched_at" in tle_cols and "ingested_at" not in tle_cols:
            cursor.execute("ALTER TABLE tle RENAME COLUMN fetched_at TO ingested_at")
            tle_cols.remove("fetched_at")
            tle_cols.add("ingested_at")
        
        if "ingested_at" not in tle_cols:
            cursor.execute("ALTER TABLE tle ADD COLUMN ingested_at DATETIME")

    conn.commit()
    conn.close()


def get_session(db_path: Path) -> Session:
    """Get a new database session."""
    uri = f"sqlite:///{db_path.absolute().as_posix()}"
    engine = create_engine(uri, echo=False)
    SessionFactory = sessionmaker(bind=engine)
    return SessionFactory()
