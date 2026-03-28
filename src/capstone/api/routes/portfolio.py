from __future__ import annotations

import traceback
import tempfile
import zipfile
import calendar

from datetime import UTC, date, datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Body, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from capstone.activity_log import log_event
from capstone.language_detection import classify_activity
from capstone.metrics import FileMetric, compute_metrics
from capstone.portfolio_pdf_builder import build_portfolio_pdf_with_pandoc
from capstone.portfolio_retrieval import _db_session
from capstone.storage import _UNSET as _DB_UNSET
from capstone.api.routes.auth import get_authenticated_username
import capstone.storage as storage_module
from capstone.storage import (
    fetch_latest_snapshot,
    fetch_latest_snapshots,
    fetch_latest_snapshots_with_zip,
    fetch_project_snapshot_history,
)

router = APIRouter(prefix="/portfolio", tags=["portfolio"])

_DB_DIR: Optional[str] = None
_TOKEN: Optional[str] = None


def configure(db_dir: Optional[str], auth_token: Optional[str]) -> None:
    global _DB_DIR, _TOKEN
    _DB_DIR = db_dir
    _TOKEN = auth_token


def _resolve_db_dir(request: Request) -> Optional[str]:
    return getattr(request.app.state, "db_dir", None) or _DB_DIR


def _resolve_auth_token(request: Request) -> Optional[str]:
    return getattr(request.app.state, "auth_token", None) or _TOKEN


def _check_auth(request: Request) -> None:
    token = _resolve_auth_token(request)
    if not token:
        return

    auth_header = request.headers.get("Authorization", "")
    if not (auth_header.startswith("Bearer ") and auth_header.split(" ", 1)[1] == token):
        raise HTTPException(status_code=401, detail="Missing or invalid token")


def _bind_current_user_from_session(request: Request) -> None:
    username = get_authenticated_username(request)
    if username:
        storage_module.CURRENT_USER = username


def _load_heatmap_rows(db_dir: str, *, user=_DB_UNSET) -> list[dict[str, Any]]:
    with _db_session(db_dir, user=user) as c:
        return fetch_latest_snapshots_with_zip(c) or []


def _load_heatmap_rows_with_guest_fallback(db_dir: str) -> list[dict[str, Any]]:
    rows = _load_heatmap_rows(db_dir)
    if rows:
        return rows
    return _load_heatmap_rows(db_dir, user=None)


class PortfolioProject(BaseModel):
    project_id: str
    title: str
    summary: Optional[str] = None
    technologies: list[str] = Field(default_factory=list)
    highlights: list[str] = Field(default_factory=list)


class Portfolio(BaseModel):
    id: str
    owner: Optional[str] = None
    projects: list[PortfolioProject]
    created_at: datetime
    updated_at: datetime


class GeneratePortfolioRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    project_ids: Optional[list[str]] = Field(None, alias="projectIds")
    owner: Optional[str] = None


class EditPortfolioRequest(BaseModel):
    owner: Optional[str] = None
    projects: Optional[list[PortfolioProject]] = None
    summary: Optional[str] = None


class PortfolioResponse(BaseModel):
    portfolio: Portfolio


class ExportFormat(str, Enum):
    json = "json"
    markdown = "markdown"
    pdf = "pdf"


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _dedupe_strings(items: list[Any]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []

    for item in items:
        if item is None:
            continue
        s = str(item).strip()
        if not s or s in seen:
            continue
        seen.add(s)
        result.append(s)

    return result


def _pick_first_str(d: dict[str, Any], keys: list[str]) -> Optional[str]:
    for key in keys:
        value = d.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _extract_skill_names(value: Any) -> list[str]:
    names: list[Any] = []

    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                name = _pick_first_str(item, ["skill", "name", "label"])
                if name:
                    names.append(name)
            else:
                names.append(item)

    elif isinstance(value, dict):
        categorized_keys = ("technical", "tools", "frameworks", "languages")
        used_categorized = False

        for key in categorized_keys:
            if key in value:
                used_categorized = True
                names.extend(_as_list(value.get(key)))

        if not used_categorized:
            names.extend(list(value.keys()))

    elif value is not None:
        names.append(value)

    return _dedupe_strings(names)


def _extract_technologies(snapshot: dict[str, Any]) -> list[str]:
    tech: list[Any] = []

    langs = snapshot.get("languages")
    if isinstance(langs, dict):
        tech.extend(list(langs.keys()))
    elif isinstance(langs, list):
        tech.extend(langs)

    tech.extend(_as_list(snapshot.get("frameworks")))
    tech.extend(_extract_skill_names(snapshot.get("skills")))
    tech.extend(_as_list(snapshot.get("tech_stack")))
    tech.extend(_as_list(snapshot.get("technologies")))

    return _dedupe_strings(tech)


def _extract_highlights(snapshot: dict[str, Any]) -> list[str]:
    highlights: list[Any] = []
    highlights.extend(_as_list(snapshot.get("highlights")))
    highlights.extend(_as_list(snapshot.get("key_features")))
    highlights.extend(_as_list(snapshot.get("notable_points")))
    return _dedupe_strings(highlights)[:6]


def _extract_summary(snapshot: dict[str, Any]) -> Optional[str]:
    return _pick_first_str(snapshot, ["summary", "description", "overview", "abstract"])


def _extract_title(project_id: str, snapshot: dict[str, Any]) -> str:
    title = _pick_first_str(snapshot, ["title", "project_name", "name", "repo_name", "repository"])
    return title or project_id


def _project_from_snapshot(project_id: str, snapshot: dict[str, Any]) -> PortfolioProject:
    return PortfolioProject(
        project_id=project_id,
        title=_extract_title(project_id, snapshot),
        summary=_extract_summary(snapshot),
        technologies=_extract_technologies(snapshot),
        highlights=_extract_highlights(snapshot),
    )


def build_portfolio(portfolio_id: str, owner: Optional[str], projects: list[PortfolioProject]) -> Portfolio:
    now = _now_utc()
    return Portfolio(
        id=portfolio_id,
        owner=owner,
        projects=projects,
        created_at=now,
        updated_at=now,
    )


def _default_portfolio_summary() -> dict[str, Any]:
    return {
        "owner": None,
        "education": "UBC Okanagan — BSc Computer Science",
        "awards": ["Capstone Team Contributor"],
        "skills": [],
        "projects": [],
        "highlights": [],
    }


def _snapshot_file_count(snapshot: dict[str, Any]) -> int:
    file_summary = snapshot.get("file_summary")
    if isinstance(file_summary, dict):
        return _safe_int(file_summary.get("file_count"))
    return _safe_int(snapshot.get("file_count"))


def _snapshot_active_days(snapshot: dict[str, Any]) -> int:
    file_summary = snapshot.get("file_summary")
    if isinstance(file_summary, dict):
        return _safe_int(file_summary.get("active_days"))
    return 0


def _snapshot_skill_names(snapshot: dict[str, Any]) -> list[str]:
    return _extract_skill_names(snapshot.get("skills")) or _extract_technologies(snapshot)


def _build_project_evolution_steps(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered = list(reversed(history))
    milestones: list[dict[str, Any]] = []
    previous_skills: set[str] = set()
    previous_file_count = 0
    previous_active_days = 0

    for index, item in enumerate(ordered):
        snapshot = item.get("snapshot") if isinstance(item.get("snapshot"), dict) else {}
        created_at = str(item.get("created_at") or "").strip()
        summary = _extract_summary(snapshot) or ""
        file_count = _snapshot_file_count(snapshot)
        active_days = _snapshot_active_days(snapshot)
        skills = _snapshot_skill_names(snapshot)
        skill_set = {skill.lower(): skill for skill in skills}
        new_skills = [skill_set[key] for key in skill_set if key not in previous_skills][:4]
        file_delta = file_count - previous_file_count if index > 0 else file_count
        skill_delta = len(skills) - len(previous_skills) if index > 0 else len(skills)
        active_days_delta = active_days - previous_active_days if index > 0 else active_days

        if index == 0:
            milestone_type = "Baseline"
        elif index == len(ordered) - 1:
            milestone_type = "Current State"
        elif file_delta >= 5 or skill_delta >= 2:
            milestone_type = "Expansion"
        elif active_days_delta > 0 or new_skills:
            milestone_type = "Refinement"
        else:
            milestone_type = f"Iteration {index + 1}"

        change_summary_parts: list[str] = []
        if file_delta > 0:
            change_summary_parts.append(f"Added {file_delta} file{'s' if file_delta != 1 else ''}")
        elif file_delta < 0:
            change_summary_parts.append(f"Reduced file scope by {abs(file_delta)}")

        if skill_delta > 0:
            change_summary_parts.append(f"Expanded into {skill_delta} more skill signal{'s' if skill_delta != 1 else ''}")
        elif skill_delta < 0:
            change_summary_parts.append(f"Focused down by {abs(skill_delta)} skill signal{'s' if skill_delta != 1 else ''}")

        if active_days_delta > 0:
            change_summary_parts.append(f"Increased active span by {active_days_delta} day{'s' if active_days_delta != 1 else ''}")

        if new_skills:
            change_summary_parts.append(f"Introduced {', '.join(new_skills[:3])}")

        if not change_summary_parts:
            change_summary_parts.append("Maintained the implementation baseline")

        milestones.append(
            {
                "label": milestone_type,
                "timestamp": created_at,
                "summary": summary,
                "changeSummary": ". ".join(change_summary_parts) + ".",
                "metrics": {
                    "files": file_count,
                    "skills": len(skills),
                    "active_days": active_days,
                },
                "delta": {
                    "files": file_delta,
                    "skills": skill_delta,
                    "active_days": active_days_delta,
                },
                "new_skills": new_skills,
                "highlights": _extract_highlights(snapshot)[:3],
            }
        )

        previous_skills = set(skill_set.keys())
        previous_file_count = file_count
        previous_active_days = active_days

    return milestones


def _load_export_projects(portfolio_id: str, db_dir: str) -> list[PortfolioProject]:
    with _db_session(db_dir) as c:
        if portfolio_id == "latest":
            rows = fetch_latest_snapshots(c) or []
            projects: list[PortfolioProject] = []

            for row in rows:
                project_id = row.get("project_id")
                snapshot = row.get("snapshot")
                if project_id and isinstance(snapshot, dict):
                    projects.append(_project_from_snapshot(str(project_id), snapshot))

            return projects

        snapshot = fetch_latest_snapshot(c, portfolio_id)
        if not snapshot or not isinstance(snapshot, dict):
            return []

        return [_project_from_snapshot(portfolio_id, snapshot)]

def _extract_row_project_and_snapshot(row: Any) -> tuple[Optional[str], Optional[dict[str, Any]]]:
    """
    Normalize rows returned by fetch_latest_snapshots().

    Supports:
    - dict-like rows with keys: project_id, snapshot
    - tuple/list rows like: (project_id, snapshot, ...)
    """
    project_id: Optional[str] = None
    snapshot: Optional[dict[str, Any]] = None

    if isinstance(row, dict):
        raw_project_id = row.get("project_id")
        raw_snapshot = row.get("snapshot")

        if raw_project_id is not None:
            project_id = str(raw_project_id)

        if isinstance(raw_snapshot, dict):
            snapshot = raw_snapshot

    return project_id, snapshot


def _build_file_summary_from_zip_path(zip_path: str | None) -> dict[str, Any]:
    if not zip_path:
        return {}

    path = Path(zip_path)
    if not path.exists():
        return {}

    metrics_inputs: list[FileMetric] = []

    try:
        with zipfile.ZipFile(path) as zf:
            roots = set()
            for info in zf.infolist():
                if info.is_dir():
                    continue
                parts = [p for p in info.filename.strip("/").split("/") if p]
                if parts:
                    roots.add(parts[0])
            root_name = next(iter(roots)) if len(roots) == 1 else None

            for info in zf.infolist():
                if info.is_dir():
                    continue
                raw_path = info.filename.strip("/")
                if not raw_path:
                    continue
                rel_path = raw_path
                if root_name and raw_path.startswith(root_name + "/"):
                    rel_path = raw_path[len(root_name) + 1 :]
                metrics_inputs.append(
                    FileMetric(
                        path=rel_path,
                        size=int(info.file_size),
                        modified=datetime(*info.date_time),
                        activity=classify_activity(rel_path),
                    )
                )
    except (zipfile.BadZipFile, FileNotFoundError, OSError, ValueError):
        return {}

    return compute_metrics(metrics_inputs).__dict__


def _build_daily_activity_from_zip_path(zip_path: str | None) -> dict[str, int]:
    if not zip_path:
        return {}

    path = Path(zip_path)
    if not path.exists():
        return {}

    daily_counts: dict[str, int] = {}

    try:
        with zipfile.ZipFile(path) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                day_key = date(*info.date_time[:3]).isoformat()
                daily_counts[day_key] = daily_counts.get(day_key, 0) + 1
    except (zipfile.BadZipFile, FileNotFoundError, OSError, ValueError):
        return {}

    return dict(sorted(daily_counts.items()))


def _expand_monthly_timeline_to_daily(monthly_timeline: dict[str, Any]) -> dict[str, int]:
    daily_counts: dict[str, int] = {}

    for period, raw_count in sorted(monthly_timeline.items()):
        period_key = str(period).strip()
        if not period_key or not isinstance(period_key, str) or len(period_key) != 7 or period_key[4] != "-":
            continue

        try:
            year = int(period_key[:4])
            month = int(period_key[5:7])
            days_in_month = calendar.monthrange(year, month)[1]
        except (ValueError, calendar.IllegalMonthError):
            continue

        count = max(0, _safe_int(raw_count))
        if count == 0:
            continue

        base = count // days_in_month
        remainder = count % days_in_month

        for day in range(1, days_in_month + 1):
            day_count = base + (1 if day <= remainder else 0)
            if day_count <= 0:
                continue
            day_key = date(year, month, day).isoformat()
            daily_counts[day_key] = day_count

    return daily_counts


def _normalize_heatmap_granularity(value: Any) -> str:
    raw = str(value or "day").strip().lower()
    if raw in {"year", "month", "day"}:
        return raw
    return "day"


def _build_heatmap_period_key(period: str, granularity: str) -> Optional[str]:
    raw = str(period or "").strip()
    if granularity == "day":
        if len(raw) == 10 and raw[4] == "-" and raw[7] == "-":
            return raw
        return None
    if granularity == "month":
        if len(raw) >= 7 and raw[4] == "-":
            return raw[:7]
        return None
    if granularity == "year":
        if len(raw) >= 4:
            return raw[:4]
        return None
    return None


def _collect_heatmap_project_activity(row: dict[str, Any]) -> dict[str, int]:
    snapshot = row.get("snapshot") or {}
    zip_path = row.get("zip_path")

    if not isinstance(snapshot, dict):
        return {}

    file_summary = snapshot.get("file_summary") or {}
    monthly_timeline = file_summary.get("timeline") if isinstance(file_summary, dict) else {}
    activity_by_day = {}
    if isinstance(file_summary, dict):
        activity_by_day = file_summary.get("daily_timeline") or {}

    if not isinstance(activity_by_day, dict) or not activity_by_day:
        activity_by_day = _build_daily_activity_from_zip_path(zip_path)

    if (not isinstance(activity_by_day, dict) or not activity_by_day) and isinstance(monthly_timeline, dict):
        activity_by_day = _expand_monthly_timeline_to_daily(monthly_timeline)

    if not isinstance(activity_by_day, dict):
        return {}

    return activity_by_day


def _build_heatmap_response(
    rows: list[dict[str, Any]],
    granularity: str,
    selected_project_id: str,
) -> dict[str, Any]:
    activity_counts: dict[str, int] = {}
    available_projects: list[str] = []
    contributing_projects: set[str] = set()

    for row in rows:
        project_id = str(row.get("project_id") or "").strip()
        if not project_id:
            continue

        available_projects.append(project_id)

        if selected_project_id and project_id != selected_project_id:
            continue

        activity_by_day = _collect_heatmap_project_activity(row)
        if not activity_by_day:
            continue

        contributing_projects.add(project_id)

        for period, count in activity_by_day.items():
            key = _build_heatmap_period_key(str(period), granularity)
            if not key:
                continue
            activity_counts[key] = activity_counts.get(key, 0) + _safe_int(count)

    project_ids = sorted(set(available_projects))

    if not activity_counts:
        return {
            "cells": [],
            "maxCount": 0,
            "projectCount": len(contributing_projects),
            "granularity": granularity,
            "selectedProjectId": selected_project_id,
            "projects": project_ids,
        }

    ordered_periods = sorted(activity_counts.items(), key=lambda item: item[0])
    max_count = max(activity_counts.values()) if activity_counts else 0
    cells = []

    for period, count in ordered_periods:
        intensity = round(count / max_count, 3) if max_count > 0 else 0.0
        cells.append(
            {
                "period": period,
                "count": count,
                "intensity": intensity,
            }
        )

    return {
        "cells": cells,
        "maxCount": max_count,
        "projectCount": len(contributing_projects),
        "granularity": granularity,
        "selectedProjectId": selected_project_id,
        "projects": project_ids,
    }

    if isinstance(row, (tuple, list)):
        if len(row) >= 1 and row[0] is not None:
            project_id = str(row[0])

        if len(row) >= 2 and isinstance(row[1], dict):
            snapshot = row[1]

        return project_id, snapshot

    return None, None

@router.post("/generate")
def generate_portfolio(payload: GeneratePortfolioRequest, request: Request) -> dict[str, Any]:
    _check_auth(request)

    db_dir = _resolve_db_dir(request)
    if not db_dir:
        raise HTTPException(status_code=500, detail="Database not configured")

    if not payload.project_ids:
        raise HTTPException(status_code=400, detail="projectIds/project_ids must be a non-empty list")

    projects: list[PortfolioProject] = []

    with _db_session(db_dir) as c:
        for pid in payload.project_ids:
            snapshot = fetch_latest_snapshot(c, str(pid))

            if not snapshot:
                log_event("ERROR", f"Snapshot missing during portfolio generation · Project: {pid}")
                raise HTTPException(status_code=404, detail=f"No snapshot found for project ID {pid}")

            if not isinstance(snapshot, dict):
                raise HTTPException(status_code=500, detail=f"Invalid snapshot format for project ID {pid}")

            projects.append(_project_from_snapshot(str(pid), snapshot))

    portfolio = build_portfolio(
        portfolio_id="latest",
        owner=payload.owner,
        projects=projects,
    )

    log_event("SUCCESS", f"Portfolio generated · Owner: {payload.owner or 'N/A'} · Projects: {len(projects)}")

    return {
        "portfolio": portfolio.model_dump(),
        "data": [
            {
                "project_id": p.project_id,
                "summary": p.summary,
                "title": p.title,
            }
            for p in projects
        ],
        "error": None,
    }


@router.post("/showcase/edit")
async def edit_portfolio_showcase(request: Request, payload: dict[str, Any] = Body(...)):
    _check_auth(request)

    project_id = (payload.get("projectId") or "").strip()
    summary = (payload.get("summary") or "").strip()

    if not project_id or not summary:
        raise HTTPException(status_code=400, detail="projectId and summary are required")

    return {"data": {"projectId": project_id, "summary": summary}, "error": None}


@router.post("/{id}/edit")
def edit_portfolio(id: str, payload: EditPortfolioRequest, request: Request) -> dict[str, Any]:
    _check_auth(request)

    if id == "showcase":
        raise HTTPException(status_code=400, detail="Use /portfolio/showcase/edit with projectId and summary")

    if payload.summary is not None and not payload.projects:
        summary = str(payload.summary).strip()
        if not summary:
            raise HTTPException(status_code=400, detail="summary is required")
        return {"data": {"projectId": id, "summary": summary}, "error": None}

    if payload.summary is None and payload.projects is None and payload.owner is None:
        raise HTTPException(status_code=400, detail="No changes provided")

    projects = payload.projects or []
    portfolio = build_portfolio(
        portfolio_id=id,
        owner=payload.owner,
        projects=projects,
    )

    log_event("INFO", f"Portfolio edited · Portfolio ID: {id}")
    return {"portfolio": portfolio.model_dump(), "error": None}


@router.get("/latest/summary")
def latest_portfolio_summary(request: Request) -> dict[str, Any]:
    try:
        _check_auth(request)
        _bind_current_user_from_session(request)

        db_dir = _resolve_db_dir(request)
        if not db_dir:
            raise HTTPException(status_code=500, detail="Database not configured")

        with _db_session(db_dir) as c:
            rows = fetch_latest_snapshots(c) or []

        if not rows:
            return {"data": _default_portfolio_summary(), "error": None}

        projects: list[PortfolioProject] = []
        all_skills: list[str] = []
        all_highlights: list[str] = []

        for row in rows:
            project_id, snapshot = _extract_row_project_and_snapshot(row)

            if not project_id or not isinstance(snapshot, dict):
                continue

            project = _project_from_snapshot(project_id, snapshot)
            projects.append(project)
            all_skills.extend(project.technologies)
            all_highlights.extend(project.highlights)

        summary = _default_portfolio_summary()
        summary["projects"] = [project.model_dump() for project in projects]
        summary["skills"] = _dedupe_strings(all_skills)
        summary["highlights"] = _dedupe_strings(all_highlights)[:10]

        log_event("SUCCESS", f"Portfolio summary generated · Projects: {len(projects)}")
        return {"data": summary, "error": None}

    except Exception as exc:
        return {
            "data": None,
            "error": str(exc),
            "trace": traceback.format_exc(),
        }

@router.get("/activity-heatmap")
def portfolio_activity_heatmap(request: Request) -> dict[str, Any]:
    try:
        _check_auth(request)
        _bind_current_user_from_session(request)

        db_dir = _resolve_db_dir(request)
        if not db_dir:
            raise HTTPException(status_code=500, detail="Database not configured")

        granularity = _normalize_heatmap_granularity(request.query_params.get("granularity"))
        selected_project_id = str(request.query_params.get("project_id") or "").strip()
        rows = _load_heatmap_rows(db_dir)
        data = _build_heatmap_response(rows, granularity, selected_project_id)

        if not data["cells"] and get_authenticated_username(request):
            guest_rows = _load_heatmap_rows_with_guest_fallback(db_dir)
            guest_data = _build_heatmap_response(guest_rows, granularity, selected_project_id)
            if guest_data["cells"]:
                data = guest_data

        log_event(
            "SUCCESS",
            "Portfolio activity heatmap generated"
            f" · Granularity: {granularity}"
            f" · Cells: {len(data['cells'])}"
            f" · Projects: {data['projectCount']}"
            + (f" · Selected Project: {selected_project_id}" if selected_project_id else ""),
        )

        return {
            "data": data,
            "error": None,
        }

    except Exception as exc:
        return {
            "data": None,
            "error": str(exc),
            "trace": traceback.format_exc(),
        }


@router.get("/project-evolution")
def portfolio_project_evolution(
    request: Request,
    project_ids: str = "",
    limit: int = 6,
) -> dict[str, Any]:
    try:
        _check_auth(request)
        _bind_current_user_from_session(request)

        db_dir = _resolve_db_dir(request)
        if not db_dir:
            raise HTTPException(status_code=500, detail="Database not configured")

        cleaned_ids = [
            str(project_id).strip()
            for project_id in str(project_ids or "").split(",")
            if str(project_id).strip()
        ][:10]

        if not cleaned_ids:
            return {"data": {}, "error": None}

        payload: dict[str, Any] = {}
        with _db_session(db_dir) as c:
            for project_id in cleaned_ids:
                history = fetch_project_snapshot_history(c, project_id, limit=max(1, min(int(limit), 12)))
                payload[project_id] = {
                    "projectId": project_id,
                    "steps": _build_project_evolution_steps(history),
                    "snapshotCount": len(history),
                }

        log_event("SUCCESS", f"Portfolio project evolution generated · Projects: {len(payload)}")
        return {"data": payload, "error": None}

    except Exception as exc:
        return {
            "data": None,
            "error": str(exc),
            "trace": traceback.format_exc(),
        }


@router.get("/{id}/export")
def export_portfolio(id: str, request: Request, format: ExportFormat = ExportFormat.json) -> Any:
    _check_auth(request)

    db_dir = _resolve_db_dir(request)
    if not db_dir:
        raise HTTPException(status_code=500, detail="Database not configured")

    log_event("INFO", f"Portfolio export requested · ID: {id} · Format: {format.value}")

    if format == ExportFormat.json:
        return {
            "portfolio_id": id,
            "exported_at": _now_utc().isoformat(),
        }

    if format == ExportFormat.markdown:
        content = f"# Portfolio {id}\n\nExport generated at {_now_utc().isoformat()}\n"
        log_event("SUCCESS", f"Portfolio exported · ID: {id} · Format: {format.value}")
        return {"content": content}

    if format == ExportFormat.pdf:
        projects = _load_export_projects(id, db_dir)
        entries = [
            {
                "project_id": p.project_id,
                "name": p.title,
                "summary": p.summary or ("Highlights: " + "; ".join(p.highlights) if p.highlights else ""),
                "source": "latest_snapshot",
            }
            for p in projects
        ]

        if not entries:
            entries = [
                {
                    "project_id": id,
                    "name": id,
                    "summary": "No snapshot data available.",
                    "source": "placeholder",
                }
            ]

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                out_path = Path(tmpdir) / f"portfolio_{id}.pdf"
                build_portfolio_pdf_with_pandoc(entries, out_path, title=f"Portfolio {id}")
                pdf_bytes = out_path.read_bytes()
        except Exception:
            pdf_bytes = (
                b"%PDF-1.4\n"
                b"1 0 obj<<>>\n"
                b"trailer<<>>\n"
                b"%%EOF"
            )

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="portfolio_{id}.pdf"'},
        )

    raise HTTPException(status_code=400, detail="Unsupported format")
