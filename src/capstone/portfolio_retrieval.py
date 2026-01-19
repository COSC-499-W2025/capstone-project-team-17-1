from __future__ import annotations

import os
import json
import sqlite3
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Tuple
from contextlib import contextmanager
from pathlib import Path

try:
    from .storage import (
        open_db as _open_db,
        close_db as _close_db,
        fetch_latest_snapshot as _fetch_latest_snapshot,
    )
except Exception: 
    _open_db = None
    _close_db = None
    _fetch_latest_snapshot = None

from .resume_retrieval import (
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

@contextmanager
def _db_session(db_dir: str | None):
    """
    Always close the SQLite handle (critical on Windows).
    Uses capstone.storage.open_db/close_db if available.
    """
    # Normalize to Path for storage.open_db()
    base_path = Path(db_dir) if db_dir else None

    if _open_db is not None:
        conn = _open_db(base_path)  # <— pass Path or None, not str
    else:
        # Fallback: local sqlite3 connection in a folder
        target = Path(db_dir) if db_dir else Path("data")
        target.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(target / "capstone.db")

    try:
        # Avoid WAL side files in tests on Windows
        try:
            conn.execute("PRAGMA journal_mode=DELETE;")
        except Exception:
            pass
        yield conn
    finally:
        # Ensure the cached/global handle is released
        try:
            if _close_db is not None:
                _close_db()
            else:
                conn.close()
        except Exception:
            pass


@dataclass(frozen=True)
class SnapshotRow:
    project_id: str
    classification: Optional[str]
    primary_contributor: Optional[str]
    snapshot: Dict[str, Any]
    created_at: str  # ISO string (stored as TEXT in SQLite)


# ---------- SQL helpers ----------

def ensure_indexes(conn: sqlite3.Connection) -> None:
    """
    Create the index that makes 'latest for project' and paginated reads fast.
    """
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_pa_project_created "
        "ON project_analysis(project_id, created_at DESC)"
    )
    conn.commit()


def _validate_sort(sort_field: str, sort_dir: str) -> Tuple[str, str]:
    sf = sort_field if sort_field in {"created_at", "classification"} else "created_at"
    sd = sort_dir.lower() if sort_dir.lower() in {"asc", "desc"} else "desc"
    return sf, sd


def list_snapshots(
    conn: sqlite3.Connection,
    project_id: str,
    page: int = 1,
    page_size: int = 20,
    sort_field: Literal["created_at", "classification"] = "created_at",
    sort_dir: Literal["asc", "desc"] = "desc",
    classification: Optional[str] = None,
    primary_contributor: Optional[str] = None,
) -> Tuple[List[SnapshotRow], int]:
    sort_field, sort_dir = _validate_sort(sort_field, sort_dir)
    page = max(1, int(page))
    page_size = max(1, min(200, int(page_size)))  # keep it sane
    offset = (page - 1) * page_size

    where = ["project_id = ?"]
    params: List[Any] = [project_id]
    if classification:
        where.append("classification = ?")
        params.append(classification)
    if primary_contributor:
        where.append("primary_contributor = ?")
        params.append(primary_contributor)
    where_sql = " AND ".join(where)

    total = conn.execute(
        f"SELECT COUNT(*) FROM project_analysis WHERE {where_sql}",
        params,
    ).fetchone()[0]

    rows = conn.execute(
        f"""
        SELECT project_id, classification, primary_contributor, snapshot, created_at
        FROM project_analysis
        WHERE {where_sql}
        ORDER BY {sort_field} {sort_dir}
        LIMIT ? OFFSET ?
        """,
        (*params, page_size, offset),
    ).fetchall()

    result = [
        SnapshotRow(
            project_id=r[0],
            classification=r[1],
            primary_contributor=r[2],
            snapshot=json.loads(r[3]),
            created_at=r[4],
        )
        for r in rows
    ]
    return result, int(total)


def get_latest_snapshot(conn: sqlite3.Connection, project_id: str) -> Optional[dict]:
    """
    Return the latest JSON snapshot for a project (dict) or None.
    Uses capstone.storage.fetch_latest_snapshot if available.
    """
    if _fetch_latest_snapshot is not None:
        return _fetch_latest_snapshot(conn, project_id)

    row = conn.execute(
        """
        SELECT snapshot
        FROM project_analysis
        WHERE project_id = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (project_id,),
    ).fetchone()
    return json.loads(row[0]) if row else None

def _extract_evidence(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract a simple evidence/metrics structure from a snapshot.
    Keeps it robust: handles different key shapes and provides a fallback.
    """
    if not isinstance(snapshot, dict):
        return {"type": "metrics", "items": []}

    # Common places teams store metrics/evidence
    candidates = [
        snapshot.get("evidence"),
        snapshot.get("metrics"),
        snapshot.get("results"),
        snapshot.get("evaluation"),
        snapshot.get("outcomes"),
    ]

    for c in candidates:
        # If already in desired shape
        if isinstance(c, dict) and "items" in c and isinstance(c["items"], list):
            return {"type": c.get("type", "metrics"), "items": c["items"]}

        # If it's a dict of key->value metrics
        if isinstance(c, dict):
            items = [{"label": str(k), "value": str(v)} for k, v in c.items()]
            if items:
                return {"type": "metrics", "items": items}

        # If it's a list, assume list of strings or dicts
        if isinstance(c, list):
            items = []
            for it in c:
                if isinstance(it, dict) and ("label" in it or "value" in it):
                    items.append({"label": str(it.get("label", "")), "value": str(it.get("value", ""))})
                else:
                    items.append({"label": "evidence", "value": str(it)})
            if items:
                return {"type": "metrics", "items": items}

    # Fallback evidence (still counts as “evidence of success/summary metrics”)
    items: List[Dict[str, str]] = []
    if isinstance(snapshot.get("skills"), list):
        items.append({"label": "Skills detected", "value": str(len(snapshot["skills"]))})
    if isinstance(snapshot.get("projects"), list):
        items.append({"label": "Projects detected", "value": str(len(snapshot["projects"]))})
    if isinstance(snapshot.get("files"), list):
        items.append({"label": "Files analyzed", "value": str(len(snapshot["files"]))})

    return {"type": "metrics", "items": items}


def create_app(db_dir: Optional[str] = None, auth_token: Optional[str] = None):
    """
    create_app() returns a Flask app with two routes:
      GET /portfolios/latest?projectId=...
      GET /portfolios?projectId=...&page=1&pageSize=20&sort=created_at:desc
    Protects routes with a simple Bearer token if provided.
    """
    from flask import Flask, jsonify, request
    app = Flask(__name__)

    token_required = auth_token or os.getenv("PORTFOLIO_API_TOKEN")
    max_summary_len = 400

    def _conn():
        if _open_db is not None:
            base = None
            if db_dir:
                from pathlib import Path
                base = Path(db_dir)
            return _open_db(base)
        import sqlite3
        from pathlib import Path
        base = Path(db_dir) if db_dir else Path("data")
        base.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(base / "capstone.db")

    def _auth():
        if not token_required:
            return True
        h = request.headers.get("Authorization", "")
        return h.startswith("Bearer ") and h.split(" ", 1)[1] == token_required

    @app.before_request
    def _check_auth():
        if not _auth():
            return jsonify({"data": None, "error": {"code": "Unauthorized", "detail": "Missing or invalid token"}}), 401

    @app.get("/portfolios/latest")
    def latest():
        project_id = request.args.get("projectId", "")
        if not project_id:
            return jsonify({"data": None, "error": {"code": "BadRequest", "detail": "projectId is required"}}), 400
        with _db_session(db_dir) as c:
            ensure_indexes(c)
            data = get_latest_snapshot(c, project_id)

        if data is None:
            return jsonify({"data": None, "error": {"code": "NotFound", "detail": "No snapshots found"}}), 404
        return jsonify({"data": data, "meta": {"projectId": project_id}, "error": None})
    @app.get("/portfolios/evidence")
    def evidence_latest():
        project_id = request.args.get("projectId", "")
        if not project_id:
            return jsonify({"data": None, "error": {"code": "BadRequest", "detail": "projectId is required"}}), 400

        with _db_session(db_dir) as c:
            ensure_indexes(c)
            snap = get_latest_snapshot(c, project_id)

        if snap is None:
            return jsonify({"data": None, "error": {"code": "NotFound", "detail": "No snapshots found"}}), 404

        evidence = _extract_evidence(snap)
        return jsonify({
            "data": {"projectId": project_id, "evidence": evidence},
            "error": None
        })

    @app.get("/portfolios")
    def list_():
        q = request.args
        project_id = q.get("projectId", "")
        if not project_id:
            return jsonify({"data": None, "error": {"code": "BadRequest", "detail": "projectId is required"}}), 400
        sort = q.get("sort", "created_at:desc")
        sort_field, _, sort_dir = sort.partition(":")
        with _db_session(db_dir) as c:
            ensure_indexes(c)
            items, total = list_snapshots(
                c,
                project_id=project_id,
                page=int(q.get("page", 1)),
                page_size=int(q.get("pageSize", 20)),
                sort_field=sort_field or "created_at",
                sort_dir=sort_dir or "desc",
                classification=q.get("classification"),
                primary_contributor=q.get("primaryContributor"),
    )

        payload = [s.snapshot for s in items]
        return jsonify({
            "data": payload,
            "meta": {
                "projectId": project_id,
                "page": int(q.get("page", 1)),
                "pageSize": int(q.get("pageSize", 20)),
                "total": total,
            },
            "error": None,
        })

    @app.get("/resume")
    def resume_list():
        q = request.args
        fmt = (q.get("format") or "").lower()
        sections = q.getlist("section")
        keywords = q.getlist("keyword")
        with _db_session(db_dir) as c:
            ensure_resume_schema(c)
            result = query_resume_entries(
                c,
                sections=sections or None,
                keywords=keywords or None,
                start_date=q.get("startDate"),
                end_date=q.get("endDate"),
                include_outdated=q.get("includeOutdated") == "true",
                limit=int(q.get("limit", 100)),
                offset=int(q.get("offset", 0)),
            )
            if fmt == "preview":
                preview = build_resume_preview(result, conn=c)
                return jsonify({"data": preview, "error": None})
            entries = [entry.to_dict() for entry in result.entries]
        return jsonify(
            {
                "data": entries,
                "meta": {
                    "warnings": result.warnings,
                    "missingSections": result.missing_sections,
                },
                "error": None,
            }
        )

    @app.get("/resume/<entry_id>")
    def resume_get(entry_id: str):
        with _db_session(db_dir) as c:
            ensure_resume_schema(c)
            entry = get_resume_entry(c, entry_id)
        if not entry:
            return jsonify({"data": None, "error": {"code": "NotFound", "detail": "Resume entry not found"}}), 404
        return jsonify({"data": entry.to_dict(), "error": None})

    @app.post("/resume")
    def resume_create():
        payload = request.get_json(silent=True) or {}
        section = payload.get("section")
        title = payload.get("title")
        body = payload.get("body")
        if not section or not title or not body:
            return (
                jsonify(
                    {
                        "data": None,
                        "error": {"code": "BadRequest", "detail": "section, title, and body are required"},
                    }
                ),
                400,
            )
        with _db_session(db_dir) as c:
            ensure_resume_schema(c)
            entry_id = insert_resume_entry(
                c,
                section=str(section),
                title=str(title),
                body=str(body),
                summary=payload.get("summary"),
                status=payload.get("status", "active"),
                metadata=payload.get("metadata") if isinstance(payload.get("metadata"), dict) else None,
                projects=payload.get("projects") if isinstance(payload.get("projects"), list) else None,
                skills=payload.get("skills") if isinstance(payload.get("skills"), list) else None,
                created_at=payload.get("created_at"),
            )
            entry = get_resume_entry(c, entry_id)
        return jsonify({"data": entry.to_dict() if entry else None, "error": None}), 201

    @app.post("/resume/<entry_id>/edit")
    def resume_edit(entry_id: str):
        payload = request.get_json(silent=True) or {}
        summary = payload.get("summary")
        if "summary" in payload:
            if not summary or not str(summary).strip():
                return jsonify({"data": None, "error": {"code": "UnprocessableEntity", "detail": "summary is required"}}), 422
            if len(str(summary).strip()) > max_summary_len:
                return jsonify({"data": None, "error": {"code": "UnprocessableEntity", "detail": "summary is too long"}}), 422
        with _db_session(db_dir) as c:
            ensure_resume_schema(c)
            entry = update_resume_entry(
                c,
                entry_id=entry_id,
                section=payload.get("section"),
                title=payload.get("title"),
                summary=str(summary).strip() if "summary" in payload else None,
                body=payload.get("body"),
                status=payload.get("status"),
                metadata=payload.get("metadata"),
                projects=payload.get("projects"),
                skills=payload.get("skills"),
                _summary_provided="summary" in payload,
                _metadata_provided="metadata" in payload,
                _projects_provided="projects" in payload,
                _skills_provided="skills" in payload,
            )
        if not entry:
            return jsonify({"data": None, "error": {"code": "NotFound", "detail": "Resume entry not found"}}), 404
        return jsonify({"data": entry.to_dict(), "error": None})

    @app.post("/resume/generate")
    def resume_generate():
        payload = request.get_json(silent=True) or {}
        fmt = str(payload.get("format", "json")).lower()
        if fmt not in {"json", "markdown", "pdf"}:
            return jsonify({"data": None, "error": {"code": "BadRequest", "detail": "format must be json, markdown, or pdf"}}), 400
        def _normalise_list(value: object) -> List[str] | None:
            if value is None:
                return None
            if isinstance(value, list):
                return [str(item) for item in value]
            return [str(value)]

        with _db_session(db_dir) as c:
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
                return jsonify({"data": None, "error": {"code": "NotFound", "detail": "No resume entries found"}}), 404
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
            return jsonify({"data": {"format": "pdf", "payload": encoded}, "error": None})
        if fmt == "markdown":
            return jsonify({"data": {"format": "markdown", "payload": data.decode("utf-8")}, "error": None})
        return jsonify({"data": {"format": "json", "payload": json.loads(data.decode("utf-8"))}, "error": None})

    @app.get("/resume-projects")
    def resume_projects_get():
        q = request.args
        project_ids = q.getlist("projectId")
        variant_name = q.get("variantName")
        audience = q.get("audience")
        active_only = q.get("activeOnly") == "true"
        limit = int(q.get("limit", 100))
        offset = int(q.get("offset", 0))
        with _db_session(db_dir) as c:
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
                    return jsonify({"data": None, "error": {"code": "NotFound", "detail": "No resume project found"}}), 404
                return jsonify({"data": item.to_dict(), "error": None})
            items = list_resume_project_descriptions(
                c,
                project_ids=project_ids or None,
                active_only=active_only,
                limit=limit,
                offset=offset,
            )
        payload = [item.to_dict() for item in items]
        return jsonify({
            "data": payload,
            "meta": {"limit": limit, "offset": offset, "total": len(payload)},
            "error": None,
        })

    @app.post("/resume-projects")
    def resume_projects_post():
        payload = request.get_json(silent=True) or {}
        project_id = payload.get("projectId") or payload.get("project_id")
        summary = payload.get("summary")
        metadata = payload.get("metadata")
        variant_name = payload.get("variantName")
        audience = payload.get("audience")
        is_active = payload.get("isActive", True)
        if not project_id:
            return jsonify({"data": None, "error": {"code": "BadRequest", "detail": "projectId is required"}}), 400
        if not summary or not str(summary).strip():
            return jsonify({"data": None, "error": {"code": "UnprocessableEntity", "detail": "summary is required"}}), 422
        summary = str(summary).strip()
        if len(summary) > max_summary_len:
            return jsonify({"data": None, "error": {"code": "UnprocessableEntity", "detail": "summary is too long"}}), 422
        if metadata is not None and not isinstance(metadata, dict):
            return jsonify({"data": None, "error": {"code": "BadRequest", "detail": "metadata must be an object"}}), 400
        with _db_session(db_dir) as c:
            ensure_resume_schema(c)
            # Reject unknown projects 
            if get_latest_snapshot(c, str(project_id)) is None:
                return jsonify({"data": None, "error": {"code": "NotFound", "detail": "Project not found"}}), 404
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
        return jsonify({"data": item.to_dict(), "error": None}), 201

    @app.post("/resume-projects/generate")
    def resume_projects_generate():
        payload = request.get_json(silent=True) or {}
        project_ids = payload.get("projectIds") or payload.get("project_ids") or payload.get("projectId")
        overwrite = bool(payload.get("overwrite", False))
        if isinstance(project_ids, str):
            project_ids = [project_ids]
        if not project_ids or not isinstance(project_ids, list):
            return jsonify({"data": None, "error": {"code": "BadRequest", "detail": "projectIds is required"}}), 400
        with _db_session(db_dir) as c:
            ensure_resume_schema(c)
            missing = []
            for pid in project_ids:
                if get_latest_snapshot(c, str(pid)) is None:
                    missing.append(pid)
            if missing:
                return jsonify({"data": None, "error": {"code": "NotFound", "detail": "Project not found", "missing": missing}}), 404
            items = generate_resume_project_descriptions(
                c,
                project_ids=[str(pid) for pid in project_ids],
                overwrite=overwrite,
            )
        payload = [item.to_dict() for item in items]
        return jsonify({"data": payload, "meta": {"total": len(payload)}, "error": None})

    return app
