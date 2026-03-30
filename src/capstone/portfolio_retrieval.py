from __future__ import annotations

import json
import sqlite3
from typing import Any, Dict, List, Literal, Optional
from contextlib import contextmanager
from pathlib import Path

from capstone.api.portfolio_helpers import (
    ensure_portfolio_tables,
    get_portfolio_customization,
    list_portfolio_images,
)

try:
    from .storage import (
        open_db as _open_db,
        close_db as _close_db,
        _UNSET as _DB_UNSET,
    )
except Exception:
    _open_db = None
    _close_db = None
    _DB_UNSET = object()


@contextmanager
def _db_session(db_dir: str | None, *, user=_DB_UNSET):
    """
    Always close the SQLite handle (critical on Windows).
    Uses capstone.storage.open_db/close_db if available.
    Pass user=None to explicitly open the guest DB regardless of CURRENT_USER.
    """
    base_path = Path(db_dir) if db_dir else None

    if _open_db is not None:
        conn = _open_db(base_path, user=user)  # pass Path or None
    else:
        target = Path(db_dir) if db_dir else Path("data")
        target.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(target / "capstone.db")

    try:
        try:
            conn.execute("PRAGMA journal_mode=DELETE;")
        except Exception:
            pass
        yield conn
    finally:
        try:
            if _close_db is not None:
                _close_db(conn)
            else:
                conn.close()
        except Exception:
            try:
                conn.close()
            except Exception:
                pass


def _extract_evidence(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """
    Minimal evidence summary for API consumers.
    """
    if isinstance(snapshot.get("project_evidence"), list) and snapshot.get("project_evidence"):
        items: List[Dict[str, str]] = []
        for it in snapshot.get("project_evidence"):
            if isinstance(it, dict):
                items.append(
                    {"label": str(it.get("label", "")), "value": str(it.get("value", ""))}
                )
            else:
                items.append({"label": "evidence", "value": str(it)})
        if items:
            return {"type": "metrics", "items": items}

    # Legacy metrics dict support
    metrics = snapshot.get("metrics")
    if isinstance(metrics, dict) and metrics:
        return {
            "type": "metrics",
            "items": [{"label": str(k), "value": str(v)} for k, v in metrics.items()],
        }

    # Structured evidence fields
    items: List[Dict[str, str]] = []
    for key in ("impact_metrics", "feedback", "evaluation"):
        value = snapshot.get(key)
        if isinstance(value, list):
            for it in value:
                if isinstance(it, dict):
                    items.append(
                        {"label": str(it.get("label", key)), "value": str(it.get("value", it))}
                    )
                else:
                    items.append({"label": key, "value": str(it)})
        elif isinstance(value, dict):
            for k, v in value.items():
                items.append({"label": f"{key}:{k}", "value": str(v)})
        elif value is not None:
            items.append({"label": key, "value": str(value)})
    if items:
        return {"type": "evidence", "items": items}

    items = []
    if isinstance(snapshot.get("skills"), list):
        items.append({"label": "Skills detected", "value": str(len(snapshot["skills"]))})
    if isinstance(snapshot.get("projects"), list):
        items.append({"label": "Projects detected", "value": str(len(snapshot["projects"]))})
    if isinstance(snapshot.get("files"), list):
        items.append({"label": "Files analyzed", "value": str(len(snapshot["files"]))})

    return {"type": "metrics", "items": items}


def _parse_view(v: Optional[str]) -> Literal["portfolio", "resume"]:
    v = (v or "").strip().lower()
    return "resume" if v == "resume" else "portfolio"

def get_latest_snapshot_dict(conn: sqlite3.Connection, project_id: str) -> Optional[Dict[str, Any]]:
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

    if not row:
        return None

    raw = row[0]

    if isinstance(raw, dict):
        return raw

    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    return None


def get_portfolio_entry(conn: sqlite3.Connection, project_id: str) -> Optional[Dict[str, Any]]:
    ensure_portfolio_tables(conn)

    snapshot = get_latest_snapshot_dict(conn, project_id)
    if snapshot is None:
        return None

    customization = get_portfolio_customization(conn, project_id)
    images = list_portfolio_images(conn, project_id)

    project_name = (
        snapshot.get("name")
        or snapshot.get("project_name")
        or snapshot.get("title")
        or project_id
    )

    summary = (
        customization.get("portfolio_blurb")
        or snapshot.get("summary")
        or snapshot.get("description")
        or ""
    )

    source = snapshot.get("source") or snapshot.get("repo_source") or ""

    return {
        "project_id": project_id,
        "name": project_name,
        "source": source,
        "summary": summary,
        "template_id": customization.get("template_id") or "classic",
        "key_role": customization.get("key_role") or "",
        "evidence_of_success": customization.get("evidence_of_success") or "",
        "portfolio_blurb": customization.get("portfolio_blurb") or "",
        "snapshot": snapshot,
        "evidence": _extract_evidence(snapshot),
        "images": images,
    }


def get_portfolio_entries(conn: sqlite3.Connection, project_ids: List[str]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []

    for project_id in project_ids:
        entry = get_portfolio_entry(conn, project_id)
        if entry is not None:
            items.append(entry)

    return items