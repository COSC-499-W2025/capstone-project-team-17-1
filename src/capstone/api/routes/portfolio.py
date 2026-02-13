from __future__ import annotations

import json
from typing import List, Optional
from datetime import datetime, UTC

from fastapi import APIRouter, HTTPException, Request, Response
from enum import Enum
from fastapi.responses import JSONResponse, PlainTextResponse

from capstone.portfolio_retrieval import _db_session, _extract_evidence, _parse_view
from capstone.project_insight import infer_user_role
from capstone.resume_retrieval import (
    build_resume_project_summary,
    ensure_resume_schema,
    get_resume_project_description,
    upsert_resume_project_description,
)
from capstone.storage import fetch_latest_snapshot, fetch_latest_snapshots
from capstone.top_project_summaries import generate_top_project_summaries, export_markdown

from capstone.api.portfolio_helpers import ensure_indexes, list_snapshots


router = APIRouter(tags=["portfolio", "resume", "users"])

# align naming used in handlers
get_latest_snapshot = fetch_latest_snapshot

_DB_DIR: Optional[str] = None
_TOKEN: Optional[str] = None


class ExportFormat(str, Enum):
    json = "json"
    markdown = "markdown"
    pdf = "pdf"


def configure(db_dir: Optional[str], auth_token: Optional[str]) -> None:
    global _DB_DIR, _TOKEN
    _DB_DIR = db_dir
    _TOKEN = auth_token


def _check_auth(request: Request) -> None:
    token = getattr(request.app.state, "auth_token", _TOKEN)
    if not token:
        return
    h = request.headers.get("Authorization", "")
    if not (h.startswith("Bearer ") and h.split(" ", 1)[1] == token):
        raise HTTPException(status_code=401, detail="Missing or invalid token")


def _demo_enabled(request: Request | None = None) -> bool:
    token = getattr(request.app.state, "auth_token", _TOKEN) if request else _TOKEN
    return token is None


def _build_demo_portfolio(portfolio_id: str, owner: Optional[str], project_ids: list[str] | None = None, projects: list[dict] | None = None) -> dict:
    if projects is None:
        projects = [{"project_id": pid, "title": f"Project_{pid}"} for pid in (project_ids or [])]
    return {
        "id": portfolio_id,
        "owner": owner,
        "projects": projects,
    }


async def _get_payload(request: Request) -> dict:
    try:
        return await request.json()
    except Exception:
        return {}


@router.get("/users")
def list_users(request: Request):
    _check_auth(request)
    with _db_session(_DB_DIR) as c:
        rows = c.execute(
            "SELECT DISTINCT contributor FROM contributor_stats ORDER BY LOWER(contributor)"
        ).fetchall()
    users = [r[0] for r in rows if r and r[0] and "[bot]" not in r[0].lower()]
    return {"data": users, "error": None}


@router.get("/users/{user}/projects")
def list_user_projects(user: str, request: Request):
    _check_auth(request)
    with _db_session(_DB_DIR) as c:
        rows = c.execute(
            "SELECT DISTINCT project_id FROM contributor_stats WHERE contributor = ? ORDER BY project_id",
            (user,),
        ).fetchall()
    projects = [r[0] for r in rows if r and r[0]]
    return {"data": projects, "error": None}


@router.get("/portfolio/summary")
def portfolio_summary(user: str, request: Request, limit: int = 3):
    _check_auth(request)
    with _db_session(_DB_DIR) as c:
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
    if view == "resume":
        with _db_session(_DB_DIR) as c:
            ensure_resume_schema(c)
            item = get_resume_project_description(c, projectId)
        if not item:
            raise HTTPException(status_code=404, detail="No resume project found")
        meta = {"projectId": projectId, "view": "resume"}
        if user:
            # Include role in response metadata
            with _db_session(_DB_DIR) as c:
                snap = get_latest_snapshot(c, projectId)
            if snap:
                meta["userRole"] = infer_user_role(snap, user)
        return {"data": item.to_dict(), "meta": meta, "error": None}

    with _db_session(_DB_DIR) as c:
        ensure_indexes(c)
        data = get_latest_snapshot(c, projectId)
    if data is None:
        raise HTTPException(status_code=404, detail="No snapshots found")
    meta = {"projectId": projectId, "view": "portfolio"}
    if user:
        # Inline role in showcase payload
        meta["userRole"] = infer_user_role(data, user)
    return {"data": data, "meta": meta, "error": None}


@router.get("/portfolios/evidence")
def evidence_latest(request: Request, projectId: str):
    _check_auth(request)
    with _db_session(_DB_DIR) as c:
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
    with _db_session(_DB_DIR) as c:
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


@router.get("/portfolio/{project_id}")
def get_portfolio_showcase(project_id: str, request: Request, user: Optional[str] = None):
    if _demo_enabled(request):
        if project_id != "demo":
            raise HTTPException(status_code=404, detail="Portfolio not found")
        return {"portfolio": _build_demo_portfolio("demo", owner="user123", projects=[])}
    _check_auth(request)
    with _db_session(_DB_DIR) as c:
        ensure_resume_schema(c)
        item = get_resume_project_description(c, project_id, variant_name="portfolio_showcase")
        snap = get_latest_snapshot(c, project_id)
        if item:
            payload = item.to_dict()
            if user and snap:
                # Enrich saved showcase with user role
                payload["user_role"] = infer_user_role(snap, user)
            return {"data": payload, "error": None}
    if not snap:
        raise HTTPException(status_code=404, detail="No snapshots found")
    summary = build_resume_project_summary(project_id, snap)
    payload = {"project_id": project_id, "summary": summary}
    if user:
        # Enrich auto summary with role
        payload["user_role"] = infer_user_role(snap, user)
    return {"data": payload, "error": None}


@router.get("/portfolio/showcase")
def get_portfolio_showcase_query(request: Request, projectId: str):
    return get_portfolio_showcase(projectId, request)


@router.post("/portfolio/generate")
async def generate_portfolio_showcase(request: Request):
    if _demo_enabled(request):
        payload = await _get_payload(request)
        project_ids = payload.get("project_ids") or []
        if not isinstance(project_ids, list):
            raise HTTPException(status_code=422, detail="project_ids must be a list")
        portfolio = _build_demo_portfolio("portfolio_001", owner=payload.get("owner"), project_ids=project_ids)
        return {"portfolio": portfolio}
    _check_auth(request)
    payload = await _get_payload(request)
    project_ids = payload.get("projectIds") or []
    if not project_ids or not isinstance(project_ids, list):
        raise HTTPException(status_code=400, detail="projectIds must be a list")
    results = []
    with _db_session(_DB_DIR) as c:
        ensure_resume_schema(c)
        for pid in project_ids:
            snap = get_latest_snapshot(c, str(pid))
            if not snap:
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


@router.post("/portfolio/{project_id}/edit")
async def edit_portfolio_showcase(project_id: str, request: Request):
    if _demo_enabled(request):
        if project_id != "demo":
            raise HTTPException(status_code=404, detail="Portfolio not found")
        payload = await _get_payload(request)
        return {"portfolio": _build_demo_portfolio("demo", owner="user123", projects=payload.get("projects") or [])}
    _check_auth(request)
    payload = await _get_payload(request)
    summary = (payload.get("summary") or "").strip()
    if not summary:
        raise HTTPException(status_code=400, detail="summary is required")
    with _db_session(_DB_DIR) as c:
        ensure_resume_schema(c)
        item = upsert_resume_project_description(
            c,
            project_id=project_id,
            summary=summary,
            variant_name="portfolio_showcase",
            metadata={"source": "custom"},
        )
    return {"data": item.to_dict(), "error": None}


@router.get("/portfolio/{portfolio_id}/export")
def export_portfolio(portfolio_id: str, request: Request, format: ExportFormat = ExportFormat.json):
    if _demo_enabled(request):
        if portfolio_id != "demo":
            raise HTTPException(status_code=404, detail="Portfolio not found")
        if format == ExportFormat.json:
            return {"portfolio_id": portfolio_id, "exported_at": datetime.now(UTC).isoformat()}
        if format == ExportFormat.markdown:
            return {"content": "# Portfolio\n\nGenerated portfolio content here"}
        if format == ExportFormat.pdf:
            pdf_bytes = (
                b"%PDF-1.4\n"
                b"1 0 obj<<>>\n"
                b"trailer<<>>\n"
                b"%%EOF"
            )
            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={"Content-Disposition": f'attachment; filename="portfolio_{portfolio_id}.pdf"'},
            )
    raise HTTPException(status_code=404, detail="Not found")
