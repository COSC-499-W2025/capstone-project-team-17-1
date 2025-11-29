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
            project_id TEXT,
            project_name TEXT,
            classification TEXT NOT NULL,
            primary_contributor TEXT,
            snapshot JSON NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    _ensure_project_analysis_columns(conn)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS resume_entries (
            id TEXT PRIMARY KEY,
            section TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT,
            body TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS resume_entry_links (
            entry_id TEXT NOT NULL,
            link_type TEXT NOT NULL CHECK(link_type IN ('project','skill')),
            link_value TEXT NOT NULL,
            FOREIGN KEY(entry_id) REFERENCES resume_entries(id) ON DELETE CASCADE
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_resume_entry_links
        ON resume_entry_links(link_type, link_value, entry_id)
        """
    )
    conn.commit()


def _ensure_project_analysis_columns(conn: sqlite3.Connection) -> None:
    info = conn.execute("PRAGMA table_info(project_analysis)").fetchall()
    cols = {row[1] for row in info}
    if "project_name" not in cols:
        # keep both identifiers for backwards compatibility.
        conn.execute("ALTER TABLE project_analysis ADD COLUMN project_name TEXT")
    if "project_id" not in cols:
        conn.execute("ALTER TABLE project_analysis ADD COLUMN project_id TEXT")


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
    project_id: str | None = None,
    *,
    classification: str,
    primary_contributor: str | None,
    snapshot: dict,
    project_name: str | None = None,
) -> None:
    """Persist a project analysis snapshot to the database."""

    identifier = project_id or project_name
    if not identifier:
        raise ValueError("project_id or project_name must be provided")
    id_value = project_id or identifier
    name_value = project_name or identifier
    doc = dict(snapshot or {})
    doc.setdefault("project_id", identifier)
    doc.setdefault("project_name", name_value)
    doc.setdefault("classification", classification)
    doc.setdefault("primary_contributor", primary_contributor)
    payload = json.dumps(doc)
    conn.execute(
        """
        INSERT INTO project_analysis (project_id, project_name, classification, primary_contributor, snapshot)
        VALUES (?, ?, ?, ?, ?)
        """,
        (id_value, name_value, classification, primary_contributor, payload),
    )
    conn.commit()


def fetch_latest_snapshot(conn: sqlite3.Connection, project_id: str) -> dict | None:
    """Return the most recent snapshot for the given project, if any."""

    try:
        cursor = conn.execute(
            """
            SELECT snapshot
            FROM project_analysis
            WHERE project_id = ? OR project_name = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (project_id, project_id),
        )
    except sqlite3.OperationalError:
        cursor = conn.execute(
            """
            SELECT snapshot
            FROM project_analysis
            WHERE project_name = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (project_id,),
        )
    row = cursor.fetchone()
    return json.loads(row[0]) if row else None

# fetch sanpshots
def fetch_latest_snapshots(conn: sqlite3.Connection) -> list[dict]:
    """
    Return the newest snapshot for every project saved in the database.
    Each item contains the same structure as fetch_latest_snapshot plus metadata.
    """
    try:
        cursor = conn.execute(
            """
            SELECT a.project_id, a.project_name, a.classification, a.primary_contributor, a.snapshot, a.created_at
            FROM project_analysis a
            JOIN (
                SELECT COALESCE(project_id, project_name) AS pid, MAX(created_at) AS created_at
                FROM project_analysis
                GROUP BY pid
            ) latest ON latest.pid = COALESCE(a.project_id, a.project_name) AND latest.created_at = a.created_at
            ORDER BY COALESCE(a.project_id, a.project_name)
            """
        )
    except sqlite3.OperationalError:
        cursor = conn.execute(
            """
            SELECT a.project_name, a.project_name, a.classification, a.primary_contributor, a.snapshot, a.created_at
            FROM project_analysis a
            JOIN (
                SELECT project_name AS pid, MAX(created_at) AS created_at
                FROM project_analysis
                GROUP BY project_name
            ) latest ON latest.pid = a.project_name AND latest.created_at = a.created_at
            ORDER BY a.project_name
            """
        )
    rows = cursor.fetchall()
    payload: list[dict] = []
    for project_id, project_name, classification, contributor, snapshot_json, created_at in rows:
        try:
            snapshot = json.loads(snapshot_json)
        except Exception:
            snapshot = {}
        payload.append(
            {
                "project_id": project_id or project_name,
                "project_name": project_name,
                "classification": classification,
                "primary_contributor": contributor,
                "created_at": created_at,
                "snapshot": snapshot,
            }
        )
    return payload


def backup_database(conn: sqlite3.Connection, destination: Path) -> Path:
    """Create a SQLite backup at the provided destination path."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    backup_conn = sqlite3.connect(destination)
    try:
        conn.backup(backup_conn)
    finally:
        backup_conn.close()
    return destination


def export_snapshots_to_json(conn: sqlite3.Connection, output_path: Path) -> int:
    """
    Export all project_analysis rows (latest snapshot per row) to a JSON file.
    Returns the number of records written.
    """
    rows = conn.execute(
        """
        SELECT project_id, project_name, classification, primary_contributor, snapshot, created_at
        FROM project_analysis
        ORDER BY created_at
        """
    ).fetchall()
    payload: list[dict] = []
    for project_id, project_name, classification, contributor, blob, created_at in rows:
        try:
            snapshot = json.loads(blob)
        except Exception:
            snapshot = {}
        payload.append(
            {
                "project_id": project_id or project_name,
                "project_name": project_name,
                "classification": classification,
                "primary_contributor": contributor,
                "created_at": created_at,
                "snapshot": snapshot,
            }
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return len(payload)


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
