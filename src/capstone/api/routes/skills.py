from fastapi import APIRouter, HTTPException
from pathlib import Path
import zipfile
import json

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


def _skills_from_snapshot(conn, project_id: str):
    latest = storage.fetch_latest_snapshot(conn, project_id)
    if not latest:
        return []

    raw_skills = latest.get("snapshot", {}).get("skills", [])
    results = []
    if isinstance(raw_skills, list):
        for item in raw_skills:
            if isinstance(item, dict):
                name = str(item.get("skill") or item.get("name") or "").strip()
                if name:
                    results.append({"name": name, "evidence": "Recovered from stored snapshot"})
            else:
                name = str(item).strip()
                if name:
                    results.append({"name": name, "evidence": "Recovered from stored snapshot"})
    elif isinstance(raw_skills, dict):
        for name, value in raw_skills.items():
            results.append({"name": str(name), "evidence": f"Recovered from stored snapshot ({value})"})
    return results

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
        log_event("WARNING", f"Skills lookup skipped · No stored upload found for project · {project_id}")
        return {
            "project_id": project_id,
            "skills": [],
            "skipped": True,
            "detail": "No stored upload was found for this project in the current workspace.",
        }

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
        log_event("WARNING", f"Invalid zip during skills extraction; falling back to snapshot skills · Project: {project_id}")
        snapshot_skills = _skills_from_snapshot(conn, project_id)
        if snapshot_skills:
            return {
                "project_id": project_id,
                "file_id": file_id,
                "skills": snapshot_skills,
                "fallback": "snapshot",
            }
        raise HTTPException(
            status_code=400,
            detail="The stored project file is no longer a valid zip archive.",
        )
    except FileNotFoundError:
        log_event("WARNING", f"Missing stored file during skills extraction; falling back to snapshot skills · Project: {project_id}")
        snapshot_skills = _skills_from_snapshot(conn, project_id)
        if snapshot_skills:
            return {
                "project_id": project_id,
                "file_id": file_id,
                "skills": snapshot_skills,
                "fallback": "snapshot",
            }
        raise HTTPException(
            status_code=409,
            detail="The stored project file is missing on this machine. Re-upload the project zip to refresh skills.",
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

@router.get("/skills/timeline")
def skills_timeline(top_n: int = 5):
    """
    Return one skills timeline node per stored analysis snapshot.
    Each node is timestamped using project_analysis.created_at so the frontend can
    render exact analysis times instead of coarse yearly buckets.
    """
    conn = storage.open_db()

    try:
        rows = conn.execute(
            """
            SELECT project_id, snapshot, created_at
            FROM project_analysis
            ORDER BY datetime(created_at) ASC, id ASC
            """
        ).fetchall()

        timeline = []
        for project_id, snapshot_raw, created_at in rows:
            try:
                snapshot = json.loads(snapshot_raw) if isinstance(snapshot_raw, str) else snapshot_raw
            except Exception:
                continue

            snapshot = snapshot or {}
            raw_skills = snapshot.get("skills") or []
            skills = []
            file_summary = snapshot.get("file_summary") or {}
            file_count = 0
            active_days = 0

            if isinstance(file_summary, dict):
                file_count = int(file_summary.get("file_count", 0) or 0)
                active_days = int(file_summary.get("active_days", 0) or 0)

            skill_count = 0

            if isinstance(raw_skills, dict):
                ranked = sorted(raw_skills.items(), key=lambda item: (-float(item[1] or 0), item[0]))
                skills = [
                    {"skill": name, "weight": float(weight or 0.0)}
                    for name, weight in ranked[: max(1, top_n)]
                ]
                skill_count = len(raw_skills)
            elif isinstance(raw_skills, list):
                normalized = []
                for skill in raw_skills:
                    if isinstance(skill, dict):
                        name = skill.get("skill") or skill.get("name")
                        weight = skill.get("score", skill.get("weight", 0.0))
                        if name:
                            normalized.append((str(name), float(weight or 0.0)))
                normalized.sort(key=lambda item: (-item[1], item[0]))
                skills = [
                    {"skill": name, "weight": weight}
                    for name, weight in normalized[: max(1, top_n)]
                ]
                skill_count = len(normalized)

            complexity_score = round(
                file_count * 0.04
                + active_days * 0.35
                + skill_count * 0.45,
                2,
            )

            timeline.append({
                "project_id": str(project_id),
                "timestamp": str(created_at),
                "skills": skills,
                "project_metrics": {
                    "file_count": file_count,
                    "active_days": active_days,
                    "skill_count": skill_count,
                    "complexity_score": complexity_score,
                },
            })

        log_event("INFO", f"Skills timeline generated · Nodes: {len(timeline)}")

        return {
            "count": len(timeline),
            "timeline": timeline,
        }

    except Exception as exc:
        log_event("ERROR", f"Skills timeline generation failed · {exc}")
        raise HTTPException(status_code=500, detail="Failed to generate skills timeline")
