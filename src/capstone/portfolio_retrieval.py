from __future__ import annotations

import json
import sqlite3
from typing import Any, Dict, List, Literal, Optional
from contextlib import contextmanager
from pathlib import Path

try:
    from .storage import (
        open_db as _open_db,
        close_db as _close_db,
    )
except Exception:
    _open_db = None
    _close_db = None


@contextmanager
def _db_session(db_dir: str | None):
    """
    Always close the SQLite handle (critical on Windows).
    Uses capstone.storage.open_db/close_db if available.
    """
    base_path = Path(db_dir) if db_dir else None

    if _open_db is not None:
        conn = _open_db(base_path)  # pass Path or None
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
        if _close_db is not None:
            try:
                _close_db(conn)
            except TypeError:
                _close_db()
        else:
            conn.close()


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
