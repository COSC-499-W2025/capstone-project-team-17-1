from pydantic import BaseModel
from typing import Optional, List
from fastapi import APIRouter, UploadFile, File, HTTPException, Response
from pathlib import Path
import tempfile
import shutil
import time

from capstone import file_store, storage
class ProjectEdit(BaseModel):
    key_role: Optional[str] = None
    evidence: Optional[str] = None
    portfolio_blurb: Optional[str] = None
    resume_bullets: Optional[List[str]] = None
    selected: Optional[bool] = None
    rank: Optional[int] = None

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("/upload")
async def upload_project(file: UploadFile = File(...), project_id: str | None = None):
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
            upload_id=project_id,  #this is for uploading project id 
        )
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass

    project_id = stored["upload_id"]
    message = "Upload stored successfully."
    if stored.get("dedup"):
        message = "Duplicate upload detected; existing file reused."
    return {
        "message": message,
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

@router.delete("/{project_id}")
def delete_project(project_id: str):
    """
    Deletes a project upload and its associated stored file.
    """
    conn = storage.open_db()

    row = conn.execute(
        """
        SELECT u.file_id, f.path
        FROM uploads u
        JOIN files f ON f.file_id = u.file_id
        WHERE u.upload_id = ?
        """,
        (project_id,),
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Project not found")

    file_id, file_path = row

    # delete upload reference
    conn.execute("DELETE FROM uploads WHERE upload_id = ?", (project_id,))
    # delete file reference
    conn.execute("DELETE FROM files WHERE file_id = ?", (file_id,))
    conn.commit()

    # best-effort physical file removal
    try:
        Path(file_path).unlink(missing_ok=True)
    except Exception:
        pass

    return {
        "data": {
            "deleted": True,
            "project_id": project_id,
            "file_id": file_id,
        },
        "error": None,
    }


@router.post("/{project_id}/thumbnail")
async def upload_project_thumbnail(project_id: str, file: UploadFile = File(...)):
    # Only accept images
    if not (file.content_type or "").startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image uploads are supported")
    filename = file.filename or "thumbnail"
    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty image upload")

    conn = storage.open_db()
    try:
        # Store latest thumbnail
        stored = storage.upsert_project_thumbnail(
            conn,
            project_id=project_id,
            image_bytes=image_bytes,
            filename=filename,
            content_type=file.content_type or "application/octet-stream",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {"data": stored, "error": None}


@router.get("/{project_id}/thumbnail")
def get_project_thumbnail(project_id: str):
    # Return the latest thumbnail bytes
    conn = storage.open_db()
    meta = storage.fetch_project_thumbnail_meta(conn, project_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Thumbnail not found")
    image_bytes = storage.fetch_project_thumbnail_bytes(conn, project_id)
    if not image_bytes:
        raise HTTPException(status_code=404, detail="Thumbnail not found")
    return Response(
        content=image_bytes,
        media_type=meta.get("content_type") or "application/octet-stream",
        headers={
            "Content-Disposition": f"inline; filename=\"{meta.get('filename') or 'thumbnail'}\"",
        },
    )

@router.get("/{project_id}/uploads")
def list_project_uploads(project_id: str):
    conn = storage.open_db()
    rows = conn.execute(
        """
        SELECT u.upload_id, u.original_name, u.file_id, u.hash, u.created_at,
               f.size_bytes, f.path
        FROM uploads u
        JOIN files f ON f.file_id = u.file_id
        WHERE u.upload_id = ?
        ORDER BY datetime(u.created_at) ASC
        """,
        (project_id,),
    ).fetchall()

    return {
        "project_id": project_id,
        "count": len(rows),
        "uploads": [
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
@router.patch("/{project_id}")
def edit_project(project_id: str, payload: ProjectEdit):
    conn = storage.open_db()
    exists = conn.execute(
        "SELECT 1 FROM uploads WHERE upload_id = ? LIMIT 1",
        (project_id,),
    ).fetchone()
    if not exists:
        raise HTTPException(status_code=404, detail="Project not found")

    updated = storage.upsert_project_overrides(
        conn,
        project_id=project_id,
        key_role=payload.key_role,
        evidence=payload.evidence,
        portfolio_blurb=payload.portfolio_blurb,
        resume_bullets=payload.resume_bullets,
        selected=payload.selected,
        rank=payload.rank,
    )
    return {"data": updated, "error": None}


@router.get("/{project_id}/overrides")
def get_project_overrides(project_id: str):
    conn = storage.open_db()
    data = storage.fetch_project_overrides(conn, project_id)
    if not data:
        raise HTTPException(status_code=404, detail="No overrides found")
    return {"data": data, "error": None}