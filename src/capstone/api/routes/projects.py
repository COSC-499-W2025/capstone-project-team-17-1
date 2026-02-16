from __future__ import annotations

from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import FileResponse
from pathlib import Path
import tempfile
import shutil
import sqlite3

from capstone import file_store, storage

router = APIRouter(prefix="/projects", tags=["projects"])


def _ensure_thumbnail_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS project_thumbnails (
            project_id TEXT NOT NULL,
            file_id INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.commit()  # make sure the table exists immediately


def _normalized_content_type(file: UploadFile) -> str:
    ct = (file.content_type or "").lower()
    # strip "text/plain; charset=utf-8" -> "text/plain"
    if ";" in ct:
        ct = ct.split(";", 1)[0].strip()
    return ct


@router.post("/{project_id}/thumbnail")
async def upload_thumbnail(project_id: str, file: UploadFile = File(...)):
    ct = _normalized_content_type(file)

    # Accept only actual image/* types (test uses image/png; reject text/plain)
    if not ct.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image uploads are allowed")

    filename = file.filename or "thumbnail"

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)

    conn = storage.open_db()
    try:
        stored = file_store.ensure_file(
            conn,
            tmp_path,
            original_name=filename,
            source="api_thumbnail",
            mime=ct or "application/octet-stream",
            project_id=project_id,
        )

        _ensure_thumbnail_table(conn)
        conn.execute(
            "INSERT INTO project_thumbnails (project_id, file_id) VALUES (?, ?)",
            (project_id, stored["file_id"]),
        )
        conn.commit()
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass

    return {
        "data": {
            "ok": True,
            "project_id": project_id,
            "file_id": stored["file_id"],
        },
        "error": None,
    }


@router.get("/{project_id}/thumbnail")
def get_thumbnail(project_id: str):
    conn = storage.open_db()
    try:
        _ensure_thumbnail_table(conn)

        row = conn.execute(
            """
            SELECT f.path, f.mime
            FROM project_thumbnails t
            JOIN files f ON f.file_id = t.file_id
            WHERE t.project_id = ?
            ORDER BY datetime(t.created_at) DESC
            LIMIT 1
            """,
            (project_id,),
        ).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Thumbnail not found")

        file_path, mime = row
        if not file_path or not Path(file_path).exists():
            raise HTTPException(status_code=404, detail="Thumbnail file missing")

        return FileResponse(path=file_path, media_type=mime or "application/octet-stream")
    finally:
        try:
            conn.close()
        except Exception:
            pass
