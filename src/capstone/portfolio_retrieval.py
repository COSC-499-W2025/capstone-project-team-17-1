# capstone/portfolio_retrieval.py
from __future__ import annotations

import os
import json
import sqlite3
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Tuple
from contextlib import contextmanager
from pathlib import Path
# If you already have these in capstone.storage, import it.
# We'll fall back to local SQL if not present (keeps this module standalone for tests).

# also try to import close_db from storage
# SAFE imports from storage
try:
    from .storage import (
        open_db as _open_db,
        close_db as _close_db,
        fetch_latest_snapshot as _fetch_latest_snapshot,
    )
except Exception:  # pragma: no cover
    _open_db = None
    _close_db = None
    _fetch_latest_snapshot = None

@contextmanager
def _db_session(db_dir: str | None):
    """
    Always close the SQLite handle (critical on Windows).
    Uses capstone.storage.open_db/close_db if available.
    """
    # Normalize to Path for storage.open_db()
    base_path = Path(db_dir) if db_dir else None

    if _open_db is not None:
        conn = _open_db(base_path)  # <— pass Path or None, not str
    else:
        # Fallback: local sqlite3 connection in a folder
        target = Path(db_dir) if db_dir else Path("data")
        target.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(target / "capstone.db")

    try:
        # Avoid WAL side files in tests on Windows
        try:
            conn.execute("PRAGMA journal_mode=DELETE;")
        except Exception:
            pass
        yield conn
    finally:
        # Ensure the cached/global handle is released
        try:
            if _close_db is not None:
                _close_db()
            else:
                conn.close()
        except Exception:
            pass


@dataclass(frozen=True)
class SnapshotRow:
    project_id: str
    classification: Optional[str]
    primary_contributor: Optional[str]
    snapshot: Dict[str, Any]
    created_at: str  # ISO string (stored as TEXT in SQLite)


# ---------- SQL helpers ----------

def ensure_indexes(conn: sqlite3.Connection) -> None:
    """
    Create the index that makes 'latest for project' and paginated reads fast.
    """
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_pa_project_created "
        "ON project_analysis(project_id, created_at DESC)"
    )
    conn.commit()


def _validate_sort(sort_field: str, sort_dir: str) -> Tuple[str, str]:
    sf = sort_field if sort_field in {"created_at", "classification"} else "created_at"
    sd = sort_dir.lower() if sort_dir.lower() in {"asc", "desc"} else "desc"
    return sf, sd


def list_snapshots(
    conn: sqlite3.Connection,
    project_id: str,
    page: int = 1,
    page_size: int = 20,
    sort_field: Literal["created_at", "classification"] = "created_at",
    sort_dir: Literal["asc", "desc"] = "desc",
    classification: Optional[str] = None,
    primary_contributor: Optional[str] = None,
) -> Tuple[List[SnapshotRow], int]:
    """
    Return a page of snapshots plus the total count.
    """
    sort_field, sort_dir = _validate_sort(sort_field, sort_dir)
    page = max(1, int(page))
    page_size = max(1, min(200, int(page_size)))  # keep it sane
    offset = (page - 1) * page_size

    where = ["project_id = ?"]
    params: List[Any] = [project_id]
    if classification:
        where.append("classification = ?")
        params.append(classification)
    if primary_contributor:
        where.append("primary_contributor = ?")
        params.append(primary_contributor)
    where_sql = " AND ".join(where)

    total = conn.execute(
        f"SELECT COUNT(*) FROM project_analysis WHERE {where_sql}",
        params,
    ).fetchone()[0]

    rows = conn.execute(
        f"""
        SELECT project_id, classification, primary_contributor, snapshot, created_at
        FROM project_analysis
        WHERE {where_sql}
        ORDER BY {sort_field} {sort_dir}
        LIMIT ? OFFSET ?
        """,
        (*params, page_size, offset),
    ).fetchall()

    result = [
        SnapshotRow(
            project_id=r[0],
            classification=r[1],
            primary_contributor=r[2],
            snapshot=json.loads(r[3]),
            created_at=r[4],
        )
        for r in rows
    ]
    return result, int(total)


def get_latest_snapshot(conn: sqlite3.Connection, project_id: str) -> Optional[dict]:
    """
    Return the latest JSON snapshot for a project (dict) or None.
    Uses capstone.storage.fetch_latest_snapshot if available.
    """
    if _fetch_latest_snapshot is not None:
        return _fetch_latest_snapshot(conn, project_id)

    row = conn.execute(
        """
        SELECT snapshot
        FROM project_analysis
        WHERE project_id = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (project_id,),
    ).fetchone()
    return json.loads(row[0]) if row else None


# ---------- Minimal REST API (Flask) ----------

def create_app(db_dir: Optional[str] = None, auth_token: Optional[str] = None):
    """
    create_app() returns a Flask app with two routes:
      GET /portfolios/latest?projectId=...
      GET /portfolios?projectId=...&page=1&pageSize=20&sort=created_at:desc
    Protects routes with a simple Bearer token if provided.
    """
    from flask import Flask, jsonify, request
    app = Flask(__name__)

    token_required = auth_token or os.getenv("PORTFOLIO_API_TOKEN")

    def _conn():
        if _open_db is not None:
            # capstone.storage handles directory creation & reuse
            base = None
            if db_dir:
                from pathlib import Path
                base = Path(db_dir)
            return _open_db(base)
        # Fallback: open in provided or default dir
        import sqlite3
        from pathlib import Path
        base = Path(db_dir) if db_dir else Path("data")
        base.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(base / "capstone.db")

    def _auth():
        if not token_required:
            return True
        h = request.headers.get("Authorization", "")
        return h.startswith("Bearer ") and h.split(" ", 1)[1] == token_required

    @app.before_request
    def _check_auth():
        if not _auth():
            return jsonify({"data": None, "error": {"code": "Unauthorized", "detail": "Missing or invalid token"}}), 401

    @app.get("/portfolios/latest")
    def latest():
        project_id = request.args.get("projectId", "")
        if not project_id:
            return jsonify({"data": None, "error": {"code": "BadRequest", "detail": "projectId is required"}}), 400
        with _db_session(db_dir) as c:
            ensure_indexes(c)
            data = get_latest_snapshot(c, project_id)

        if data is None:
            return jsonify({"data": None, "error": {"code": "NotFound", "detail": "No snapshots found"}}), 404
        return jsonify({"data": data, "meta": {"projectId": project_id}, "error": None})

    @app.get("/portfolios")
    def list_():
        q = request.args
        project_id = q.get("projectId", "")
        if not project_id:
            return jsonify({"data": None, "error": {"code": "BadRequest", "detail": "projectId is required"}}), 400
        sort = q.get("sort", "created_at:desc")
        sort_field, _, sort_dir = sort.partition(":")
        with _db_session(db_dir) as c:
            ensure_indexes(c)
            items, total = list_snapshots(
                c,
                project_id=project_id,
                page=int(q.get("page", 1)),
                page_size=int(q.get("pageSize", 20)),
                sort_field=sort_field or "created_at",
                sort_dir=sort_dir or "desc",
                classification=q.get("classification"),
                primary_contributor=q.get("primaryContributor"),
    )

        payload = [s.snapshot for s in items]
        return jsonify({
            "data": payload,
            "meta": {
                "projectId": project_id,
                "page": int(q.get("page", 1)),
                "pageSize": int(q.get("pageSize", 20)),
                "total": total,
            },
            "error": None,
        })

    return app
