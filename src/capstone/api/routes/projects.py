from fastapi import APIRouter, UploadFile, File, HTTPException
from pathlib import Path
import tempfile
import shutil
import time

from capstone import file_store, storage

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("/upload")
async def upload_project(file: UploadFile = File(...)):
    filename = file.filename or "upload.zip"
    if not filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip files are supported")

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)

    conn = storage.open_db()
    try:
        stored = file_store.ensure_file(
            conn,
            tmp_path,
            original_name=filename,
            source="api_upload",
            mime="application/zip",
        )
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass

    project_id = stored["upload_id"]
    return {
        "project_id": project_id,
        "file_id": stored["file_id"],
        "hash": stored["hash"],
        "dedup": stored["dedup"],
        "size_bytes": stored["size_bytes"],
        "stored_path": stored["path"],
    }


@router.get("")
def list_projects():
    """
    Lists uploaded .zip projects from CAS storage.
    """
    conn = storage.open_db()
    rows = conn.execute(
        """
        SELECT u.upload_id, u.original_name, u.file_id, u.hash, u.created_at,
               f.size_bytes, f.path
        FROM uploads u
        JOIN files f ON f.file_id = u.file_id
        ORDER BY datetime(u.created_at) DESC
        """
    ).fetchall()
    return {
        "count": len(rows),
        "projects": [
            {
                "project_id": r[0],
                "filename": r[1],
                "file_id": r[2],
                "hash": r[3],
                "created_at": r[4],
                "size_bytes": r[5],
                "stored_path": r[6],
            }
            for r in rows
        ],
    }


@router.get("/{project_id}")
def get_project(project_id: str):
    """
    Returns info for a specific uploaded project zip by upload_id.
    """
    conn = storage.open_db()
    row = conn.execute(
        """
        SELECT u.upload_id, u.original_name, u.file_id, u.hash, u.created_at,
               f.size_bytes, f.path
        FROM uploads u
        JOIN files f ON f.file_id = u.file_id
        WHERE u.upload_id = ?
        LIMIT 1
        """,
        (project_id,),
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Project not found")

    return {
        "project_id": row[0],
        "filename": row[1],
        "file_id": row[2],
        "hash": row[3],
        "created_at": row[4],
        "size_bytes": row[5],
        "stored_path": row[6],
    }
