from fastapi import APIRouter
from typing import List
from pydantic import BaseModel
from datetime import datetime
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

        # --- FILE COUNT ---
        file_summary = snapshot.get("file_summary")

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
