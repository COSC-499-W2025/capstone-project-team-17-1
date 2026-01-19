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
            project_id TEXT NOT NULL,
            classification TEXT NOT NULL,
            primary_contributor TEXT,
            snapshot JSON NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS contributor_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT NOT NULL,
            contributor TEXT NOT NULL,
            commits INTEGER NOT NULL DEFAULT 0,
            line_changes INTEGER NOT NULL DEFAULT 0,
            pull_requests INTEGER NOT NULL DEFAULT 0,
            issues INTEGER NOT NULL DEFAULT 0,
            reviews INTEGER NOT NULL DEFAULT 0,
            score REAL NOT NULL DEFAULT 0,
            weights_hash TEXT,
            source TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_contributor_stats_project
        ON contributor_stats (project_id, contributor, created_at)
        """
    )
    info = conn.execute("PRAGMA table_info(contributor_stats)").fetchall()
    columns = {row[1] for row in info}
    if "weights_hash" not in columns:
        conn.execute("ALTER TABLE contributor_stats ADD COLUMN weights_hash TEXT")
        conn.commit()

    # backfill legacy rows that only had project_name, can be deleted at end
    info = conn.execute("PRAGMA table_info(project_analysis)").fetchall()
    columns = {row[1] for row in info}
    if "project_id" not in columns:
        conn.execute("ALTER TABLE project_analysis ADD COLUMN project_id TEXT")
    if "project_name" in columns:
        conn.execute("UPDATE project_analysis SET project_id = COALESCE(project_id, project_name) WHERE project_id IS NULL")
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
        try:
            _DB_HANDLE.close()
        except Exception:  # pragma: no cover
            logger.warning("Failed to close DB cleanly", exc_info=True)
        finally:
            _DB_HANDLE = None
            _DB_PATH = None



def store_analysis_snapshot(
    conn: sqlite3.Connection,
    project_id: str,
    classification: str = "unknown",
    primary_contributor: str | None = None,
    snapshot: dict | None = None,
) -> None:

    if not project_id:
        raise ValueError("project_id must be provided")
    doc = dict(snapshot or {})
    doc.setdefault("project_id", project_id)
    doc.setdefault("classification", classification)
    doc.setdefault("primary_contributor", primary_contributor)
    payload = json.dumps(doc)
    conn.execute(
        """
        INSERT INTO project_analysis (project_id, classification, primary_contributor, snapshot)
        VALUES (?, ?, ?, ?)
        """,
        (project_id, classification, primary_contributor, payload),
    )
    conn.commit()


def store_contributor_stats(
    conn: sqlite3.Connection,
    project_id: str,
    contributor: str,
    *,
    commits: int = 0,
    line_changes: int = 0,
    pull_requests: int = 0,
    issues: int = 0,
    reviews: int = 0,
    score: float = 0.0,
    weights_hash: str | None = None,
    source: str | None = None,
) -> None:
    if not project_id:
        raise ValueError("project_id must be provided")
    if not contributor:
        raise ValueError("contributor must be provided")
    conn.execute(
        """
        INSERT INTO contributor_stats (
            project_id,
            contributor,
            commits,
            line_changes,
            pull_requests,
            issues,
            reviews,
            score,
            weights_hash,
            source
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            project_id,
            contributor,
            int(commits),
            int(line_changes),
            int(pull_requests),
            int(issues),
            int(reviews),
            float(score),
            weights_hash,
            source,
        ),
    )
    conn.commit()


def fetch_latest_contributor_stats(
    conn: sqlite3.Connection,
    project_id: str,
) -> list[dict]:
    if not project_id:
        return []
    cursor = conn.execute(
        """
        WITH latest_time AS (
            SELECT contributor, MAX(created_at) AS created_at
            FROM contributor_stats
            WHERE project_id = ?
            GROUP BY contributor
        ),
        latest_row AS (
            SELECT cs.contributor, MAX(cs.id) AS id
            FROM contributor_stats cs
            JOIN latest_time lt
              ON lt.contributor = cs.contributor
             AND lt.created_at = cs.created_at
            WHERE cs.project_id = ?
            GROUP BY cs.contributor
        )
        SELECT
            cs.id,
            cs.project_id,
            cs.contributor,
            cs.commits,
            cs.line_changes,
            cs.pull_requests,
            cs.issues,
            cs.reviews,
            cs.score,
            cs.weights_hash,
            cs.source,
            cs.created_at
        FROM contributor_stats cs
        JOIN latest_row lr ON lr.id = cs.id
        ORDER BY cs.score DESC, cs.contributor ASC
        """,
        (project_id, project_id),
    )
    rows = cursor.fetchall()
    payload: list[dict] = []
    for row in rows:
        (
            row_id,
            project_id,
            contributor,
            commits,
            line_changes,
            pull_requests,
            issues,
            reviews,
            score,
            weights_hash,
            source,
            created_at,
        ) = row
        payload.append(
            {
                "id": row_id,
                "project_id": project_id,
                "contributor": contributor,
                "commits": commits,
                "line_changes": line_changes,
                "pull_requests": pull_requests,
                "issues": issues,
                "reviews": reviews,
                "score": score,
                "weights_hash": weights_hash,
                "source": source,
                "created_at": created_at,
            }
        )
    return payload


def update_contributor_score(
    conn: sqlite3.Connection,
    row_id: int,
    *,
    score: float,
    weights_hash: str | None = None,
) -> None:
    conn.execute(
        """
        UPDATE contributor_stats
        SET score = ?, weights_hash = ?
        WHERE id = ?
        """,
        (float(score), weights_hash, int(row_id)),
    )
    conn.commit()


def fetch_contributor_rankings(
    conn: sqlite3.Connection,
    project_id: str,
    *,
    sort_by: str = "score",
) -> list[dict]:
    allowed = {
        "score": "score",
        "commits": "commits",
        "line_changes": "line_changes",
        "pull_requests": "pull_requests",
        "issues": "issues",
        "reviews": "reviews",
    }
    sort_key = allowed.get(sort_by, "score")
    rows = fetch_latest_contributor_stats(conn, project_id)
    return sorted(rows, key=lambda row: (-float(row.get(sort_key, 0)), row.get("contributor", "")))


def fetch_latest_snapshot(conn: sqlite3.Connection, project_id: str) -> dict | None:
    """Return the most recent snapshot for the given project, if any."""

    cursor = conn.execute(
        """
        SELECT snapshot
        FROM project_analysis
        WHERE project_id = ?
        ORDER BY datetime(created_at) DESC, id DESC
        LIMIT 1
        """,
        (project_id,),
    )
    row = cursor.fetchone()
    return json.loads(row[0]) if row else None


def fetch_latest_snapshots(conn: sqlite3.Connection, limit: int | None = None) -> list[dict]:
    # return newest snapshot for every project saved in the database
    # each item contains the same structure as fetch_latest_snapshot plus metadata

    if limit is not None and int(limit) <= 0:
        return []

    cursor = conn.execute(
        f"""
        WITH latest_time AS (
            SELECT project_id, MAX(created_at) AS created_at
            FROM project_analysis
            GROUP BY project_id
        ),
        latest_row AS (
            SELECT pa.project_id, MAX(pa.id) AS id
            FROM project_analysis pa
            JOIN latest_time lt
              ON lt.project_id = pa.project_id
             AND lt.created_at = pa.created_at
            GROUP BY pa.project_id
        )
        SELECT a.project_id, a.classification, a.primary_contributor, a.snapshot, a.created_at
        FROM project_analysis a
        JOIN latest_row lr ON lr.id = a.id
        ORDER BY datetime(a.created_at) DESC, a.id DESC
        {"LIMIT ?" if limit is not None else ""}
        """,
        (() if limit is None else (int(limit),)),
    )

    rows = cursor.fetchall()
    payload: list[dict] = []
    for project_id, classification, contributor, snapshot_json, created_at in rows:
        try:
            snapshot = json.loads(snapshot_json)
        except Exception:
            snapshot = {}
        payload.append(
            {
                "project_id": project_id,
                "classification": classification,
                "primary_contributor": contributor,
                "created_at": created_at,
                "snapshot": snapshot,
            }
        )
    return payload



def backup_database(conn: sqlite3.Connection, destination: Path) -> Path:
    # create a SQLite backup at the provided destination path
    destination.parent.mkdir(parents=True, exist_ok=True)
    backup_conn = sqlite3.connect(destination)
    try:
        conn.backup(backup_conn)
    finally:
        backup_conn.close()
    return destination


def export_snapshots_to_json(conn: sqlite3.Connection, output_path: Path) -> int:
    # export all project_analysis rows (latest snapshot per row) to a JSON file
    # Returns the number of records written
    rows = conn.execute(
        """
        SELECT project_id, classification, primary_contributor, snapshot, created_at
        FROM project_analysis
        ORDER BY created_at
        """
    ).fetchall()
    payload: list[dict] = []
    for project_id, classification, contributor, blob, created_at in rows:
        try:
            snapshot = json.loads(blob)
        except Exception:
            snapshot = {}
        payload.append(
            {
                "project_id": project_id,
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
    "store_contributor_stats",
    "fetch_latest_contributor_stats",
    "update_contributor_score",
    "fetch_contributor_rankings",
    "backup_database",
    "export_snapshots_to_json",
]
