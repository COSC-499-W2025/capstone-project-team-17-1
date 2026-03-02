from __future__ import annotations

import base64
import json
import tempfile
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from capstone.activity_log import log_event
from capstone.portfolio_retrieval import _db_session
from capstone.resume_pdf_builder import build_pdf_with_latex
from capstone.resume_retrieval import (
    build_resume_preview,
    ensure_resume_schema,
    export_resume,
    get_resume_entry,
    get_resume_project_description,
    insert_resume_entry,
    list_resume_project_descriptions,
    query_resume_entries,
    update_resume_entry,
    generate_resume_project_descriptions,
    upsert_resume_project_description,
)
from capstone.storage import fetch_latest_snapshot, fetch_latest_snapshots_for_projects

router = APIRouter(tags=["resume"])

_DB_DIR: Optional[str] = None
_TOKEN: Optional[str] = None

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

async def _get_payload(request: Request) -> dict:
    try:
        return await request.json()
    except Exception:
        return {}


@router.post("/resume/render-pdf")
async def resume_render_pdf(request: Request):
    _check_auth(request)
    payload = await _get_payload(request)
    resume_payload = payload.get("resume")
    if not isinstance(resume_payload, dict):
        raise HTTPException(status_code=400, detail="resume object is required")

    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "resume.pdf"
        try:
            build_pdf_with_latex(resume_payload, out_path)
        except Exception as exc:
            log_event("ERROR", f"Resume PDF render failed · {exc}")
            raise HTTPException(status_code=500, detail=f"PDF render failed: {exc}")
        encoded = base64.b64encode(out_path.read_bytes()).decode("ascii")
        log_event("SUCCESS", "Resume PDF rendered successfully")
    return {"data": {"format": "pdf", "payload": encoded}, "error": None}

@router.get("/resume")
def resume_list(
    request: Request,
    format: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    section: Optional[List[str]] = None,
    keyword: Optional[List[str]] = None,
    startDate: Optional[str] = None,
    endDate: Optional[str] = None,
    includeOutdated: Optional[bool] = False,
):
    _check_auth(request)
    fmt = (format or "").lower()
    with _db_session(_DB_DIR) as c:
        ensure_resume_schema(c)
        result = query_resume_entries(
            c,
            sections=section or None,
            keywords=keyword or None,
            start_date=startDate,
            end_date=endDate,
            include_outdated=bool(includeOutdated),
            limit=limit,
            offset=offset,
        )
        if fmt == "preview":
            preview = build_resume_preview(result, conn=c)
            return JSONResponse({"data": preview, "error": None})
        items = [entry.to_dict() for entry in result.entries]
    if fmt == "markdown":
        payload = "\n\n".join([export_markdown(item) for item in items])
        return PlainTextResponse(payload)
    return JSONResponse(
        {
            "data": items,
            "meta": {"warnings": result.warnings, "missingSections": result.missing_sections},
            "error": None,
        }
    )


@router.post("/resume")
async def resume_insert(request: Request):
    _check_auth(request)
    payload = await _get_payload(request)
    section = (payload.get("section") or "projects").strip()
    title = (payload.get("title") or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="title is required")
    with _db_session(_DB_DIR) as c:
        ensure_resume_schema(c)
        entry_id = insert_resume_entry(
            c,
            section=section,
            title=title,
            summary=payload.get("summary"),
            body=payload.get("body"),
            skills=payload.get("skills"),
            projects=payload.get("projects"),
            status=payload.get("status"),
            metadata=payload.get("metadata"),
        )
        entry = get_resume_entry(c, entry_id)
        log_event("SUCCESS", f"Resume entry created · ID: {entry_id} · Section: {section}")
    return JSONResponse({"data": entry.to_dict(), "error": None}, status_code=200)


@router.get("/resume/{entry_id}")
def resume_get(entry_id: str, request: Request):
    _check_auth(request)
    with _db_session(_DB_DIR) as c:
        ensure_resume_schema(c)
        entry = get_resume_entry(c, entry_id)
    if not entry:
        log_event("ERROR", f"Resume Not found · ID: {entry_id}")
        raise HTTPException(status_code=404, detail="Resume entry not found")
    return {"data": entry.to_dict(), "error": None}


@router.patch("/resume/{entry_id}")
async def resume_update(entry_id: str, request: Request):
    _check_auth(request)
    payload = await _get_payload(request)
    with _db_session(_DB_DIR) as c:
        ensure_resume_schema(c)
        entry = update_resume_entry(
            c,
            entry_id=entry_id,
            summary=payload.get("summary"),
            _summary_provided="summary" in payload,
            body=payload.get("body"),
            skills=payload.get("skills"),
            projects=payload.get("projects"),
            section=payload.get("section"),
            status=payload.get("status"),
            metadata=payload.get("metadata"),
        )
    if not entry:
        log_event("ERROR", f"Resume update failed · Not found · ID: {entry_id}")
        raise HTTPException(status_code=404, detail="Resume entry not found")
    log_event("SUCCESS", f"Resume entry updated · ID: {entry_id}")
    return {"data": entry.to_dict(), "error": None}


@router.post("/resume/{entry_id}/edit")
async def resume_update_alias(entry_id: str, request: Request):
    """
    Alias for PATCH /resume/{id} to satisfy API consumers expecting POST.
    """
    # Delegate to the main update handler
    return await resume_update(entry_id, request)


@router.delete("/resume/{entry_id}")
def resume_delete(entry_id: str, request: Request):
    _check_auth(request)
    with _db_session(_DB_DIR) as c:
        ensure_resume_schema(c)
        ok = delete_resume_entry(c, entry_id)
    if not ok:
        log_event("ERROR", f"Resume delete failed · Not found · ID: {entry_id}")
        raise HTTPException(status_code=404, detail="Resume entry not found")
    log_event("WARNING", f"Resume entry deleted · ID: {entry_id}")
    return {"data": {"deleted": True, "id": entry_id}, "error": None}


@router.post("/resume/generate")
async def resume_generate(request: Request):
    _check_auth(request)
    payload = await _get_payload(request)
    fmt = str(payload.get("format", "json")).lower()
    if fmt not in {"json", "markdown", "pdf"}:
        raise HTTPException(status_code=400, detail="format must be json, markdown, or pdf")

    def _normalise_list(value: object) -> List[str] | None:
        if value is None:
            return None
        if isinstance(value, list):
            return [str(item) for item in value]
        return [str(value)]

    with _db_session(_DB_DIR) as c:
        ensure_resume_schema(c)
        result = query_resume_entries(
            c,
            sections=_normalise_list(payload.get("sections")),
            keywords=_normalise_list(payload.get("keywords")),
            start_date=payload.get("startDate"),
            end_date=payload.get("endDate"),
            include_outdated=bool(payload.get("includeOutdated", False)),
            limit=int(payload.get("limit", 100)),
            offset=int(payload.get("offset", 0)),
        )
        if not result.entries:
            log_event("ERROR", "Resume generation failed · No entries found")
            raise HTTPException(status_code=404, detail="No resume entries found")
        project_ids = sorted({pid for entry in result.entries for pid in entry.project_ids})
        description_map = {}
        if project_ids:
            descriptions = list_resume_project_descriptions(
                c,
                project_ids=project_ids,
                active_only=True,
                limit=len(project_ids),
            )
            description_map = {item.project_id: item for item in descriptions}
        data = export_resume(result.entries, fmt=fmt, project_descriptions=description_map)
    if fmt == "pdf":
        import base64

        encoded = base64.b64encode(data).decode("ascii")
        return {"data": {"format": "pdf", "payload": encoded}, "error": None}
    if fmt == "markdown":
        return {"data": {"format": "markdown", "payload": data.decode("utf-8")}, "error": None}
    log_event("SUCCESS", f"Resume generated · Format: {fmt} · Entries: {len(result.entries)}")
    return {"data": {"format": "json", "payload": json.loads(data.decode("utf-8"))}, "error": None}


@router.get("/resume-projects")
def resume_projects_get(request: Request):
    _check_auth(request)
    q = request.query_params
    project_ids = q.getlist("projectId")
    variant_name = q.get("variantName")
    audience = q.get("audience")
    active_only = q.get("activeOnly") == "true"
    limit = int(q.get("limit", 100))
    offset = int(q.get("offset", 0))

    with _db_session(_DB_DIR) as c:
        ensure_resume_schema(c)
        if project_ids and len(project_ids) == 1 and q.get("list") != "true":
            item = get_resume_project_description(
                c,
                project_ids[0],
                variant_name=variant_name,
                audience=audience,
                active_only=not q.get("includeInactive") == "true",
            )
            if not item:
                log_event("ERROR", f"Resume project description failed · Project not found · {item.project_id}")
                raise HTTPException(status_code=404, detail="No resume project found")
            return {"data": item.to_dict(), "error": None}

        items = list_resume_project_descriptions(
            c,
            project_ids=project_ids or None,
            active_only=active_only,
            limit=limit,
            offset=offset,
        )

    payload = [item.to_dict() for item in items]
    log_event("SUCCESS", f"Resume project description updated · Project: {project_id}")
    return {"data": payload, "meta": {"limit": limit, "offset": offset, "total": len(payload)}, "error": None}


@router.post("/resume-projects")
async def resume_projects_post(request: Request):
    _check_auth(request)
    payload = await _get_payload(request)
    project_id = payload.get("projectId") or payload.get("project_id")
    summary = payload.get("summary")
    metadata = payload.get("metadata")
    variant_name = payload.get("variantName")
    audience = payload.get("audience")
    is_active = payload.get("isActive", True)
    if not project_id:
        raise HTTPException(status_code=400, detail="projectId is required")
    if not summary or not str(summary).strip():
        raise HTTPException(status_code=422, detail="summary is required")
    summary = str(summary).strip()
    if len(summary) > 400:
        raise HTTPException(status_code=422, detail="summary is too long")
    if metadata is not None and not isinstance(metadata, dict):
        raise HTTPException(status_code=400, detail="metadata must be an object")

    with _db_session(_DB_DIR) as c:
        ensure_resume_schema(c)
        if fetch_latest_snapshot(c, str(project_id)) is None:
            raise HTTPException(status_code=404, detail="Project not found")
        if metadata is None:
            metadata = {}
        metadata.setdefault("source", "custom")
        item = upsert_resume_project_description(
            c,
            project_id=str(project_id),
            summary=summary,
            variant_name=str(variant_name) if variant_name else None,
            audience=str(audience) if audience else None,
            is_active=bool(is_active),
            metadata=metadata if isinstance(metadata, dict) else None,
        )

    return JSONResponse({"data": item.to_dict(), "error": None}, status_code=201)


@router.post("/resume-projects/generate")
async def resume_projects_generate(request: Request):
    _check_auth(request)
    payload = await _get_payload(request)
    project_ids = payload.get("projectIds") or payload.get("project_ids") or payload.get("projectId")
    overwrite = bool(payload.get("overwrite", False))

    if isinstance(project_ids, str):
        project_ids = [project_ids]

    if not project_ids or not isinstance(project_ids, list):
        raise HTTPException(status_code=400, detail="projectIds is required")

    ids = [str(pid) for pid in project_ids]

    with _db_session(_DB_DIR) as c:
        ensure_resume_schema(c)
        latest_map = fetch_latest_snapshots_for_projects(c, ids)
        missing = [pid for pid, snap in latest_map.items() if snap is None]
        if missing:
            log_event("ERROR", f"Resume project generation failed · Missing projects")
            raise HTTPException(status_code=404, detail="Project not found")

        items = generate_resume_project_descriptions(
            c,
            project_ids=ids,
            overwrite=overwrite,
        )

    payload = [item.to_dict() for item in items]
    log_event("SUCCESS", f"Resume project descriptions generated · Projects: {len(ids)}")
    return {"data": payload, "meta": {"total": len(payload)}, "error": None}
