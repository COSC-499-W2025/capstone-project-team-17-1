from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class SnapshotRow:
    project_id: str
    classification: Optional[str]
    primary_contributor: Optional[str]
    snapshot: Dict[str, Any]
    created_at: str  # ISO string stored as TEXT in SQLite


def ensure_indexes(conn: sqlite3.Connection) -> None:
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
    sort_field: str = "created_at",
    sort_dir: str = "desc",
    classification: Optional[str] = None,
    primary_contributor: Optional[str] = None,
) -> Tuple[List[SnapshotRow], int]:
    sort_field, sort_dir = _validate_sort(sort_field, sort_dir)
    page = max(1, int(page))
    page_size = max(1, min(200, int(page_size)))
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
        ORDER BY {sort_field} {sort_dir.upper()}
        LIMIT ? OFFSET ?
        """,
        params + [page_size, offset],
    ).fetchall()

    items = [
        SnapshotRow(
            project_id=r[0],
            classification=r[1],
            primary_contributor=r[2],
            snapshot=json.loads(r[3]),
            created_at=r[4],
        )
        for r in rows
    ]
    return items, total
