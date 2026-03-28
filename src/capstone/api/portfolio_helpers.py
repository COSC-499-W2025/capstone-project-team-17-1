from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

ALLOWED_PORTFOLIO_TEMPLATES = {"classic", "case_study", "gallery"}
ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


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
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_portfolio_images_project "
        "ON portfolio_images(project_id, sort_order, created_at)"
    )
    conn.commit()
    
def ensure_portfolio_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS portfolio_customizations (
            project_id TEXT PRIMARY KEY,
            template_id TEXT NOT NULL DEFAULT 'classic',
            key_role TEXT,
            evidence_of_success TEXT,
            portfolio_blurb TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS portfolio_images (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            image_path TEXT NOT NULL,
            caption TEXT,
            is_cover INTEGER DEFAULT 0,
            sort_order INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
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

def get_latest_snapshot(conn: sqlite3.Connection, project_id: str) -> Optional[SnapshotRow]:
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
        return json.loads(raw)
    return None


def get_portfolio_customization(conn: sqlite3.Connection, project_id: str) -> Dict[str, Any]:
    row = conn.execute(
        """
        SELECT project_id, template_id, key_role, evidence_of_success, portfolio_blurb, updated_at
        FROM portfolio_customizations
        WHERE project_id = ?
        """,
        (project_id,),
    ).fetchone()

    if not row:
        return {
            "project_id": project_id,
            "template_id": "classic",
            "key_role": "",
            "evidence_of_success": "",
            "portfolio_blurb": "",
            "updated_at": None,
        }

    return {
        "project_id": row[0],
        "template_id": row[1] or "classic",
        "key_role": row[2] or "",
        "evidence_of_success": row[3] or "",
        "portfolio_blurb": row[4] or "",
        "updated_at": row[5],
    }


def upsert_portfolio_customization(
    conn: sqlite3.Connection,
    project_id: str,
    *,
    template_id: str,
    key_role: str,
    evidence_of_success: str,
    portfolio_blurb: str,
) -> Dict[str, Any]:
    template_id = (template_id or "classic").strip().lower()
    if template_id not in ALLOWED_PORTFOLIO_TEMPLATES:
        raise ValueError(f"Invalid template_id: {template_id}")

    conn.execute(
        """
        INSERT INTO portfolio_customizations (
            project_id,
            template_id,
            key_role,
            evidence_of_success,
            portfolio_blurb,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(project_id) DO UPDATE SET
            template_id = excluded.template_id,
            key_role = excluded.key_role,
            evidence_of_success = excluded.evidence_of_success,
            portfolio_blurb = excluded.portfolio_blurb,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            project_id,
            template_id,
            key_role or "",
            evidence_of_success or "",
            portfolio_blurb or "",
        ),
    )
    conn.commit()
    return get_portfolio_customization(conn, project_id)


def list_portfolio_images(conn: sqlite3.Connection, project_id: str) -> List[Dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT id, project_id, image_path, caption, is_cover, sort_order, created_at
        FROM portfolio_images
        WHERE project_id = ?
        ORDER BY sort_order ASC, created_at ASC
        """,
        (project_id,),
    ).fetchall()

    return [
        {
            "id": row[0],
            "project_id": row[1],
            "image_path": row[2],
            "caption": row[3] or "",
            "is_cover": bool(row[4]),
            "sort_order": int(row[5] or 0),
            "created_at": row[6],
        }
        for row in rows
    ]


def _safe_filename(filename: str) -> str:
    name = Path(filename or "upload").name
    stem = Path(name).stem[:80] or "image"
    suffix = Path(name).suffix.lower()
    if suffix not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError("Unsupported image type")
    return f"{stem}{suffix}"


def _project_image_dir(base_dir: Path, project_id: str) -> Path:
    safe_project = "".join(ch if ch.isalnum() or ch in {"-", "."} else "_" for ch in project_id)
    path = base_dir / "portfolio_images" / safe_project
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_portfolio_image(
    conn: sqlite3.Connection,
    *,
    project_id: str,
    filename: str,
    file_bytes: bytes,
    images_base_dir: Path,
    caption: str = "",
    make_cover: bool = False,
) -> Dict[str, Any]:
    if not file_bytes:
        raise ValueError("Uploaded file is empty")

    safe_name = _safe_filename(filename)
    image_id = uuid.uuid4().hex
    ext = Path(safe_name).suffix.lower()

    project_dir = _project_image_dir(images_base_dir, project_id)
    stored_name = f"{image_id}{ext}"
    stored_path = project_dir / stored_name
    stored_path.write_bytes(file_bytes)

    row = conn.execute(
        "SELECT COALESCE(MAX(sort_order), -1) + 1 FROM portfolio_images WHERE project_id = ?",
        (project_id,),
    ).fetchone()
    next_sort = int(row[0] or 0)

    if make_cover:
        conn.execute(
            "UPDATE portfolio_images SET is_cover = 0 WHERE project_id = ?",
            (project_id,),
        )

    conn.execute(
        """
        INSERT INTO portfolio_images (
            id, project_id, image_path, caption, is_cover, sort_order
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            image_id,
            project_id,
            str(stored_path),
            caption or "",
            1 if make_cover else 0,
            next_sort,
        ),
    )
    conn.commit()

    result = conn.execute(
        """
        SELECT id, project_id, image_path, caption, is_cover, sort_order, created_at
        FROM portfolio_images
        WHERE id = ?
        """,
        (image_id,),
    ).fetchone()

    return {
        "id": result[0],
        "project_id": result[1],
        "image_path": result[2],
        "caption": result[3] or "",
        "is_cover": bool(result[4]),
        "sort_order": int(result[5] or 0),
        "created_at": result[6],
    }


def delete_portfolio_image(
    conn: sqlite3.Connection,
    *,
    project_id: str,
    image_id: str,
) -> bool:
    row = conn.execute(
        """
        SELECT image_path
        FROM portfolio_images
        WHERE id = ? AND project_id = ?
        """,
        (image_id, project_id),
    ).fetchone()

    if not row:
        return False

    image_path = Path(row[0])
    conn.execute(
        "DELETE FROM portfolio_images WHERE id = ? AND project_id = ?",
        (image_id, project_id),
    )
    conn.commit()

    try:
        if image_path.exists():
            image_path.unlink()
    except Exception:
        pass

    return True


def set_cover_portfolio_image(
    conn: sqlite3.Connection,
    *,
    project_id: str,
    image_id: str,
) -> bool:
    exists = conn.execute(
        "SELECT 1 FROM portfolio_images WHERE id = ? AND project_id = ?",
        (image_id, project_id),
    ).fetchone()

    if not exists:
        return False

    conn.execute("UPDATE portfolio_images SET is_cover = 0 WHERE project_id = ?", (project_id,))
    conn.execute(
        "UPDATE portfolio_images SET is_cover = 1 WHERE id = ? AND project_id = ?",
        (image_id, project_id),
    )
    conn.commit()
    return True


def reorder_portfolio_images(
    conn: sqlite3.Connection,
    *,
    project_id: str,
    image_ids: List[str],
) -> List[Dict[str, Any]]:
    existing_rows = conn.execute(
        "SELECT id FROM portfolio_images WHERE project_id = ?",
        (project_id,),
    ).fetchall()
    existing_ids = {row[0] for row in existing_rows}

    if set(image_ids) != existing_ids:
        raise ValueError("image_ids must contain every image for the project exactly once")

    for index, image_id in enumerate(image_ids):
        conn.execute(
            """
            UPDATE portfolio_images
            SET sort_order = ?
            WHERE id = ? AND project_id = ?
            """,
            (index, image_id, project_id),
        )

    conn.commit()
    return list_portfolio_images(conn, project_id)
