from fastapi import APIRouter
from typing import List
from pydantic import BaseModel
from datetime import datetime
import sqlite3
from capstone.portfolio_retrieval import _db_session
from capstone.activity_log import log_event
import capstone.storage as storage

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


def _fallback_projects_from_uploads(db) -> list[dict]:
    rows = db.execute(
        """
        SELECT
            u.upload_id,
            MAX(u.created_at) AS created_at
        FROM uploads u
        WHERE u.upload_id IS NOT NULL AND TRIM(u.upload_id) != ''
        GROUP BY u.upload_id
        ORDER BY datetime(MAX(u.created_at)) DESC
        """
    ).fetchall()
    payload = []
    for project_id, created_at in rows:
        payload.append(
            {
                "project_id": project_id,
                "created_at": created_at,
                "total_files": 0,
                "total_skills": 0,
                "classification": None,
                "primary_contributor": None,
                "is_github": False,
                "contributor_count": 0,
            }
        )
    return payload


def _fallback_projects_from_cloud(storage_user_key: str | None) -> list[dict]:
    if not storage_user_key:
        return []
    try:
        from capstone.system.cloud_storage import BUCKET_NAME, list_objects

        prefix = f"users/{storage_user_key}/projects/"
        resp = list_objects(BUCKET_NAME, prefix) or {}
        objects = resp.get("Contents") or []
        by_project: dict[str, str] = {}
        for obj in objects:
            key = str(obj.get("Key") or "")
            if not key.startswith(prefix):
                continue
            suffix = key[len(prefix):]
            project_id = suffix.split("/", 1)[0].strip()
            if not project_id:
                continue
            last_modified = str(obj.get("LastModified") or "")
            by_project[project_id] = max(last_modified, by_project.get(project_id, ""))

        payload = []
        for project_id, created_at in by_project.items():
            payload.append(
                {
                    "project_id": project_id,
                    "created_at": created_at or datetime.utcnow().isoformat(),
                    "total_files": 0,
                    "total_skills": 0,
                    "classification": None,
                    "primary_contributor": None,
                    "is_github": False,
                    "contributor_count": 0,
                }
            )
        payload.sort(key=lambda row: str(row.get("created_at") or ""), reverse=True)
        return payload
    except Exception:
        return []

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
        uploads_fallback = _fallback_projects_from_uploads(db)

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
        # Only enforce upload_id membership when the uploads table actually has rows;
        # otherwise "not in upload_ids" is true for every project and we would hide all
        # snapshots that lack file_summary/skills (common for GitHub imports or older DBs).
        if (
            upload_ids
            and normalized_project_id not in upload_ids
            and not has_file_summary
            and not has_skills
        ):
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

    storage_user_key = storage.resolve_storage_user_key(storage.get_current_user())
    cloud_fallback = _fallback_projects_from_cloud(storage_user_key) if storage_user_key else []

    # In authenticated mode the cloud is the source of truth.
    # Build a merged list where cloud projects are always shown, supplemented
    # by local analysis data when available.  Local-only projects (not yet
    # confirmed in the cloud) are included only when they have real content
    # (non-zero file or skill count) so that stale test/ghost entries are
    # suppressed without hiding a project whose cloud upload just failed.
    if storage_user_key and cloud_fallback:
        cloud_project_ids = {str(row.get("project_id")) for row in cloud_fallback}
        if projects:
            local_by_id = {str(p.get("project_id")): p for p in projects}
            merged: dict = {}
            for row in cloud_fallback:
                pid = str(row.get("project_id"))
                # Use local data (has real stats) when available, cloud stub otherwise
                merged[pid] = local_by_id.get(pid, row)
            # Include local-only projects that have real content (not phantom entries)
            for p in projects:
                pid = str(p.get("project_id"))
                if pid not in cloud_project_ids:
                    has_content = int(p.get("total_files") or 0) > 0 or int(p.get("total_skills") or 0) > 0
                    if has_content:
                        merged.setdefault(pid, p)
            return list(merged.values())
        # Do not return cloud-only stubs here when local uploads exist: those rows are
        # what DELETE /projects/{id} removes. Returning cloud first hid uploads and made
        # the last local project undeletable (404) or out of sync with the card id.

    if not projects and uploads_fallback:
        log_event(
            "WARNING",
            "Recent projects fallback activated: project_analysis empty/incomplete, serving uploads-based list",
        )
        if storage_user_key and cloud_fallback:
            seen = {str(u.get("project_id")) for u in uploads_fallback if u.get("project_id")}
            extra = [
                row
                for row in cloud_fallback
                if str(row.get("project_id") or "") not in seen
            ]
            return uploads_fallback + extra
        return uploads_fallback

    if not projects and cloud_fallback:
        log_event(
            "WARNING",
            "Recent projects fallback activated: serving cloud prefix projects",
        )
        return cloud_fallback

    return projects
