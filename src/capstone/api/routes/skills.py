from fastapi import APIRouter, HTTPException
from pathlib import Path
import zipfile

from capstone import storage, file_store
from capstone.activity_log import log_event
router = APIRouter(tags=["skills"])

EXT_TO_SKILL = {
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

@router.get("/projects/{project_id}/skills")
def skills_for_project(project_id: str):
    conn = storage.open_db()
    row = conn.execute(
        """
        SELECT u.file_id
        FROM uploads u
        WHERE u.upload_id = ?
        ORDER BY datetime(u.created_at) DESC
        LIMIT 1
        """,
        (project_id,),
    ).fetchone()
    if not row:
        log_event("ERROR", f"Skills lookup failed · Project not found · {project_id}")
        raise HTTPException(status_code=404, detail="Project not found")

    file_id = row[0]
    try:
        with file_store.open_file(conn, file_id) as fh, zipfile.ZipFile(fh) as z:
            skills = {}
            for name in z.namelist():
                suffix = Path(name).suffix.lower()
                if suffix in EXT_TO_SKILL:
                    skill = EXT_TO_SKILL[suffix]
                    skills[skill] = skills.get(skill, 0) + 1
    except zipfile.BadZipFile:
        log_event("ERROR", f"Invalid zip during skills extraction · Project: {project_id}")
        raise HTTPException(status_code=400, detail="Stored file is not a valid zip")
    except FileNotFoundError:
        log_event("ERROR", f"Missing stored file during skills extraction · Project: {project_id}")
        raise HTTPException(
            status_code=409,
            detail="Stored upload file not found on this machine. Re-upload the project zip.",
        )

    return {
        "project_id": project_id,
        "file_id": file_id,
        "skills": [{"name": k, "evidence": f"{v} file(s) detected"} for k, v in skills.items()],
    }


@router.get("/skills")
def skills_all(limit: int = 200):
    """
    Aggregate skills across all uploaded projects.
    """
    conn = storage.open_db()
    rows = conn.execute(
        """
        SELECT u.upload_id, u.file_id
        FROM uploads u
        ORDER BY datetime(u.created_at) DESC
        """
    ).fetchall()

    # total file hits and distinct project count.
    skills: dict[str, dict[str, int]] = {}
    processed = 0
    for _, file_id in rows:
        if processed >= limit:
            break
        try:
            # Open each uploaded zip
            with file_store.open_file(conn, file_id) as fh, zipfile.ZipFile(fh) as z:
                seen: set[str] = set()
                for name in z.namelist():
                    suffix = Path(name).suffix.lower()
                    if suffix in EXT_TO_SKILL:
                        skill = EXT_TO_SKILL[suffix]
                        bucket = skills.setdefault(skill, {"files": 0, "projects": 0})
                        bucket["files"] += 1
                        seen.add(skill)
                for skill in seen:
                    bucket = skills.setdefault(skill, {"files": 0, "projects": 0})
                    bucket["projects"] += 1
        except (zipfile.BadZipFile, FileNotFoundError):
            continue
        processed += 1
    log_event("INFO", f"Global skills aggregation computed · Projects scanned: {processed}")
    return {
        "count": len(skills),
        "processed": processed,
        "skills": [
            {
                "name": name,
                "files": stats["files"],
                "projects": stats["projects"],
            }
            for name, stats in sorted(skills.items(), key=lambda it: (-it[1]["projects"], it[0]))
        ],
    }
