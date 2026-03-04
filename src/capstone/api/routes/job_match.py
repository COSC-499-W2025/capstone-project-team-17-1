from __future__ import annotations

import json
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from capstone.job_matching import (
    match_job_to_project,
    build_resume_snippet,
    build_jd_profile,
    rank_projects_for_job,
    matches_to_json,
)
from capstone.storage import open_db, close_db
from capstone.activity_log import log_event

router = APIRouter(prefix="/job-matching", tags=["job-matching"])


class JobMatchRequest(BaseModel):
    project_id: str = Field(..., description="Project ID in db")
    job_description: str = Field(..., description="Raw job description text")


class JobRankingRequest(BaseModel):
    job_description: str = Field(..., description="Raw job description text")


@router.post("/match")
def match_single_project(payload: JobMatchRequest) -> Dict[str, Any]:
    try:
        result = match_job_to_project(
            job_text=payload.job_description,
            project_id=payload.project_id,
            db_dir=None,
        )

        log_event(
            "SUCCESS",
            f"Job match completed · Project: {payload.project_id}"
        )

    except Exception as e:
        log_event(
            "ERROR",
            f"Job match failed · Project: {payload.project_id} · {str(e)}"
        )
        raise HTTPException(status_code=400, detail=str(e))

    snippet = build_resume_snippet(result)

    return {
        "project_id": result.project_id,
        "job_skills": result.job_skills,
        "matched_skills": result.matched_skills,
        "missing_skills": result.missing_skills,
        "resume_snippet": snippet,
    }


@router.post("/rank")
def rank_projects(
    payload: JobRankingRequest,
    top_k: int = Query(10, ge=1, le=100, description="Return top K matches (1–100). Default 10."),
) -> Any:
    conn = open_db(None)
    try:
        cursor = conn.execute("SELECT project_id, snapshot FROM project_analysis")
        rows = cursor.fetchall()

        if not rows:
            raise HTTPException(status_code=404, detail="No projects in database")

        project_snapshots: List[Dict[str, Any]] = []
        for project_id, snapshot_json in rows:
            snap = json.loads(snapshot_json)
            snap["project_id"] = project_id
            project_snapshots.append(snap)

        if not project_snapshots:
            raise HTTPException(status_code=404, detail="No project snapshots found in database")

    finally:
        # keep your existing close_db behavior, but also try to close conn safely
        try:
            conn.close()
        except Exception:
            pass
        close_db()

    jd_profile = build_jd_profile(payload.job_description)
    matches = rank_projects_for_job(jd_profile, project_snapshots)

    matches = matches[:top_k]
    log_event(
    "INFO",
    f"Job ranking executed · Candidates: {len(project_snapshots)} · Returned: {len(matches)}"
)
    
    return matches_to_json(matches)