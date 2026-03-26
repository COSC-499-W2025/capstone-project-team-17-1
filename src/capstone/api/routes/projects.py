from pydantic import BaseModel
from typing import Optional, List
from fastapi import APIRouter, Form, UploadFile, File, HTTPException, Response, Request
from pathlib import Path
from datetime import datetime
import tempfile
import shutil
import time
import zipfile
import hashlib
from collections import Counter
from capstone.activity_log import log_event
from capstone import file_store, storage
from capstone.language_detection import classify_activity
from capstone.metrics import FileMetric, compute_metrics
from capstone.resume_retrieval import build_resume_project_item
from capstone.system.cloud_storage import upload_database, upload_project_zip, delete_project_zip
import capstone.storage as storage_module
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


def _restore_user_from_request(request: Request | None) -> None:
    """Restore storage.CURRENT_USER from the Bearer session when available."""
    if request is None:
        return
    try:
        from capstone.api.routes.auth import get_authenticated_username

        username = get_authenticated_username(request)
        if username:
            storage_module.CURRENT_USER = username
    except Exception:
        pass


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


def _build_file_summary_from_zip(zip_path: Path) -> dict:
    metrics_inputs: list[FileMetric] = []

    try:
        with zipfile.ZipFile(zip_path) as zf:
            root_name = None
            roots = set()
            for info in zf.infolist():
                if info.is_dir():
                    continue
                parts = [p for p in info.filename.strip("/").split("/") if p]
                if parts:
                    roots.add(parts[0])
            if len(roots) == 1:
                root_name = next(iter(roots))

            for info in zf.infolist():
                if info.is_dir():
                    continue
                raw_path = info.filename.strip("/")
                if not raw_path:
                    continue
                rel_path = raw_path
                if root_name and raw_path.startswith(root_name + "/"):
                    rel_path = raw_path[len(root_name) + 1 :]
                modified = datetime(*info.date_time)
                metrics_inputs.append(
                    FileMetric(
                        path=rel_path,
                        size=int(info.file_size),
                        modified=modified,
                        activity=classify_activity(rel_path),
                    )
                )
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid zip archive")

    return compute_metrics(metrics_inputs).__dict__


def _is_noreply_email(email: str) -> bool:
    lowered = email.strip().lower()
    return (
        lowered == "noreply@github.com"
        or lowered.endswith("@users.noreply.github.com")
        or lowered.endswith("@noreply.github.com")
    )


def _extract_contributors_from_zip(conn, file_id: str) -> list[tuple[str, str | None]]:
    """Extract contributor (name, email) pairs from git log files in a stored zip.

    Parses lines of the form ``commit:HASH|%an|%ae|%ct|%s``
    (written by ``_write_git_log`` in cli.py).

    Returns deduplicated ``(author_name, email_or_None)`` tuples.  Passing both
    values to ``upsert_user`` lets the storage layer match contributors across
    the GitHub-URL flow (GitHub login + email) and the ZIP flow (git user.name +
    git user.email), reconciling them via shared email when available.
    """
    raw_entries: list[tuple[str, str | None]] = []
    try:
        with file_store.open_file(conn, file_id) as fh:
            with zipfile.ZipFile(fh) as zf:
                for info in zf.infolist():
                    path_lower = info.filename.lower()
                    is_git_log = (
                        ".git/logs/git_log" in path_lower
                        or path_lower.endswith("git_log")
                        or path_lower.endswith("git_log.txt")
                    )
                    if not is_git_log:
                        continue
                    try:
                        raw = zf.read(info)
                        text = raw.decode("utf-8", errors="ignore")
                        for line in text.splitlines():
                            if not line.startswith("commit:"):
                                continue
                            # format: commit:HASH|%an|%ae|%ct|%s
                            parts = line[len("commit:"):].split("|")
                            if len(parts) < 2:
                                continue
                            author = parts[1].strip()
                            if not author or author.lower().endswith("[bot]"):
                                continue
                            email: str | None = None
                            if len(parts) >= 3:
                                raw_email = parts[2].strip()
                                if raw_email and not _is_noreply_email(raw_email):
                                    email = raw_email
                            raw_entries.append((author, email))
                    except Exception:
                        continue
    except Exception:
        pass

    # Deduplicate: email takes priority (keeps first occurrence per email, then per name)
    seen_emails: set[str] = set()
    seen_names: set[str] = set()
    result: list[tuple[str, str | None]] = []
    for name, email in raw_entries:
        if email:
            if email in seen_emails:
                continue
            seen_emails.add(email)
        name_key = name.lower()
        if name_key in seen_names:
            continue
        seen_names.add(name_key)
        result.append((name, email))
    return result


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
async def upload_project(
    project_id: str,
    file: UploadFile = File(...),   
):
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

    existing = conn.execute(
        "SELECT 1 FROM uploads WHERE upload_id = ? LIMIT 1",
        (project_id,),
    ).fetchone()

    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Project ID '{project_id}' already exists."
        )
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
        "file_count": len(manifest.get("files", [])),
        "file_summary": _build_file_summary_from_zip(Path(stored["path"])),
    }
    
    storage.store_analysis_snapshot(
        conn,
        project_id=project_id,
        classification="unknown",
        primary_contributor=None,
        snapshot=snapshot,
        zip_path = stored["path"] 
    )
    log_event("SUCCESS", f"Analysis snapshot stored · Project: {project_id}")
    # Mirror GitHub import flow: extract git-log contributors and store in users/user_projects.
    # Pass email alongside the git author name so upsert_user can reconcile with the same
    # person's GitHub-login record (matched by shared email) rather than creating a duplicate.
    try:
        contributors = _extract_contributors_from_zip(conn, stored["file_id"])
        for cname, cemail in contributors:
            uid = storage.upsert_user(conn, cname, email=cemail)
            storage.link_user_to_project(conn, uid, project_id, contributor_name=cname)
    except Exception:
        pass  # non-fatal; contributors will be populated on full analysis

    message = "Upload stored successfully."
    if stored.get("dedup"):
        log_event("WARNING", f"Duplicate upload detected · Project: {project_id}")
        message = "Duplicate upload detected; existing file reused."
    elif auto_detected:
        log_event("SUCCESS", f"Upload matched to existing project · Project: {project_id}")
        message = "Upload stored and matched to existing project automatically."
    else: 
        log_event("SUCCESS", f"New project uploaded · Project: {project_id}")
    if storage_module.CURRENT_USER:
        try:
            upload_project_zip(
                storage_module.CURRENT_USER,
                project_id,
                Path(stored["path"]),
                filename,
            )
            upload_database(storage_module.CURRENT_USER)
        except Exception:
            log_event("WARNING", f"Cloud sync failed after upload · Project: {project_id}")
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


@router.post("/upload-bundle")
async def upload_project_bundle(file: UploadFile = File(...)):
    """Upload a multi-project zip bundle.

    Each top-level directory inside the zip is treated as a separate project
    and stored independently.  Returns a list of per-project records.

    If the zip contains only one top-level directory it is stored the same as
    a regular ``POST /projects/upload`` call.
    """
    filename = file.filename or "upload.zip"
    if not filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip files are supported")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)

    try:
        # --- Discover top-level directories ---
        try:
            with zipfile.ZipFile(tmp_path) as src:
                top_dirs: dict[str, list] = {}
                for info in src.infolist():
                    if info.is_dir():
                        continue
                    name = info.filename.strip("/")
                    if not name:
                        continue
                    parts = [p for p in name.split("/") if p]
                    top = parts[0]
                    if top.startswith("__MACOSX"):
                        continue
                    top_dirs.setdefault(top, []).append(info)
        except zipfile.BadZipFile:
            raise HTTPException(status_code=400, detail="Invalid zip archive")

        if not top_dirs:
            raise HTTPException(status_code=400, detail="Zip archive is empty")

        conn = storage.open_db()
        results = []

        for sub_name in sorted(top_dirs.keys()):
            entries = top_dirs[sub_name]

            # Repackage this subproject into its own temporary zip
            with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as sub_tmp:
                sub_tmp_path = Path(sub_tmp.name)

            try:
                with zipfile.ZipFile(tmp_path) as src:
                    with zipfile.ZipFile(sub_tmp_path, "w", zipfile.ZIP_DEFLATED) as out:
                        for info in entries:
                            out.writestr(info, src.read(info))

                sub_filename = f"{sub_name}.zip"

                # Try to match an existing project, otherwise generate a new id
                project_id = _auto_detect_project_id(conn, sub_tmp_path, sub_filename)
                auto_detected = bool(project_id)
                if not project_id:
                    project_id = _generate_project_id_from_zip(conn, sub_tmp_path, sub_filename)

                stored = file_store.ensure_file(
                    conn,
                    sub_tmp_path,
                    original_name=sub_filename,
                    source="api_upload_bundle",
                    mime="application/zip",
                    upload_id=project_id,
                )
                project_id = stored["upload_id"]

                manifest = _inspect_stored_zip_manifest(conn, stored["file_id"])
                snapshot = {
                    "project_id": project_id,
                    "skills": manifest.get("skills", {}),
                    "root_name": manifest.get("root_name") or sub_name,
                    "file_count": len(manifest.get("files", [])),
                    "source": "multi_project_zip",
                    "file_summary": _build_file_summary_from_zip(sub_tmp_path),
                }
                storage.store_analysis_snapshot(
                    conn,
                    project_id=project_id,
                    classification="unknown",
                    primary_contributor=None,
                    snapshot=snapshot,
                )

                try:
                    contributors = _extract_contributors_from_zip(conn, stored["file_id"])
                    for cname, cemail in contributors:
                        uid = storage.upsert_user(conn, cname, email=cemail)
                        storage.link_user_to_project(conn, uid, project_id, contributor_name=cname)
                except Exception:
                    pass  # non-fatal

                results.append(
                    {
                        "project_id": project_id,
                        "subproject_name": sub_name,
                        "auto_detected_project_id": auto_detected,
                        "file_id": stored["file_id"],
                        "hash": stored["hash"],
                        "dedup": stored["dedup"],
                        "size_bytes": stored["size_bytes"],
                        "file_count": snapshot["file_count"],
                        "skills": snapshot["skills"],
                    }
                )
                if storage_module.CURRENT_USER:
                    try:
                        upload_project_zip(
                            storage_module.CURRENT_USER,
                            project_id,
                            Path(stored["path"]),
                            sub_filename,
                        )
                    except Exception:
                        log_event("WARNING", f"Cloud zip sync failed after bundle upload · Project: {project_id}")
            finally:
                try:
                    sub_tmp_path.unlink(missing_ok=True)
                except Exception:
                    pass

    finally:
        try:
            tmp_path.unlink(missing_ok=True)          
        except Exception:
            pass

        if storage_module.CURRENT_USER:
            try:
                upload_database(storage_module.CURRENT_USER)
            except Exception:
                pass

    return {
        "message": f"Bundle split into {len(results)} project(s).",
        "count": len(results),
        "projects": results,
    }


@router.get("")
def list_projects(request: Request):
    """
    Lists uploaded .zip projects from CAS storage.
    """
    _restore_user_from_request(request)
    conn = storage.open_db()
    try:
        rows = conn.execute(
            """
            SELECT u.upload_id, u.original_name, u.file_id, u.hash, u.created_at,
                   f.size_bytes, f.path
            FROM uploads u
            JOIN files f ON f.file_id = u.file_id
            ORDER BY datetime(u.created_at) DESC
            """
        ).fetchall()
    except Exception as exc:
        if "no such table" not in str(exc).lower():
            raise
        rows = []
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
def get_project(id: str, request: Request):
    """
    Returns info for a specific uploaded project zip by upload_id.
    """
    _restore_user_from_request(request)
    conn = storage.open_db()
    try:
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
    except Exception as exc:
        if "no such table" not in str(exc).lower():
            raise
        row = None

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
    Deletes a project and its associated stored file (ZIP upload) or
    GitHub-imported entry (no local blob).
    """
    conn = storage.open_db()

    # --- ZIP-upload path: project lives in uploads + files tables ---
    upload_row = conn.execute(
        """
        SELECT u.file_id, f.path, u.original_name
        FROM uploads u
        JOIN files f ON f.file_id = u.file_id
        WHERE u.upload_id = ?
        """,
        (id,),
    ).fetchone()

    # --- GitHub-import path: project lives only in github_projects / project_analysis ---
    github_row = conn.execute(
        "SELECT project_id FROM github_projects WHERE project_id = ?",
        (id,),
    ).fetchone() if not upload_row else None

    if not upload_row and not github_row:
        # Last chance: project may exist only in project_analysis (e.g. older imports)
        analysis_row = conn.execute(
            "SELECT project_id FROM project_analysis WHERE project_id = ? LIMIT 1",
            (id,),
        ).fetchone()
        if not analysis_row:
            log_event("ERROR", "Project not found · Project: ")
            raise HTTPException(status_code=404, detail="Project not found")

    file_id = None
    original_name = None

    if upload_row:
        file_id, file_path, original_name = upload_row

        conn.execute("DELETE FROM uploads WHERE upload_id = ?", (id,))

        remaining_refs = conn.execute(
            "SELECT COUNT(*) FROM uploads WHERE file_id = ?",
            (file_id,),
        ).fetchone()[0]

        should_delete_blob = remaining_refs == 0

        if should_delete_blob:
            conn.execute("DELETE FROM files WHERE file_id = ?", (file_id,))
        else:
            conn.execute(
                "UPDATE files SET ref_count = CASE WHEN ref_count > 0 THEN ref_count - 1 ELSE 0 END WHERE file_id = ?",
                (file_id,),
            )

    # Always remove shared analysis / contributor records
    conn.execute("DELETE FROM project_analysis WHERE project_id = ?", (id,))
    conn.execute("DELETE FROM user_projects WHERE project_id = ?", (id,))
    conn.execute("DELETE FROM github_projects WHERE project_id = ?", (id,))
    conn.commit()

    # Remove physical blob only when no other upload references it
    if upload_row and should_delete_blob:
        try:
            Path(file_path).unlink(missing_ok=True)
        except Exception:
            pass

    # Best-effort cloud cleanup
    if storage_module.CURRENT_USER:
        try:
            delete_project_zip(
                storage_module.CURRENT_USER,
                id,
                original_name or "project.zip",
            )
        except Exception:
            pass

        try:
            upload_database(storage_module.CURRENT_USER)
        except Exception:
            pass

    log_event("WARNING", f"Project deleted · Project: {id}")

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
    log_event("SUCCESS", f"Thumbnail updated · Project: {id}")
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
        "SELECT 1 FROM project_analysis WHERE project_id = ? LIMIT 1",
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
    log_event("INFO", f"Project overrides updated · Project: {id}")
    return {"data": updated, "error": None}


@router.post("/{id}/edit")
def edit_project_legacy(id: str, payload: ProjectEdit):
    """
    Backward-compatible alias for older clients still posting to /projects/{id}/edit.
    """
    return edit_project(id, payload)


@router.get("/{id}/overrides")
def get_project_overrides(id: str):
    conn = storage.open_db()
    data = storage.fetch_project_overrides(conn, id)
    if not data:
        raise HTTPException(status_code=404, detail="No overrides found")
    return {"data": data, "error": None}


@router.post("/{project_id}/generate-resume")
async def generate_project_resume(project_id: str, request: Request):
    """Generate a modular resume (resumes/resume_sections/resume_items) from a zip project.

    Mirrors the GitHub import resume flow:
    1. Resolves the contributor/user for this project.
    2. Extracts skills and builds a project summary from the stored snapshot.
    3. Calls upsert_default_resume_modules to persist to the new resume tables.

    Optional JSON body:
      { "username": "<github_username>" }   -- pick a specific contributor
    """
    try:
        body = await request.json()
    except Exception:
        body = {}
    requested_username: str | None = (body.get("username") or "").strip() or None

    conn = storage.open_db()

    # 1. Verify project exists and get latest snapshot
    snap = storage.fetch_latest_snapshot(conn, project_id)
    if snap is None:
        raise HTTPException(status_code=404, detail="Project not found or not yet analyzed")

    # 2. Resolve the contributor to use as the resume owner
    username = requested_username
    if not username:
        # Prefer primary_contributor from snapshot collaboration data
        collab = snap.get("collaboration") or {}
        username = (
            collab.get("primary_contributor")
            or snap.get("primary_contributor")
        )
    if not username:
        # Fall back to any contributor linked to this project
        linked = conn.execute(
            """
            SELECT u.username
            FROM user_projects up
            JOIN users u ON u.id = up.user_id
            WHERE up.project_id = ?
            ORDER BY up.id
            LIMIT 1
            """,
            (project_id,),
        ).fetchone()
        if linked:
            username = linked[0]
    if not username:
        username = project_id  # last-resort fallback

    # 3. Upsert user and ensure project link
    user_id = storage.upsert_user(conn, username)
    storage.link_user_to_project(conn, user_id, project_id, contributor_name=username)

    # 4. Extract skills from snapshot (languages + frameworks + skills list)
    skill_names: list[str] = []
    seen_skills: set[str] = set()

    def _add_skill(name: str) -> None:
        key = name.strip().lower()
        if key and key not in seen_skills:
            seen_skills.add(key)
            skill_names.append(name.strip())

    langs = snap.get("languages") or {}
    if isinstance(langs, dict):
        for lang in langs:
            _add_skill(lang)

    frameworks = snap.get("frameworks") or []
    if isinstance(frameworks, list):
        for fw in frameworks:
            if fw:
                _add_skill(str(fw))

    raw_skills = snap.get("skills") or []
    if isinstance(raw_skills, list):
        for item in raw_skills:
            if isinstance(item, dict):
                name = item.get("skill") or item.get("name") or ""
                if name:
                    _add_skill(str(name))
            elif item:
                _add_skill(str(item))
    elif isinstance(raw_skills, dict):
        for name in raw_skills:
            _add_skill(name)

    # 5. Build project item from snapshot
    project_item = build_resume_project_item(project_id, snap)
    if not project_item.get("title"):
        project_item["title"] = snap.get("project_name") or snap.get("root_name") or project_id

    project_items = [project_item]

    # 6. Build header from user profile
    user_profile = storage.get_user_profile(conn, user_id) or {}
    city = (user_profile.get("city") or "").strip()
    state = (user_profile.get("state_region") or "").strip()
    location = ", ".join(part for part in [city, state] if part)
    header = {
        "full_name": (user_profile.get("full_name") or username).strip(),
        "email": (user_profile.get("email") or "").strip(),
        "phone": (user_profile.get("phone_number") or "").strip(),
        "location": location,
        "github_url": (user_profile.get("github_url") or "").strip(),
        "portfolio_url": (user_profile.get("portfolio_url") or "").strip(),
    }

    # 7. Persist using the modular resume tables (same as GitHub import flow)
    resume_id = storage.upsert_default_resume_modules(
        conn,
        user_id=user_id,
        header=header,
        core_skills=skill_names,
        projects=project_items,
        create_new=True,
    )

    return {
        "data": {
            "resume_id": resume_id,
            "user_id": user_id,
            "username": username,
            "project_id": project_id,
        },
        "error": None,
    }
