from fastapi import APIRouter
from typing import List
from pydantic import BaseModel
from datetime import datetime
import sqlite3
from capstone.portfolio_retrieval import _db_session
from capstone.activity_log import log_event

router = APIRouter()


class RecentProject(BaseModel):
    project_id: str
    created_at: datetime
    total_files: int
    total_skills: int
    classification: str | None
    primary_contributor: str | None
    is_github: bool
    contributor_count: int


import json


def _load_upload_ids(db) -> set[str]:
    try:
        return {
            str(row[0]).strip()
            for row in db.execute("SELECT DISTINCT upload_id FROM uploads").fetchall()
            if str(row[0]).strip()
        }
    except sqlite3.OperationalError as exc:
        if "no such table" in str(exc).lower() and "uploads" in str(exc).lower():
            log_event("WARNING", "Recent projects loaded without uploads table; falling back to snapshot-only filtering")
            return set()
        raise

@router.get("/dashboard/recent-projects", response_model=List[RecentProject])
def get_recent_projects():
    with _db_session(None) as db:
        rows = db.execute("""
SELECT
    pa.project_id,
    pa.created_at,
    pa.snapshot,
    pa.classification,
    pa.primary_contributor,
    CASE
        WHEN gp.project_id IS NOT NULL THEN 1
        ELSE 0
    END AS is_github,
    COALESCE(uc.cnt, 0) AS contributor_count
FROM project_analysis pa
LEFT JOIN github_projects gp
    ON pa.project_id = gp.project_id
LEFT JOIN (
    SELECT project_id, COUNT(DISTINCT user_id) AS cnt
    FROM user_projects
    GROUP BY project_id
) uc ON pa.project_id = uc.project_id
WHERE pa.rowid IN (
    SELECT MAX(rowid)
    FROM project_analysis
    GROUP BY project_id
)
ORDER BY pa.created_at DESC
""").fetchall()

        upload_ids = _load_upload_ids(db)

    projects = []

    for row in rows:
        project_id = row[0]
        created_at = row[1]
        snapshot_raw = row[2]
        classification = row[3]
        primary_contributor = row[4]
        is_github = bool(row[5])
        contributor_count = int(row[6])

        try:
            snapshot = json.loads(snapshot_raw)
        except Exception:
            log_event("WARNING", f"Skipping invalid project snapshot in recent projects · Project: {project_id}")
            continue

        normalized_project_id = str(project_id or "").strip()
        snapshot_project_id = str(snapshot.get("project_id") or snapshot.get("id") or "").strip()
        file_summary = snapshot.get("file_summary")
        has_file_summary = isinstance(file_summary, dict) and any(
            file_summary.get(key) not in (None, "", 0)
            for key in ("file_count", "active_days", "language_count", "total_lines")
        )
        raw_skills = snapshot.get("skills")
        has_skills = (
            isinstance(raw_skills, list) and len(raw_skills) > 0
        ) or (
            isinstance(raw_skills, dict) and len(raw_skills.keys()) > 0
        )

        # Filter out placeholder / broken recent-project entries that only have a bare
        # ID snapshot and no corresponding uploaded project in the current workspace.
        if normalized_project_id not in upload_ids and not has_file_summary and not has_skills:
            log_event(
                "WARNING",
                f"Skipping incomplete project snapshot in recent projects · Project: {normalized_project_id or snapshot_project_id or 'unknown'}",
            )
            continue

        # --- FILE COUNT ---
        if isinstance(file_summary, dict):
            total_files = file_summary.get("file_count", 0)
        else:
            total_files = snapshot.get("file_count", 0)

        # --- SKILL COUNT ---
        skills = snapshot.get("skills", [])

        if isinstance(skills, list):
            total_skills = len(skills)
        elif isinstance(skills, dict):
            total_skills = len(skills.keys())
        else:
            total_skills = 0

        projects.append({
            "project_id": project_id,
            "created_at": created_at,
            "total_files": total_files,
            "total_skills": total_skills,
            "classification": classification,
            "primary_contributor": primary_contributor,
            "is_github": is_github,
            "contributor_count": contributor_count
        })

    return projects
