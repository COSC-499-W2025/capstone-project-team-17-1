"""Lightweight storage utilities used to persist analysis data."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Optional

from .logging_utils import get_logger


logger = get_logger(__name__)

DB_DIR = Path("data")
_DB_HANDLE: Optional[sqlite3.Connection] = None
_DB_PATH: Optional[Path] = None


def _initialize_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS project_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_name TEXT NOT NULL,
            classification TEXT NOT NULL,
            primary_contributor TEXT,
            snapshot JSON NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()

    # Backwards compatibility: rename project_id -> project_name if needed.
    columns = {
        row[1]
        for row in conn.execute("PRAGMA table_info(project_analysis)").fetchall()
    }
    if "project_name" not in columns and "project_id" in columns:
        conn.execute("ALTER TABLE project_analysis RENAME COLUMN project_id TO project_name")
        conn.commit()


def open_db(base_dir: Path | None = None) -> sqlite3.Connection:
    """Open (or create) a sqlite database stored under the configured directory."""

    global _DB_HANDLE, _DB_PATH

    target_dir = base_dir or DB_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    db_path = target_dir / "capstone.db"

    if _DB_HANDLE is not None and _DB_PATH == db_path:
        logger.debug("Reusing existing database handle at %s", db_path)
        return _DB_HANDLE

    if _DB_HANDLE is not None:
        try:
            _DB_HANDLE.close()
        except Exception:  # pragma: no cover - defensive close
            logger.warning("Failed to close previous database handle", exc_info=True)

    logger.info("Opening database at %s", db_path)
    _DB_PATH = db_path
    _DB_HANDLE = sqlite3.connect(db_path)
    _initialize_schema(_DB_HANDLE)
    return _DB_HANDLE


def close_db() -> None:
    """Close the shared database handle if it exists."""

    global _DB_HANDLE, _DB_PATH
    if _DB_HANDLE is not None:
        _DB_HANDLE.close()
    _DB_HANDLE = None
    _DB_PATH = None


def store_analysis_snapshot(
    conn: sqlite3.Connection,
    project_name: str,
    classification: str,
    primary_contributor: str | None,
    snapshot: dict,
) -> None:
    """Persist a project analysis snapshot to the database."""

    payload = json.dumps(snapshot)
    conn.execute(
        """
        INSERT INTO project_analysis (project_name, classification, primary_contributor, snapshot)
        VALUES (?, ?, ?, ?)
        """,
        (project_name, classification, primary_contributor, payload),
    )
    conn.commit()


def fetch_latest_snapshot(conn: sqlite3.Connection, project_name: str) -> dict | None:
    """Return the most recent snapshot for the given project, if any."""

    cursor = conn.execute(
        """
        SELECT snapshot
        FROM project_analysis
        WHERE project_name = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (project_name,),
    )
    row = cursor.fetchone()
    return json.loads(row[0]) if row else None


def fetch_latest_snapshots(conn: sqlite3.Connection) -> dict[str, dict]:
    """Return the latest snapshot for each project currently stored."""

    cursor = conn.execute(
        """
        SELECT project_name, snapshot
        FROM project_analysis
        ORDER BY project_name ASC, created_at DESC, id DESC
        """
    )
    snapshots: dict[str, dict] = {}
    for project_name, payload in cursor:
        # Results are sorted newest-first per project, so first hit wins.
        if project_name in snapshots:
            continue
        try:
            # Pick only the first row per project thanks to ORDER BY above.
            snapshots[project_name] = json.loads(payload)
        except json.JSONDecodeError:  # pragma: no cover - defensive parsing
            logger.warning("Skipping invalid snapshot payload for project %s", project_name)
    return snapshots


__all__ = [
    "open_db",
    "close_db",
    "DB_DIR",
    "store_analysis_snapshot",
    "fetch_latest_snapshot",
    "fetch_latest_snapshots",
]
