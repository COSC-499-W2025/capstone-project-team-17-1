from __future__ import annotations

import base64
import json as _json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse, Response

from capstone.portfolio_retrieval import _db_session
from capstone.resume_pdf_builder import build_pdf_with_latex
from capstone.resume_retrieval import build_resume_project_item
import capstone.storage as storage


# ---------------------------------------------------------------------------
# Helpers — convert new resume structure to formats expected by PDF builder
# ---------------------------------------------------------------------------

def _resume_to_pdf_payload(resume: dict) -> dict:
    """
    Map fetch_resume() output → dict accepted by build_pdf_with_latex / _extract_template_fields.
    - Renames section 'key' → 'name', normalising singular→plural where the PDF builder expects it
    - Hoists header metadata to top-level fields
    - Adds 'dateRange' to each item from start_date / end_date
    """
    # PDF builder expects plural section names for these
    _KEY_MAP = {
        "project": "projects",
        "certification": "certifications",
        "award": "awards",
    }

    def _item_for_pdf(item: dict) -> dict:
        """Add dateRange field and keep everything else as-is."""
        out = dict(item)
        start = item.get("start_date") or ""
        end = item.get("end_date") or ""
        if start or end:
            out["dateRange"] = " - ".join(filter(None, [start, end]))
        return out

    payload: dict = {
        "title": resume.get("title", ""),
        "target_role": resume.get("target_role", ""),
        "sections": [],
    }
    for sec in resume.get("sections") or []:
        key = sec.get("key", "")
        items = [_item_for_pdf(i) for i in (sec.get("items") or [])]
        # Hoist header metadata to top-level fields PDF builder expects
        if key == "header" and items:
            meta = items[0].get("metadata") or {}
            payload.setdefault("fullName", meta.get("full_name", ""))
            payload.setdefault("email", meta.get("email", ""))
            payload.setdefault("phone", meta.get("phone", ""))
            payload.setdefault("location", meta.get("location", ""))
            payload.setdefault("github", meta.get("github_url", ""))
            payload.setdefault("portfolio", meta.get("portfolio_url", ""))
        section_name = _KEY_MAP.get(key, key)
        payload["sections"].append({"name": section_name, "items": items})
    return payload


def _resume_to_markdown(resume: dict) -> str:
    """Convert fetch_resume() output to a simple Markdown string."""
    lines = [f"# {resume.get('title', 'Resume')}"]
    if resume.get("target_role"):
        lines.append(f"**Target Role:** {resume['target_role']}")
    lines.append("")
    for sec in resume.get("sections") or []:
        if not sec.get("is_enabled", True):
            continue
        items = [i for i in (sec.get("items") or []) if i.get("is_enabled", True)]
        if not items:
            continue
        lines.append(f"## {sec.get('label', sec.get('key', ''))}")
        for item in items:
            title = item.get("title") or ""
            subtitle = item.get("subtitle") or ""
            dates = " – ".join(
                filter(None, [item.get("start_date"), item.get("end_date")])
            )
            header_parts = filter(None, [title, subtitle, dates])
            lines.append(f"**{', '.join(header_parts)}**" if title else "")
            if item.get("content"):
                lines.append(item["content"])
            for bullet in item.get("bullets") or []:
                if bullet:
                    lines.append(f"- {bullet}")
            lines.append("")
    return "\n".join(lines).strip()

router = APIRouter(prefix="/resumes", tags=["resumes"])

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


def _require_db() -> Optional[str]:
    return _DB_DIR


async def _get_payload(request: Request) -> dict:
    try:
        return await request.json()
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Resumes collection
# ---------------------------------------------------------------------------

def _get_session_contributor_id(request: Request) -> Optional[int]:
    """Resolve contributor_id from Bearer token via auth sessions."""
    from capstone.api.routes.auth import _SESSIONS, _extract_bearer
    token = _extract_bearer(request)
    if not token or token not in _SESSIONS:
        return None
    return _SESSIONS[token].get("contributor_id")


@router.get("")
def list_resumes(request: Request, user_id: Optional[int] = None):
    _check_auth(request)
    # Prefer resolving user_id from session; fall back to explicit query param
    resolved_id = _get_session_contributor_id(request) or user_id
    if not resolved_id:
        raise HTTPException(status_code=400, detail="user_id is required (or login to auto-resolve)")
    with _db_session(_require_db()) as conn:
        resumes = storage.fetch_resumes(conn, resolved_id)
    return {"data": resumes, "meta": {"total": len(resumes)}, "error": None}


@router.post("")
async def create_resume(request: Request):
    _check_auth(request)
    payload = await _get_payload(request)
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    title = str(payload.get("title") or "Default Resume").strip()
    target_role = payload.get("target_role")
    with _db_session(_require_db()) as conn:
        resume_id = storage.insert_resume(conn, int(user_id), title, target_role)
        resume = storage.fetch_resume(conn, resume_id)
    return JSONResponse({"data": resume, "error": None}, status_code=201)


# ---------------------------------------------------------------------------
# render-pdf — MUST be registered before /{resume_id} to avoid routing conflict
# ---------------------------------------------------------------------------

@router.post("/render-pdf")
async def render_pdf(request: Request):
    """Render a resume dict (new format) directly to PDF and return base64-encoded bytes."""
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
            raise HTTPException(status_code=500, detail=f"PDF render failed: {exc}")
        encoded = base64.b64encode(out_path.read_bytes()).decode("ascii")
    return {"data": {"format": "pdf", "payload": encoded}, "error": None}


@router.post("/generate")
async def generate_resume(request: Request):
    """Auto-generate (or refresh) a resume for a user from all their linked projects.

    Request body:
      { "user_id": <int>, "create_new": <bool, default false>, "resume_title": <str, optional> }

    Aggregates skills and project summaries from every project snapshot linked to the
    user, then calls upsert_default_resume_modules to persist the result.
    Returns the full nested resume object.
    """
    _check_auth(request)
    payload = await _get_payload(request)

    # owner_id: who the resume belongs to — always the logged-in user
    owner_id = _get_session_contributor_id(request)
    if not owner_id:
        raise HTTPException(status_code=400, detail="user_id is required (or login to auto-resolve)")
    owner_id = int(owner_id)

    # data_user_id: whose project data / skills / profile to aggregate
    # defaults to owner (generating for yourself), can be overridden for collaborative projects
    data_user_id = payload.get("user_id")
    data_user_id = int(data_user_id) if data_user_id else owner_id

    create_new = bool(payload.get("create_new", False))
    resume_title = payload.get("resume_title") or None
    selected_project_ids = payload.get("project_ids") or None

    with _db_session(_require_db()) as conn:
        from capstone.api.routes.auth import _SESSIONS, _extract_bearer, _save_sessions

        auth_token = _extract_bearer(request)
        auth_user = (_SESSIONS.get(auth_token) or {}).get("user") or {} if auth_token else {}

        # Contributor ids can go stale if the local users table was rebuilt or reset.
        # Recreate the local user from the current auth profile before inserting rows
        # that reference users.id.
        owner_profile = storage.get_user_profile(conn, owner_id)
        if not owner_profile and auth_user:
            auth_username = (auth_user.get("username") or "").strip()
            github_url = (auth_user.get("github_url") or "").strip()
            github_handle = github_url.rstrip("/").split("/")[-1].strip() if github_url else ""
            identity = github_handle or auth_username
            if identity:
                owner_id = storage.upsert_user(
                    conn,
                    identity,
                    email=(auth_user.get("email") or "").strip() or None,
                )
                owner_profile = storage.get_user_profile(conn, owner_id)
                if auth_token and auth_token in _SESSIONS:
                    _SESSIONS[auth_token]["contributor_id"] = owner_id
                    _save_sessions()
        if not owner_profile:
            raise HTTPException(status_code=404, detail=f"Local user {owner_id} was not found")

        # --- default title: auth_username_yyyymmddhhmmss (guestuser if not logged in) ---
        if not resume_title:
            username = auth_user.get("username") or "guestuser"
            resume_title = f"{username}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # --- collect projects: use selected list if provided, else all linked to data_user_id ---
        if selected_project_ids:
            project_ids = [str(p) for p in selected_project_ids]
        else:
            rows = conn.execute(
                "SELECT project_id FROM user_projects WHERE user_id = ?",
                (data_user_id,),
            ).fetchall()
            project_ids = [r[0] for r in rows]

        # --- aggregate skills and project summaries ---
        seen_skills: set[str] = set()
        skill_names: list[str] = []
        project_items: list[dict] = []

        def _add_skill(name: str) -> None:
            key = name.strip().lower()
            if key and key not in seen_skills:
                seen_skills.add(key)
                skill_names.append(name.strip())

        for pid in project_ids:
            snap = storage.fetch_latest_snapshot(conn, pid)
            if not snap:
                continue
            langs = snap.get("languages") or {}
            if isinstance(langs, dict):
                for lang in langs:
                    _add_skill(lang)
            for fw in (snap.get("frameworks") or []):
                if fw:
                    _add_skill(str(fw))
            raw_skills = snap.get("skills") or []
            if isinstance(raw_skills, list):
                for item in raw_skills:
                    if isinstance(item, dict):
                        _add_skill(str(item.get("skill") or item.get("name") or ""))
                    elif item:
                        _add_skill(str(item))
            elif isinstance(raw_skills, dict):
                for name in raw_skills:
                    _add_skill(name)
            item = build_resume_project_item(pid, snap)
            if not item.get("title"):
                item["title"] = snap.get("project_name") or snap.get("root_name") or pid
            project_items.append(item)

        # --- build header ---
        # Auth profile is only used when generating for the logged-in user themselves.
        # When generating for another contributor, use only their local profile.
        is_self = (data_user_id == owner_id)

        # Header data: use auth profile for self, local git profile for others
        local_profile = storage.get_user_profile(conn, data_user_id) or {}

        def _pick(auth_key: str, local_key: Optional[str] = None) -> str:
            local_val = (local_profile.get(local_key or auth_key) or "").strip()
            if not is_self:
                return local_val
            return (auth_user.get(auth_key) or "").strip() or local_val

        city = _pick("city")
        state = _pick("state_region")
        location = ", ".join(p for p in [city, state] if p)
        if is_self:
            username = auth_user.get("username") or local_profile.get("username") or str(owner_id)
        else:
            username = local_profile.get("username") or str(data_user_id)
        header = {
            "full_name": _pick("full_name") or username,
            "email": _pick("email"),
            "phone": _pick("phone_number"),
            "location": location,
            "github_url": _pick("github_url"),
            "portfolio_url": _pick("portfolio_url"),
        }

        # Resume always owned by the logged-in user (owner_id),
        # regardless of whose data was used to generate it.
        resume_id = storage.upsert_default_resume_modules(
            conn,
            user_id=owner_id,
            header=header,
            core_skills=skill_names,
            projects=project_items,
            resume_title=resume_title,
            create_new=create_new,
        )
        resume = storage.fetch_resume(conn, resume_id)

    return JSONResponse({"data": resume, "error": None}, status_code=201)


# ---------------------------------------------------------------------------
# Single resume
# ---------------------------------------------------------------------------

@router.get("/{resume_id}")
def get_resume(resume_id: str, request: Request):
    _check_auth(request)
    with _db_session(_require_db()) as conn:
        resume = storage.fetch_resume(conn, resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    return {"data": resume, "error": None}


@router.patch("/{resume_id}")
async def update_resume(resume_id: str, request: Request):
    _check_auth(request)
    payload = await _get_payload(request)
    with _db_session(_require_db()) as conn:
        found = storage.update_resume(
            conn,
            resume_id,
            title=payload.get("title"),
            target_role=payload.get("target_role"),
            status=payload.get("status"),
        )
        if not found:
            raise HTTPException(status_code=404, detail="Resume not found")
        resume = storage.fetch_resume(conn, resume_id)
    return {"data": resume, "error": None}


@router.delete("/{resume_id}")
def delete_resume(resume_id: str, request: Request):
    _check_auth(request)
    with _db_session(_require_db()) as conn:
        ok = storage.delete_resume(conn, resume_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Resume not found")
    return {"data": {"deleted": True, "id": resume_id}, "error": None}


@router.get("/{resume_id}/export")
def export_resume(resume_id: str, request: Request, format: str = "json"):
    """Export a resume as JSON, Markdown, or PDF (base64)."""
    _check_auth(request)
    fmt = format.lower()
    if fmt not in {"json", "markdown", "pdf"}:
        raise HTTPException(status_code=400, detail="format must be json, markdown, or pdf")
    with _db_session(_require_db()) as conn:
        resume = storage.fetch_resume(conn, resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    if fmt == "json":
        return {"data": resume, "error": None}
    if fmt == "markdown":
        return PlainTextResponse(_resume_to_markdown(resume))
    # pdf — return binary stream so Postman / browsers can open it directly
    pdf_payload = _resume_to_pdf_payload(resume)
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "resume.pdf"
        try:
            build_pdf_with_latex(pdf_payload, out_path)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"PDF render failed: {exc}")
        pdf_bytes = out_path.read_bytes()
    title_slug = (resume.get("title") or "resume").replace(" ", "_")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{title_slug}.pdf"'},
    )


# ---------------------------------------------------------------------------
# Sections — reorder MUST be registered before /{section_id}
# ---------------------------------------------------------------------------

@router.get("/{resume_id}/sections")
def list_sections(resume_id: str, request: Request):
    _check_auth(request)
    with _db_session(_require_db()) as conn:
        if not storage.fetch_resume(conn, resume_id):
            raise HTTPException(status_code=404, detail="Resume not found")
        sections = storage.fetch_resume_sections(conn, resume_id)
    return {"data": sections, "meta": {"total": len(sections)}, "error": None}


@router.post("/{resume_id}/sections/reorder")
async def reorder_sections(resume_id: str, request: Request):
    _check_auth(request)
    payload = await _get_payload(request)
    ids = payload.get("ids")
    if not isinstance(ids, list):
        raise HTTPException(status_code=400, detail="ids must be a list")
    with _db_session(_require_db()) as conn:
        if not storage.fetch_resume(conn, resume_id):
            raise HTTPException(status_code=404, detail="Resume not found")
        sections = storage.reorder_resume_sections(conn, resume_id, ids)
    return {"data": sections, "error": None}


@router.post("/{resume_id}/sections")
async def create_section(resume_id: str, request: Request):
    _check_auth(request)
    payload = await _get_payload(request)
    key = str(payload.get("key") or "").strip()
    label = str(payload.get("label") or "").strip()
    if not key:
        raise HTTPException(status_code=400, detail="key is required")
    if not label:
        raise HTTPException(status_code=400, detail="label is required")
    is_custom = bool(payload.get("is_custom", True))
    sort_order = payload.get("sort_order")
    with _db_session(_require_db()) as conn:
        if not storage.fetch_resume(conn, resume_id):
            raise HTTPException(status_code=404, detail="Resume not found")
        section_id = storage.insert_resume_section(
            conn, resume_id, key, label,
            is_custom=is_custom,
            sort_order=int(sort_order) if sort_order is not None else None,
        )
        sections = storage.fetch_resume_sections(conn, resume_id)
        section = next((s for s in sections if s["id"] == section_id), None)
    return JSONResponse({"data": section, "error": None}, status_code=201)


@router.patch("/{resume_id}/sections/{section_id}")
async def update_section(resume_id: str, section_id: str, request: Request):
    _check_auth(request)
    payload = await _get_payload(request)
    is_enabled = payload.get("is_enabled")
    sort_order = payload.get("sort_order")
    with _db_session(_require_db()) as conn:
        found = storage.update_resume_section(
            conn,
            section_id,
            label=payload.get("label"),
            is_enabled=bool(is_enabled) if is_enabled is not None else None,
            sort_order=int(sort_order) if sort_order is not None else None,
        )
        if not found:
            raise HTTPException(status_code=404, detail="Section not found")
        sections = storage.fetch_resume_sections(conn, resume_id)
        section = next((s for s in sections if s["id"] == section_id), None)
    return {"data": section, "error": None}


@router.delete("/{resume_id}/sections/{section_id}")
def delete_section(resume_id: str, section_id: str, request: Request):
    _check_auth(request)
    with _db_session(_require_db()) as conn:
        ok = storage.delete_resume_section(conn, section_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Section not found")
    return {"data": {"deleted": True, "id": section_id}, "error": None}


# ---------------------------------------------------------------------------
# Items — reorder MUST be registered before /{item_id}
# ---------------------------------------------------------------------------

@router.get("/{resume_id}/sections/{section_id}/items")
def list_items(resume_id: str, section_id: str, request: Request):
    _check_auth(request)
    with _db_session(_require_db()) as conn:
        items = storage.fetch_resume_items(conn, section_id)
    return {"data": items, "meta": {"total": len(items)}, "error": None}


@router.post("/{resume_id}/sections/{section_id}/items/reorder")
async def reorder_items(resume_id: str, section_id: str, request: Request):
    _check_auth(request)
    payload = await _get_payload(request)
    ids = payload.get("ids")
    if not isinstance(ids, list):
        raise HTTPException(status_code=400, detail="ids must be a list")
    with _db_session(_require_db()) as conn:
        items = storage.reorder_resume_items(conn, section_id, ids)
    return {"data": items, "error": None}


@router.post("/{resume_id}/sections/{section_id}/items")
async def create_item(resume_id: str, section_id: str, request: Request):
    _check_auth(request)
    payload = await _get_payload(request)
    sort_order = payload.get("sort_order")
    bullets = payload.get("bullets")
    metadata = payload.get("metadata")
    if bullets is not None and not isinstance(bullets, list):
        raise HTTPException(status_code=400, detail="bullets must be a list")
    if metadata is not None and not isinstance(metadata, dict):
        raise HTTPException(status_code=400, detail="metadata must be an object")
    with _db_session(_require_db()) as conn:
        item_id = storage.insert_resume_item(
            conn,
            section_id,
            title=payload.get("title"),
            subtitle=payload.get("subtitle"),
            start_date=payload.get("start_date"),
            end_date=payload.get("end_date"),
            location=payload.get("location"),
            content=payload.get("content"),
            bullets=bullets,
            metadata=metadata,
            sort_order=int(sort_order) if sort_order is not None else None,
        )
        items = storage.fetch_resume_items(conn, section_id)
        item = next((i for i in items if i["id"] == item_id), None)
    return JSONResponse({"data": item, "error": None}, status_code=201)


@router.patch("/{resume_id}/sections/{section_id}/items/{item_id}")
async def update_item(resume_id: str, section_id: str, item_id: str, request: Request):
    _check_auth(request)
    payload = await _get_payload(request)
    bullets = payload.get("bullets")
    metadata = payload.get("metadata")
    is_enabled = payload.get("is_enabled")
    if bullets is not None and not isinstance(bullets, list):
        raise HTTPException(status_code=400, detail="bullets must be a list")
    if metadata is not None and not isinstance(metadata, dict):
        raise HTTPException(status_code=400, detail="metadata must be an object")
    with _db_session(_require_db()) as conn:
        found = storage.update_resume_item(
            conn,
            item_id,
            title=payload.get("title"),
            subtitle=payload.get("subtitle"),
            start_date=payload.get("start_date"),
            end_date=payload.get("end_date"),
            location=payload.get("location"),
            content=payload.get("content"),
            bullets=bullets,
            metadata=metadata,
            is_enabled=bool(is_enabled) if is_enabled is not None else None,
        )
        if not found:
            raise HTTPException(status_code=404, detail="Item not found")
        items = storage.fetch_resume_items(conn, section_id)
        item = next((i for i in items if i["id"] == item_id), None)
    return {"data": item, "error": None}


@router.delete("/{resume_id}/sections/{section_id}/items/{item_id}")
def delete_item(resume_id: str, section_id: str, item_id: str, request: Request):
    _check_auth(request)
    with _db_session(_require_db()) as conn:
        ok = storage.delete_resume_item(conn, item_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"data": {"deleted": True, "id": item_id}, "error": None}
