"""Lightweight storage utilities used to persist analysis data."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
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
            project_id TEXT NOT NULL,
            classification TEXT NOT NULL,
            primary_contributor TEXT,
            snapshot JSON NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
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
    project_id: str,
    classification: str,
    primary_contributor: str | None,
    snapshot: dict,
) -> None:
    """Persist a project analysis snapshot to the database."""

    # make sure every stored snapshot includes the key identifiers 
    prepared_snapshot = _prepare_snapshot_payload(snapshot, project_id, classification, primary_contributor)
    payload = json.dumps(prepared_snapshot)
    try:
        cursor = conn.execute(
            """
            INSERT INTO project_analysis (project_id, classification, primary_contributor, snapshot)
            VALUES (?, ?, ?, ?)
            """,
            (project_id, classification, primary_contributor, payload),
        )
        row_id = cursor.lastrowid
        _validate_snapshot_insert(
            conn,
            row_id,
            project_id=project_id,
            classification=classification,
            primary_contributor=primary_contributor,
        )
    except Exception:
        conn.rollback()
        raise
    else:
        conn.commit()


def fetch_latest_snapshot(conn: sqlite3.Connection, project_id: str) -> dict | None:
    """Return the most recent snapshot for the given project, if any."""

    cursor = conn.execute(
        """
        SELECT snapshot
        FROM project_analysis
        WHERE project_id = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (project_id,),
    )
    row = cursor.fetchone()
    return json.loads(row[0]) if row else None


def fetch_latest_snapshots(conn: sqlite3.Connection) -> dict[str, dict]:
    """Return the latest snapshot for each project currently stored."""

    cursor = conn.execute(
        """
        SELECT project_id, snapshot
        FROM project_analysis
        ORDER BY project_id ASC, created_at DESC, id DESC
        """
    )
    snapshots: dict[str, dict] = {}
    for project_id, payload in cursor:
        # Results are sorted newest-first per project, so first hit wins.
        if project_id in snapshots:
            continue
        try:
            # Pick only the first row per project_id thanks to ORDER BY above.
            snapshots[project_id] = json.loads(payload)
        except json.JSONDecodeError:  # pragma: no cover - defensive parsing
            logger.warning("Skipping invalid snapshot payload for project %s", project_id)
    return snapshots


def backup_database(conn: sqlite3.Connection, destination: Path | None = None) -> Path:
    """Create a sqlite backup file so snapshots can be versioned."""

    if destination is None:
        # we can keep multiple copies
        if _DB_PATH is None:
            raise ValueError("Database path unknown; open_db must be called before backup.")
        timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d-%H%M%S")
        backup_dir = _DB_PATH.parent / "backups"
        destination = backup_dir / f"capstone-backup-{timestamp}.db"
    destination.parent.mkdir(parents=True, exist_ok=True)
    backup_conn = sqlite3.connect(destination)
    try:
        conn.backup(backup_conn)
    finally:
        backup_conn.close()
    logger.info("Created database backup at %s", destination)
    return destination


def export_snapshots_to_json(conn: sqlite3.Connection, output_path: Path) -> int:
    """Export all stored snapshots to a JSON file for external backup."""

    cursor = conn.execute(
        """
        SELECT project_id, classification, primary_contributor, snapshot, created_at
        FROM project_analysis
        ORDER BY created_at ASC, id ASC
        """
    )
    records = []
    for project_id, classification, primary, payload, created_at in cursor:
        try:
            snapshot = json.loads(payload)
        except json.JSONDecodeError:
            logger.warning("Skipping corrupt snapshot for %s during export", project_id)
            continue
        record = {
            "project_id": project_id,
            "classification": classification,
            "primary_contributor": primary,
            "created_at": created_at,
            "snapshot": snapshot,
        }
        records.append(record)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        json.dump(records, fh, indent=2)
    logger.info("Exported %s snapshot(s) to %s", len(records), output_path)
    return len(records)


def _prepare_snapshot_payload(
    snapshot: dict,
    project_id: str,
    classification: str,
    primary_contributor: str | None,
) -> dict:
    prepared = dict(snapshot)
    # downstream readers expect these keys 
    prepared.setdefault("project_id", project_id)
    prepared.setdefault("classification", classification)
    if primary_contributor is not None:
        prepared.setdefault("primary_contributor", primary_contributor)
    return prepared


def _validate_snapshot_insert(
    conn: sqlite3.Connection,
    row_id: int,
    *,
    project_id: str,
    classification: str,
    primary_contributor: str | None,
) -> None:
    cursor = conn.execute(
        """
        SELECT project_id, classification, primary_contributor, snapshot
        FROM project_analysis
        WHERE id = ?
        """,
        (row_id,),
    )
    row = cursor.fetchone()
    if row is None:
        # can't find the row – treat as corruption
        raise sqlite3.DatabaseError(f"Inserted snapshot row {row_id} is missing.")
    stored_project_id, stored_classification, stored_primary, payload = row
    if stored_project_id != project_id or stored_classification != classification:
        raise sqlite3.DatabaseError("Integrity check failed: stored metadata mismatch.")
    try:
        decoded = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise sqlite3.DatabaseError("Stored snapshot payload is not valid JSON.") from exc
    if decoded.get("project_id") != project_id:
        raise sqlite3.DatabaseError("Snapshot payload missing expected project_id.")
    if decoded.get("classification") != classification:
        raise sqlite3.DatabaseError("Snapshot payload missing expected classification.")
    if primary_contributor and decoded.get("primary_contributor") != primary_contributor:
        raise sqlite3.DatabaseError("Snapshot payload missing expected primary_contributor.")


__all__ = [
    "open_db",
    "close_db",
    "DB_DIR",
    "store_analysis_snapshot",
    "fetch_latest_snapshot",
    "fetch_latest_snapshots",
    "backup_database",
    "export_snapshots_to_json",
]
