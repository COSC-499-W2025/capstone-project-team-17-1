from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, HTTPException, Request
from capstone.activity_log import log_event

from capstone.portfolio_retrieval import _db_session, _extract_evidence, _parse_view, get_portfolio_entry
from capstone.resume_retrieval import (
    build_resume_project_summary,
    ensure_resume_schema,
    get_resume_project_description,
    upsert_resume_project_description
)
from capstone.storage import fetch_latest_snapshot, fetch_latest_snapshots
from capstone.top_project_summaries import generate_top_project_summaries, export_markdown

from capstone.api.portfolio_helpers import ensure_indexes, list_snapshots, ensure_portfolio_tables

router = APIRouter(prefix="/showcase", tags=["portfolio", "resume", "users"])

# global variables
_DB_DIR: Optional[str] = None   # SQLite db path
_TOKEN: Optional[str] = None   # optional auth token to protect endpoints

# for server startup
def configure(db_dir: Optional[str], auth_token: Optional[str]) -> None:
    global _DB_DIR, _TOKEN
    _DB_DIR = db_dir
    _TOKEN = auth_token

# token check for if auth is required
def _check_auth(request: Request) -> None:
    # skip auth
    if not _TOKEN:
        return
    # auth header check
    h = request.headers.get("Authorization", "")
    if not (h.startswith("Bearer ") and h.split(" ", 1)[1] == _TOKEN):
        raise HTTPException(status_code=401, detail="Missing or invalid token")

def _require_db() -> Optional[str]:
    return _DB_DIR

# align naming used in handlers
get_latest_snapshot = fetch_latest_snapshot

async def _get_payload(request: Request) -> dict:
    try:
        return await request.json()
    except Exception:
        return {}

@router.get("/users")
def list_users(request: Request):
    from capstone.github_contributors import _is_noreply_email, _is_bot_contributor
    _check_auth(request)
    with _db_session(_require_db()) as c:
        rows = c.execute("""
            SELECT DISTINCT u.id, u.username, u.email
            FROM users u
            INNER JOIN user_projects up ON u.id = up.user_id
            INNER JOIN project_analysis pa ON up.project_id = pa.project_id
            -- Exclude no-email users when another user WITH an email is
            -- already linked to at least one of the same projects.
            -- This removes git-fullname duplicates when the GitHub-login
            -- version (with real email) is also present.
            WHERE NOT (
                u.email IS NULL
                AND EXISTS (
                    SELECT 1 FROM users u2
                    INNER JOIN user_projects up2 ON u2.id = up2.user_id
                    WHERE u2.email IS NOT NULL
                      AND u2.id != u.id
                      AND up2.project_id IN (
                          SELECT project_id FROM user_projects WHERE user_id = u.id
                      )
                )
            )
            ORDER BY LOWER(u.username)
        """).fetchall()
    users = [
        {"id": r[0], "username": r[1]}
        for r in rows
        if r and r[1]
        and not _is_bot_contributor(r[1])
        and not _is_noreply_email(r[2])
    ]
    return {"data": users, "error": None}

@router.get("/users/{user}/projects")
def list_user_projects(user: str, request: Request):
    _check_auth(request)
    with _db_session(_require_db()) as c:
        rows = c.execute(
            "SELECT DISTINCT project_id FROM contributor_stats WHERE contributor = ? ORDER BY project_id",
            (user,),
        ).fetchall()
    projects = [r[0] for r in rows if r and r[0]]
    return {"data": projects, "error": None}

@router.get("/portfolio/summary")
def portfolio_summary(user: str, request: Request, limit: int = 3):
    _check_auth(request)
    with _db_session(_require_db()) as c:
        snapshots = fetch_latest_snapshots(c)
    snapshot_map = {
        str(item.get("project_id")): (item.get("snapshot") or {})
        for item in snapshots
        if item.get("project_id")
    }
    summaries = generate_top_project_summaries(snapshot_map, limit=limit, user=user)
    payload = [export_markdown(item) for item in summaries]
    return {"data": payload, "meta": {"user": user, "limit": limit}, "error": None}


@router.get("/portfolios/latest")
def latest(request: Request, projectId: str, view: Optional[str] = None, user: Optional[str] = None):
    _check_auth(request)
    view = _parse_view(view)

    user_role = None
    if user:
        with _db_session(_require_db()) as c:
            row = c.execute(
                "SELECT 1 FROM contributor_stats WHERE project_id = ? AND contributor = ? LIMIT 1",
                (projectId, user),
            ).fetchone()
        if row:
            user_role = "primary_contributor"

    if view == "resume":
        with _db_session(_require_db()) as c:
            ensure_resume_schema(c)
            item = get_resume_project_description(c, projectId)
        if not item:
            log_event("ERROR", f"No resume found · Project: {projectId}")
            raise HTTPException(status_code=404, detail="No resume project found")
        
        log_event("INFO", f"Resume accessed · Project: {projectId}")
        return {
            "data": item.to_dict(),
            "meta": {"projectId": projectId, "view": "resume", "user": user, "userRole": user_role},
            "error": None,
        }

    with _db_session(_require_db()) as c:
        ensure_indexes(c)
        data = get_latest_snapshot(c, projectId)
    if data is None:
        raise HTTPException(status_code=404, detail="No snapshots found")
    return {
        "data": data,
        "meta": {"projectId": projectId, "view": "portfolio", "user": user, "userRole": user_role},
        "error": None,
    }

@router.get("/portfolios/evidence")
def evidence_latest(request: Request, projectId: str):
    _check_auth(request)
    with _db_session(_require_db()) as c:
        ensure_indexes(c)
        snap = get_latest_snapshot(c, projectId)
    if snap is None:
        raise HTTPException(status_code=404, detail="No snapshots found")
    evidence = _extract_evidence(snap)
    return {"data": {"projectId": projectId, "evidence": evidence}, "error": None}


@router.get("/portfolios")
def list_(request: Request, projectId: str, page: int = 1, pageSize: int = 20, sort: str = "created_at:desc"):
    _check_auth(request)
    sort_field, _, sort_dir = sort.partition(":")
    with _db_session(_require_db()) as c:
        ensure_indexes(c)
        items, total = list_snapshots(
            c,
            project_id=projectId,
            page=int(page),
            page_size=int(pageSize),
            sort_field=sort_field or "created_at",
            sort_dir=sort_dir or "desc",
        )
    payload = [s.snapshot for s in items]
    return {
        "data": payload,
        "meta": {"projectId": projectId, "page": int(page), "pageSize": int(pageSize), "total": total},
        "error": None,
    }

@router.get("/portfolio/showcase")
def get_portfolio_showcase_query(request: Request, projectId: str, user: Optional[str] = None):
    return get_portfolio_showcase(projectId, request, user=user)

@router.get("/portfolio/{id}")
def get_portfolio_showcase(id: str, request: Request, user: Optional[str] = None):
    _check_auth(request)
    
    user_role = None
    if user:
        with _db_session(_require_db()) as c:
            row = c.execute(
                "SELECT 1 FROM contributor_stats WHERE project_id = ? AND contributor = ? LIMIT 1",
                (id, user),
            ).fetchone()
        if row:
            user_role = "primary_contributor"
            
    with _db_session(_require_db()) as c:
        ensure_portfolio_tables(c)
        ensure_indexes(c)
        entry = get_portfolio_entry(c, id)
        
    if entry:
        if user_role:
            entry["user_role"] = user_role
        return {"data": entry, "error": None}
    
    with _db_session(_require_db()) as c:
        ensure_resume_schema(c)
        item = get_resume_project_description(c, id, variant_name="portfolio_showcase")
        if item:
            payload = item.to_dict()
            if user_role:
                payload["user_role"] = user_role
            return {"data": payload, "error": None}
        
        snap = get_latest_snapshot(c, id)
    
    if not snap:
        log_event("ERROR", f"Snapshot not found · Project: {id}")
        raise HTTPException(status_code=404, detail="No snapshots found")
    
    summary = build_resume_project_summary(id, snap)
    payload = {"project_id": id, "summary": summary}
    if user_role:
        payload["user_role"] = user_role
    return {"data": payload, "error": None}


@router.post("/portfolio/generate")
async def generate_portfolio_showcase(request: Request):
    _check_auth(request)
    payload = await _get_payload(request)
    project_ids = payload.get("projectIds") or []
    if not project_ids or not isinstance(project_ids, list):
        raise HTTPException(status_code=400, detail="projectIds must be a list")
    results = []
    with _db_session(_require_db()) as c:
        ensure_resume_schema(c)
        for pid in project_ids:
            snap = get_latest_snapshot(c, str(pid))
            if not snap:
                log_event("WARNING", f"Portfolio generation skipped · No snapshot · {pid}")
                continue
            summary = build_resume_project_summary(str(pid), snap)
            item = upsert_resume_project_description(
                c,
                project_id=str(pid),
                summary=summary,
                variant_name="portfolio_showcase",
                metadata={"source": "auto"},
            )
            results.append(item.to_dict())

            log_event("SUCCESS", f"Portfolio generated · Project: {pid}")
    return {"data": results, "error": None}

@router.post("/portfolio/showcase/edit")
async def edit_portfolio_showcase_query(request: Request):
    _check_auth(request)
    payload = await _get_payload(request)
    project_id = (payload.get("projectId") or "").strip()
    summary = (payload.get("summary") or "").strip()
    if not project_id or not summary:
        raise HTTPException(status_code=400, detail="projectId and summary are required")
    return await edit_portfolio_showcase(project_id, request)

@router.post("/portfolio/{id}/edit")
async def edit_portfolio_showcase(id: str, request: Request):
    _check_auth(request)
    payload = await _get_payload(request)
    summary = (payload.get("summary") or "").strip()
    if not summary:
        raise HTTPException(status_code=400, detail="summary is required")
    with _db_session(_require_db()) as c:
        ensure_resume_schema(c)
        item = upsert_resume_project_description(
            c,
            project_id=id,
            summary=summary,
            variant_name="portfolio_showcase",
            metadata={"source": "custom"},
        )

    log_event("INFO", f"Portfolio updated · Project: {id}")
    return {"data": item.to_dict(), "error": None}
