from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, HTTPException, Request
from capstone.activity_log import log_event

from capstone.portfolio_retrieval import _db_session, _extract_evidence, _parse_view
from capstone.storage import fetch_latest_snapshot, fetch_latest_snapshots
from capstone.top_project_summaries import generate_top_project_summaries, export_markdown

from capstone.api.portfolio_helpers import ensure_indexes, list_snapshots

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
            FROM contributors u
            INNER JOIN user_projects up ON u.id = up.user_id
            INNER JOIN project_analysis pa ON up.project_id = pa.project_id
            -- Exclude no-email users when another user WITH an email is
            -- already linked to at least one of the same projects.
            -- This removes git-fullname duplicates when the GitHub-login
            -- version (with real email) is also present.
            WHERE NOT (
                u.email IS NULL
                AND EXISTS (
                    SELECT 1 FROM contributors u2
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

from typing import Optional  # already there

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

