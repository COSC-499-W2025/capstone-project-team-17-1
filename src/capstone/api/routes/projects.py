from pydantic import BaseModel
from typing import Optional, List
from fastapi import APIRouter, UploadFile, File, HTTPException, Response
from pathlib import Path
import tempfile
import shutil
import time
import zipfile
import hashlib
from collections import Counter

from capstone import file_store, storage
class ProjectEdit(BaseModel):
    key_role: Optional[str] = None
    evidence: Optional[str] = None
    portfolio_blurb: Optional[str] = None
    resume_bullets: Optional[List[str]] = None
    selected: Optional[bool] = None
    rank: Optional[int] = None

router = APIRouter(prefix="/projects", tags=["projects"])

_EXT_TO_SKILL = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".java": "java",
    ".cpp": "c++",
    ".c": "c",
    ".go": "go",
    ".rs": "rust",
    ".sql": "sql",
    ".html": "html",
    ".css": "css",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".json": "json",
    ".md": "markdown",
}


def _normalize_token(value: str | None) -> str:
    token = (value or "").strip().lower()
    out = []
    prev_sep = False
    for ch in token:
        if ch.isalnum():
            out.append(ch)
            prev_sep = False
        elif not prev_sep:
            out.append("_")
            prev_sep = True
    return "".join(out).strip("_")


def _inspect_zip_manifest(zip_path: Path) -> dict:
    try:
        with zipfile.ZipFile(zip_path) as zf:
            files = []
            skills = Counter()
            roots = []
            for info in zf.infolist():
                if info.is_dir():
                    continue
                path = info.filename.strip("/")
                if not path:
                    continue
                files.append((path, int(info.file_size), int(getattr(info, "CRC", 0))))
                parts = [p for p in path.split("/") if p]
                if parts:
                    roots.append(parts[0])
                suffix = Path(path).suffix.lower()
                skill = _EXT_TO_SKILL.get(suffix)
                if skill:
                    skills[skill] += 1
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid zip archive")

    # Normalize away a single common root folder
    root_name = roots[0] if roots and all(r == roots[0] for r in roots) else None
    rel_files = []
    for path, size, crc in files:
        rel = path
        if root_name and path.startswith(root_name + "/"):
            rel = path[len(root_name) + 1 :]
        rel_files.append((rel, size, crc))
    rel_files.sort(key=lambda x: x[0])
    signature_src = "|".join(f"{p}:{s}:{c}" for p, s, c in rel_files)
    signature = hashlib.sha256(signature_src.encode("utf-8")).hexdigest() if rel_files else ""
    return {
        "root_name": root_name,
        "root_norm": _normalize_token(root_name),
        "files": rel_files,
        "file_paths": {p for p, _, _ in rel_files},
        "skills": dict(skills),
        "signature": signature,
    }


def _inspect_stored_zip_manifest(conn, file_id: str) -> dict:
    with file_store.open_file(conn, file_id) as fh, tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
        shutil.copyfileobj(fh, tmp)
        tmp_path = Path(tmp.name)
    try:
        return _inspect_zip_manifest(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)


def _auto_detect_project_id(conn, tmp_zip_path: Path, filename: str) -> str | None:
    new_manifest = _inspect_zip_manifest(tmp_zip_path)
    rows = conn.execute(
        """
        SELECT u.upload_id, u.file_id, u.original_name, u.created_at
        FROM uploads u
        JOIN (
            SELECT upload_id, MAX(datetime(created_at)) AS max_created
            FROM uploads
            GROUP BY upload_id
        ) latest
          ON latest.upload_id = u.upload_id
         AND datetime(u.created_at) = latest.max_created
        ORDER BY datetime(u.created_at) DESC
        """
    ).fetchall()
    filename_norm = _normalize_token(Path(filename).stem)
    best: tuple[float, str] | None = None
    for upload_id, file_id, original_name, _ in rows:
        try:
            prior = _inspect_stored_zip_manifest(conn, file_id)
        except Exception:
            continue
        # Exact file manifest match
        if prior["signature"] and prior["signature"] == new_manifest["signature"]:
            return str(upload_id)
        score = 0.0
      
        if new_manifest["root_norm"] and new_manifest["root_norm"] == prior.get("root_norm"):
            score += 0.6
        prior_name_norm = _normalize_token(Path(original_name or "").stem)
        if filename_norm and filename_norm == prior_name_norm:
            score += 0.2
        union = len(new_manifest["file_paths"] | prior.get("file_paths", set()))
        inter = len(new_manifest["file_paths"] & prior.get("file_paths", set()))
        if union:
            score += 0.6 * (inter / union)
        if score >= 0.65 and (best is None or score > best[0]):
            best = (score, str(upload_id))
    return best[1] if best else None


def _generate_project_id_from_zip(conn, tmp_zip_path: Path, filename: str) -> str:
    manifest = _inspect_zip_manifest(tmp_zip_path)
    base = manifest.get("root_norm") or _normalize_token(Path(filename).stem) or "project"
    short = (manifest.get("signature") or hashlib.sha256(filename.encode("utf-8")).hexdigest())[:8]
    candidate = f"{base}_{short}"
    exists = conn.execute("SELECT 1 FROM uploads WHERE upload_id = ? LIMIT 1", (candidate,)).fetchone()
    if not exists:
        return candidate
    suffix = 2
    while True:
        alt = f"{candidate}_{suffix}"
        exists = conn.execute("SELECT 1 FROM uploads WHERE upload_id = ? LIMIT 1", (alt,)).fetchone()
        if not exists:
            return alt
        suffix += 1


@router.post("/upload")
async def upload_project(file: UploadFile = File(...), project_id: str | None = None):
    filename = file.filename or "upload.zip"
    if not filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip files are supported")

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)

    conn = storage.open_db()
    auto_detected = False
    if not project_id:
        project_id = _auto_detect_project_id(conn, tmp_path, filename)
        auto_detected = bool(project_id)
    if not project_id:
        project_id = _generate_project_id_from_zip(conn, tmp_path, filename)
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
    
    manifest = _inspect_stored_zip_manifest(conn, stored["file_id"])
    
    snapshot = {
        "project_id": project_id,
        "skills": manifest.get("skills", {}),
        "root_name": manifest.get("root_name"),
        "file_count": len(manifest.get("files", []))
    }
    
    storage.store_analysis_snapshot(
        conn,
        project_id=project_id,
        classification="unknown",
        primary_contributor=None,
        snapshot=snapshot
    )
    
    message = "Upload stored successfully."
    if stored.get("dedup"):
        message = "Duplicate upload detected; existing file reused."
    elif auto_detected:
        message = "Upload stored and matched to existing project automatically."
    return {
        "message": message,
        "project_id": project_id,
        "auto_detected_project_id": auto_detected,
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


@router.get("/{id}")
def get_project(id: str):
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
        (id,),
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

@router.delete("/{id}")
def delete_project(id: str):
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
        (id,),
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Project not found")

    file_id, file_path = row

    # delete upload reference
    conn.execute("DELETE FROM uploads WHERE upload_id = ?", (id,))
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
            "project_id": id,
            "file_id": file_id,
        },
        "error": None,
    }


@router.post("/{id}/thumbnail")
async def upload_project_thumbnail(id: str, file: UploadFile = File(...)):
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
            project_id=id,
            image_bytes=image_bytes,
            filename=filename,
            content_type=file.content_type or "application/octet-stream",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {"data": stored, "error": None}


@router.get("/{id}/thumbnail")
def get_project_thumbnail(id: str):
    # Return the latest thumbnail bytes
    conn = storage.open_db()
    meta = storage.fetch_project_thumbnail_meta(conn, id)
    if not meta:
        raise HTTPException(status_code=404, detail="Thumbnail not found")
    image_bytes = storage.fetch_project_thumbnail_bytes(conn, id)
    if not image_bytes:
        raise HTTPException(status_code=404, detail="Thumbnail not found")
    return Response(
        content=image_bytes,
        media_type=meta.get("content_type") or "application/octet-stream",
        headers={
            "Content-Disposition": f"inline; filename=\"{meta.get('filename') or 'thumbnail'}\"",
        },
    )

@router.get("/{id}/uploads")
def list_project_uploads(id: str):
    conn = storage.open_db()
    rows = conn.execute(
        """
        SELECT u.original_name, u.hash, u.file_id, f.size_bytes, u.created_at,
               f.size_bytes, f.path
        FROM uploads u
        JOIN files f ON f.file_id = u.file_id
        WHERE u.upload_id = ?
        ORDER BY datetime(u.created_at) ASC
        """,
        (id,),
    ).fetchall()

    uploads_payload = [
        {
            "project_id": id,
            "filename": r[0],
            "file_id": r[2],
            "hash": r[1],
            "created_at": r[4],
            "size_bytes": r[3],
            "stored_path": r[6],
        }
        for r in rows
    ]
    snapshot_diff = _build_upload_diff(conn, rows)

    return {
        "project_id": id,
        "count": len(rows),
        "uploads": uploads_payload,
        "snapshot_diff": snapshot_diff,
    }


def _load_upload_zip_manifest(conn, file_id: str) -> dict:
    with file_store.open_file(conn, file_id) as fh:
        try:
            with zipfile.ZipFile(fh) as zf:
                files = {}
                skills = Counter()
                roots = []
                for info in zf.infolist():
                    if info.is_dir():
                        continue
                    path = info.filename.strip("/")
                    if not path:
                        continue
                    parts = [p for p in path.split("/") if p]
                    if parts:
                        roots.append(parts[0])
                    files[path] = {"size": int(info.file_size), "crc": int(getattr(info, "CRC", 0))}
                    skill = _EXT_TO_SKILL.get(Path(path).suffix.lower())
                    if skill:
                        skills[skill] += 1
        except zipfile.BadZipFile:
            raise HTTPException(status_code=400, detail="Stored file is not a valid zip")
    root_name = roots[0] if roots and all(r == roots[0] for r in roots) else None
    normalized_files = {}
    for path, meta in files.items():
        rel = path[len(root_name) + 1 :] if root_name and path.startswith(root_name + "/") else path
        normalized_files[rel] = meta
    return {"root_name": root_name, "files": normalized_files, "skills": dict(skills)}


def _build_upload_diff(conn, rows, earlier_index: int = 0, later_index: int = -1) -> dict | None:
    if len(rows) < 2:
        return None
    size = len(rows)
    # Default API behavior compares earliest vs latest upload
    e_idx = earlier_index if earlier_index >= 0 else size + earlier_index
    l_idx = later_index if later_index >= 0 else size + later_index
    if e_idx < 0 or e_idx >= size or l_idx < 0 or l_idx >= size or e_idx == l_idx:
        return None

    earlier = rows[e_idx]
    later = rows[l_idx]
    earlier_manifest = _load_upload_zip_manifest(conn, earlier[2])
    later_manifest = _load_upload_zip_manifest(conn, later[2])

    ef, lf = earlier_manifest["files"], later_manifest["files"]
    epaths, lpaths = set(ef), set(lf)
    added = sorted(lpaths - epaths)
    removed = sorted(epaths - lpaths)
    modified = sorted(p for p in (epaths & lpaths) if ef[p] != lf[p])

    es = earlier_manifest["skills"]
    ls = later_manifest["skills"]
    skill_changes = []
    for name in sorted(set(es) | set(ls)):
        before = int(es.get(name, 0))
        after = int(ls.get(name, 0))
        if before != after:
            skill_changes.append({"name": name, "before": before, "after": after, "delta": after - before})

    return {
        "earlier": {"index": e_idx, "filename": earlier[0], "file_id": earlier[2], "created_at": earlier[4]},
        "later": {"index": l_idx, "filename": later[0], "file_id": later[2], "created_at": later[4]},
        "files": {
            "added": added,
            "removed": removed,
            "modified": modified,
            "summary": {
                "added_count": len(added),
                "removed_count": len(removed),
                "modified_count": len(modified),
            },
        },
        "skills": {"before": es, "after": ls, "changes": skill_changes},
    }
@router.patch("/{id}")
def edit_project(id: str, payload: ProjectEdit):
    conn = storage.open_db()
    exists = conn.execute(
        "SELECT 1 FROM uploads WHERE upload_id = ? LIMIT 1",
        (id,),
    ).fetchone()
    if not exists:
        raise HTTPException(status_code=404, detail="Project not found")

    updated = storage.upsert_project_overrides(
        conn,
        project_id=id,
        key_role=payload.key_role,
        evidence=payload.evidence,
        portfolio_blurb=payload.portfolio_blurb,
        resume_bullets=payload.resume_bullets,
        selected=payload.selected,
        rank=payload.rank,
    )
    return {"data": updated, "error": None}


@router.get("/{id}/overrides")
def get_project_overrides(id: str):
    conn = storage.open_db()
    data = storage.fetch_project_overrides(conn, id)
    if not data:
        raise HTTPException(status_code=404, detail="No overrides found")
    return {"data": data, "error": None}
