from datetime import datetime
from typing import List

from fastapi import APIRouter, Request
from pydantic import BaseModel

from capstone import storage
from capstone.api.routes.projects import _build_project_summary_list, _restore_user_from_request

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

@router.get("/dashboard/recent-projects", response_model=List[RecentProject])
def get_recent_projects(request: Request):
    _restore_user_from_request(request)
    conn = storage.open_db()
    try:
        projects = _build_project_summary_list(conn)
    except Exception as exc:
        if "no such table" not in str(exc).lower():
            raise
        projects = []
    return projects[:5]
