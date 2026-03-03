from fastapi import APIRouter
from typing import List
from pydantic import BaseModel
from datetime import datetime
from capstone.portfolio_retrieval import _db_session

router = APIRouter()


class RecentProject(BaseModel):
    project_id: str
    created_at: datetime
    total_files: int
    total_skills: int
    classification: str | None
    primary_contributor: str | None


import json

@router.get("/dashboard/recent-projects", response_model=List[RecentProject])
def get_recent_projects():
    with _db_session(None) as db:
        rows = db.execute("""
            SELECT pa.project_id,
       pa.created_at,
       pa.snapshot,
       pa.classification,
       pa.primary_contributor
FROM project_analysis pa
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

        snapshot = json.loads(snapshot_raw)

        total_files = snapshot.get("file_count", 0)

        skills = snapshot.get("skills", {})
        total_skills = len(skills) if isinstance(skills, dict) else 0

        projects.append({
            "project_id": project_id,
            "created_at": created_at,
            "total_files": total_files,
            "total_skills": total_skills,
            "classification": classification,
            "primary_contributor": primary_contributor,
        })

    return projects