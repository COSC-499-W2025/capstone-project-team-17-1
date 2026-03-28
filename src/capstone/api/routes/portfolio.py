from __future__ import annotations

import traceback
import tempfile
import zipfile
import calendar

from datetime import UTC, date, datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Body, HTTPException, Request, Response, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

from capstone.activity_log import log_event
from capstone.language_detection import classify_activity
from capstone.metrics import FileMetric, compute_metrics
from capstone.portfolio_pdf_builder import build_portfolio_pdf_with_pandoc
from capstone.portfolio_retrieval import _db_session, _extract_evidence, get_portfolio_entry, get_portfolio_entries
from capstone.api.routes.auth import get_authenticated_username
import capstone.storage as storage_module
from capstone.storage import fetch_latest_snapshot, fetch_latest_snapshots, fetch_latest_snapshots_with_zip
from capstone.project_role import infer_project_role_from_snapshot
from capstone.top_project_summaries import gather_evidence
from capstone.api.portfolio_helpers import (
    ensure_indexes,
    ensure_portfolio_tables,
    get_portfolio_customization,
    list_portfolio_images,
    save_portfolio_image,
    delete_portfolio_image,
    set_cover_portfolio_image,
    reorder_portfolio_images,
    upsert_portfolio_customization,
    get_latest_snapshot as helper_get_latest_snapshot,
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


def _load_heatmap_rows(db_dir: str) -> list[dict[str, Any]]:
    with _db_session(db_dir) as c:
        return fetch_latest_snapshots_with_zip(c) or []


def _load_heatmap_rows_with_guest_fallback(db_dir: str) -> list[dict[str, Any]]:
    rows = _load_heatmap_rows(db_dir)
    if rows:
        return rows

    previous_user = storage_module.CURRENT_USER
    try:
        storage_module.CURRENT_USER = None
        return _load_heatmap_rows(db_dir)
    finally:
        storage_module.CURRENT_USER = previous_user


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

    template_id: Optional[str] = None
    key_role: Optional[str] = None
    evidence_of_success: Optional[str] = None
    portfolio_blurb: Optional[str] = None


class ReorderPortfolioImagesRequest(BaseModel):
    image_ids: list[str]


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
    

def _resolve_images_base_dir(request: Request) -> Path:
    db_dir = _resolve_db_dir(request)
    if db_dir:
        return Path(db_dir)
    return Path("data")


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


def _stringify_evidence_value(value: Any) -> str:
    if isinstance(value, dict):
        label = str(value.get("label") or "").strip()
        raw = value.get("value")
        if isinstance(raw, dict):
            raw = ", ".join(
                str(v).strip()
                for v in raw.values()
                if str(v).strip()
            )
        elif isinstance(raw, list):
            raw = ", ". join(str(v).strip() for v in raw if str(v).strip())
        text = str(raw or "").strip()
        return text or label
    return str(value or "").strip()

def _format_portfolio_evidence_line(label: str, value: str) -> str:
    label = str(label or "").strip()
    value = str(value or "").strip()
    if not value:
        return ""
    if not label:
        return value
    return f"{label}: {value}"


def _collect_portfolio_evidence_lines(snapshot: dict[str, Any], limit: int = 4) -> list[str]:
    lines: list[str] = []

    # pull structured evidence first if it exists in snapshot
    extracted = _extract_evidence(snapshot)
    extracted_items = extracted.get("items", []) if isinstance(extracted, dict) else []

    for item in extracted_items:
        if not isinstance(item, dict):
            text = str(item).strip()
        else:
            text = _format_portfolio_evidence_line(
                item.get("label", ""),
                _stringify_evidence_value(item),
            )
        if text and text not in lines:
            lines.append(text)

    # fill with general evidence generated from snapshot metrics
    generated = gather_evidence(snapshot)
    for evidence in generated:
        detail = str(getattr(evidence, "detail", "") or "").strip()
        if detail and detail not in lines:
            lines.append(detail)

    # default if still empty
    if not lines:
        file_summary = snapshot.get("file_summary") or {}
        file_count = 0
        active_days = 0
        if isinstance(file_summary, dict):
            file_count = _safe_int(file_summary.get("file_count"))
            active_days = _safe_int(file_summary.get("active_days"))

        if file_count:
            lines.append(f"{file_count} files analyzed")
        if active_days:
            lines.append(f"Active development across {active_days} tracked days")

    return lines[:limit]

def _build_portfolio_blurb(project_id: str, snapshot: dict[str, Any], inferred_role: str) -> str:
    title = _extract_title(project_id, snapshot)
    technologies = _extract_technologies(snapshot)
    frameworks = _as_list(snapshot.get("frameworks"))
    collaboration = snapshot.get("collaboration", {}) or {}
    classification = str(collaboration.get("classification") or "").strip().lower()

    raw_summary = _extract_summary(snapshot)
    existing = _extract_summary(snapshot)
    
    if existing:
        lowered = existing.lower()
        generic_markers = [
            "uses ",
            "showcases applied software development work",
            "deliver core project functionality",
        ]
        if not any(marker in lowered for marker in generic_markers):
            return existing

    stack = _dedupe_strings([*technologies, *frameworks])[:4]
    stack_text = ", ".join(stack)

    role_phrase = inferred_role.lower() if inferred_role else "software development"

    if classification == "individual":
        if stack_text:
            return (
                f"{title} is an individual {role_phrase} project built with {stack_text}. "
                f"It focuses on delivering the core functionality and main use case of the application."
            )
        return (
            f"{title} is an individual {role_phrase} project focused on building a complete working solution "
            f"for its main purpose."
        )
                
    if classification == "collaborative":
        if stack_text:
            return (
                f"{title} is a collaborative {role_phrase} project built with {stack_text}. "
                f"It is designed to deliver the main product workflow and overall user experience."
            )
        return (
            f"{title} is a collaborative {role_phrase} project focused on delivering the main functionality "
            f"and shared project goals."
        )

    # fallback for unknown/missing collaboration data
    if stack_text:
        return (
            f"{title} is a {role_phrase} project built with {stack_text}. "
            f"It is intended to deliver the main functionality and core project experience."
        )

    return (
        f"{title} is a {role_phrase} project focused on delivering a working solution for its primary purpose."
    )
    
    
def _build_analysis_defaults(project_id: str, snapshot: dict[str, Any]) -> dict[str, str]:
    summary = ""
    highlights = _extract_highlights(snapshot)

    evidence_lines = _collect_portfolio_evidence_lines(snapshot, limit=4)
    
    if not evidence_lines and highlights:
        evidence_lines = highlights[:2]
        
    evidence_text = " • ".join(evidence_lines).strip()

    collaboration = snapshot.get("collaboration", {}) or {}
    classification = str(collaboration.get("classification") or "").strip().lower()
    primary = str(collaboration.get("primary_contributor") or "").strip()
    
    inferred_role = str(snapshot.get("project_role") or "").strip()
    if not inferred_role:
        inferred_role = infer_project_role_from_snapshot(snapshot)

    if classification == "individual":
        role_text = inferred_role
    elif primary:
        role_text = f"{inferred_role}"
    else:
        role_text = inferred_role
        
    summary = _build_portfolio_blurb(project_id, snapshot, inferred_role)

    return {
        "key_role": role_text,
        "evidence_of_success": evidence_text,
        "portfolio_blurb": summary
    }
    

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


def _extract_row_project_and_snapshot(row: Any) -> tuple[Optional[str], Optional[dict[str, Any]]]:
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

# helper to build data for case study theme
def _build_case_study_abstract(project_id: str, snapshot: dict[str, Any]) -> str:
    existing = _extract_summary(snapshot)
    if existing:
        return existing.strip()

    title = _extract_title(project_id, snapshot)
    technologies = _extract_technologies(snapshot)[:4]
    highlights = _extract_highlights(snapshot)[:2]

    tech_text = ", ".join(technologies)
    highlight_text = " ".join(highlights)

    if tech_text and highlight_text:
        return f"{title} is a project built with {tech_text}. {highlight_text}"

    if tech_text:
        return f"{title} is a project built with {tech_text} to deliver its core functionality."

    return f"{title} is a software project focused on delivering its main use case."

# helper to build data for portfolio templates
def _build_template_payload(
    project_id: str,
    snapshot: dict[str, Any],
    customization: dict[str, Any],
    images: list[dict[str, Any]],
) -> dict[str, Any]:
    resolved = {
        "key_role": str(customization.get("key_role") or ""),
        "evidence_of_success": str(customization.get("evidence_of_success") or ""),
        "portfolio_blurb": str(customization.get("portfolio_blurb") or ""),
    }

    default_role = str(snapshot.get("project_role") or infer_project_role_from_snapshot(snapshot))
    role = resolved["key_role"] or default_role
    blurb = resolved["portfolio_blurb"] or _build_portfolio_blurb(project_id, snapshot, role)
    evidence = resolved["evidence_of_success"] or " • ".join(_collect_portfolio_evidence_lines(snapshot, limit=4))

    cover_image = next((img for img in images if img.get("is_cover")), None)
    if not cover_image and images:
        cover_image = images[0]

    metrics = []
    file_summary = snapshot.get("file_summary") or {}
    if isinstance(file_summary, dict):
        if file_summary.get("file_count"):
            metrics.append({"label": "Files", "value": file_summary.get("file_count")})
        if file_summary.get("active_days"):
            metrics.append({"label": "Active Days", "value": file_summary.get("active_days")})
        if file_summary.get("total_bytes"):
            metrics.append({"label": "Bytes", "value": file_summary.get("total_bytes")})

    return {
        "classic": {
            "title": _extract_title(project_id, snapshot),
            "summary": blurb,
            "role": role,
            "evidence": evidence,
            "cover_image": cover_image,
            "stack": _extract_technologies(snapshot)[:6],
        },
        "gallery": {
            "title": _extract_title(project_id, snapshot),
            "headline": blurb,
            "cover_image": cover_image,
            "images": images[:8],
        },
        "case_study": {
            "title": _extract_title(project_id, snapshot),
            "abstract": _build_case_study_abstract(project_id, snapshot),
            "role": role,
            "evidence": _collect_portfolio_evidence_lines(snapshot, limit=4),
            "metrics": metrics,
            "stack": _extract_technologies(snapshot)[:6],
            "cover_image": cover_image,
        },
    }


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
    _bind_current_user_from_session(request)

    if id == "showcase":
        raise HTTPException(status_code=400, detail="Use /portfolio/showcase/edit with projectId and summary")
    
    db_dir = _resolve_db_dir(request)
    if not db_dir:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    customization_requested = any(
        value is not None
        for value in (
            payload.template_id,
            payload.key_role,
            payload.evidence_of_success,
            payload.portfolio_blurb,
            payload.summary
        )
    )
    
    if customization_requested and payload.projects is None:
        with _db_session(db_dir) as conn:
            ensure_portfolio_tables(conn)
            ensure_indexes(conn)
            
            snapshot = helper_get_latest_snapshot(conn, id)
            if not snapshot:
                raise HTTPException(status_code=404, detail="Project not found")
            
            current = get_portfolio_customization(conn, id) or {}
            
            try:
                customization = upsert_portfolio_customization(
                    conn,
                    id,
                    template_id=(payload.template_id or current.get("template_id") or "classic"),
                    key_role=(payload.key_role if payload.key_role is not None else current.get("key_role", "")),
                    evidence_of_success=(
                        payload.evidence_of_success
                        if payload.evidence_of_success is not None
                        else current.get("evidence_of_success", "")
                    ),
                    portfolio_blurb=(
                        payload.portfolio_blurb
                        if payload.portfolio_blurb is not None
                        else (payload.summary if payload.summary is not None else current.get("portfolio_blurb", ""))
                    ),
                )
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
                
        return {"data": customization, "error": None}
    
    if payload.summary is None and payload.projects is None and payload.owner is None:
        raise HTTPException(status_code=400, detail="No changes provided")
        
    projects = payload.projects or []
    portfolio = build_portfolio(
        portfolio_id=id,
        owner=payload.owner,
        projects=projects
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
        with _db_session(db_dir) as conn:
            ensure_portfolio_tables(conn)
            ensure_indexes(conn)
            
            if id == "latest":
                rows = fetch_latest_snapshots(conn) or []
                project_ids: list[str] = []
                
                for row in rows:
                    project_id, snapshot = _extract_row_project_and_snapshot(row)
                    if project_id and isinstance(snapshot, dict):
                        project_ids.append(project_id)
                
                entries=get_portfolio_entries(conn, project_ids)
            else:
                entry = get_portfolio_entry(conn, id)
                entries = [entry] if entry else []

        if not entries:
            entries = [
                {
                    "project_id": id,
                    "name": id,
                    "summary": "No snapshot data available.",
                    "source": "placeholder",
                    "template_id": "classic",
                    "images": []
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

@router.get("/{id}")
def read_portfolio_entry(id: str, request: Request) -> dict[str, Any]:
    _check_auth(request)
    _bind_current_user_from_session(request)

    db_dir = _resolve_db_dir(request)
    if not db_dir:
        raise HTTPException(status_code=500, detail="Database not configured")

    with _db_session(db_dir) as conn:
        ensure_portfolio_tables(conn)
        ensure_indexes(conn)
        
        snapshot = helper_get_latest_snapshot(conn, id)
        customization = get_portfolio_customization(conn, id) or {}
        images = list_portfolio_images(conn, id)

    if not snapshot and not customization:
        raise HTTPException(status_code=404, detail="Project portfolio not found")
    
    analysis_defaults = (
        _build_analysis_defaults(id, snapshot)
        if isinstance(snapshot, dict)
        else {
            "key_role": "",
            "evidence_of_success": "",
            "portfolio_blurb": ""
        }
    )
    
    overrides = {
        "key_role": str(customization.get("key_role") or ""),
        "evidence_of_success": str(customization.get("evidence_of_success") or ""),
        "portfolio_blurb": str(customization.get("portfolio_blurb") or "")
    }
    
    resolved = {
        "key_role": overrides["key_role"] or analysis_defaults["key_role"],
        "evidence_of_success": overrides["evidence_of_success"] or analysis_defaults["evidence_of_success"],
        "portfolio_blurb": overrides["portfolio_blurb"] or analysis_defaults["portfolio_blurb"]
    }

    payload = {
        "project_id": id,
        "template_id": str(customization.get("template_id") or "classic"),
        "analysis_defaults": analysis_defaults,
        "overrides": overrides,
        "resolved": resolved,
        "images": images
    }
    
    if isinstance(snapshot, dict):
        payload["title"] = _extract_title(id, snapshot)
        payload["summary"] = _extract_summary(snapshot)
        payload["template_payload"] = (
            _build_template_payload(id, snapshot, customization, images)
            if isinstance(snapshot, dict)
                else {}
)
        
    return {"data": payload, "error": None}


@router.get("/{id}/images")
def read_portfolio_images(id: str, request: Request) -> dict[str, Any]:
    _check_auth(request)
    _bind_current_user_from_session(request)

    db_dir = _resolve_db_dir(request)
    if not db_dir:
        raise HTTPException(status_code=500, detail="Database not configured")

    with _db_session(db_dir) as conn:
        ensure_portfolio_tables(conn)
        ensure_indexes(conn)
        return {"data": {"images": list_portfolio_images(conn, id)}, "error": None}


@router.post("/{id}/images")
async def upload_portfolio_image(
    id: str,
    request: Request,
    file: UploadFile = File(...),
    caption: str = Form(""),
    is_cover: bool = Form(False),
) -> dict[str, Any]:
    _check_auth(request)
    _bind_current_user_from_session(request)

    db_dir = _resolve_db_dir(request)
    if not db_dir:
        raise HTTPException(status_code=500, detail="Database not configured")

    file_bytes = await file.read()

    with _db_session(db_dir) as conn:
        ensure_portfolio_tables(conn)
        ensure_indexes(conn)

        snapshot = helper_get_latest_snapshot(conn, id)
        if not snapshot:
            raise HTTPException(status_code=404, detail="Project not found")

        try:
            image = save_portfolio_image(
                conn,
                project_id=id,
                filename=file.filename or "upload.png",
                file_bytes=file_bytes,
                images_base_dir=_resolve_images_base_dir(request),
                caption=caption,
                make_cover=is_cover,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"data": image, "error": None}


@router.delete("/{id}/images/{image_id}")
def remove_portfolio_image(id: str, image_id: str, request: Request) -> dict[str, Any]:
    _check_auth(request)
    _bind_current_user_from_session(request)

    db_dir = _resolve_db_dir(request)
    if not db_dir:
        raise HTTPException(status_code=500, detail="Database not configured")

    with _db_session(db_dir) as conn:
        ensure_portfolio_tables(conn)
        ensure_indexes(conn)

        deleted = delete_portfolio_image(conn, project_id=id, image_id=image_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Image not found")

    return {"data": {"ok": True}, "error": None}


@router.post("/{id}/images/{image_id}/cover")
def choose_cover_portfolio_image(id: str, image_id: str, request: Request) -> dict[str, Any]:
    _check_auth(request)
    _bind_current_user_from_session(request)

    db_dir = _resolve_db_dir(request)
    if not db_dir:
        raise HTTPException(status_code=500, detail="Database not configured")

    with _db_session(db_dir) as conn:
        ensure_portfolio_tables(conn)
        ensure_indexes(conn)

        updated = set_cover_portfolio_image(conn, project_id=id, image_id=image_id)
        if not updated:
            raise HTTPException(status_code=404, detail="Image not found")

    return {"data": {"ok": True}, "error": None}


@router.post("/{id}/images/reorder")
def reorder_project_portfolio_images(
    id: str,
    payload: ReorderPortfolioImagesRequest,
    request: Request,
) -> dict[str, Any]:
    _check_auth(request)
    _bind_current_user_from_session(request)

    db_dir = _resolve_db_dir(request)
    if not db_dir:
        raise HTTPException(status_code=500, detail="Database not configured")

    with _db_session(db_dir) as conn:
        ensure_portfolio_tables(conn)
        ensure_indexes(conn)

        try:
            images = reorder_portfolio_images(conn, project_id=id, image_ids=payload.image_ids)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"data": {"images": images}, "error": None}


@router.get("/{id}/images/{image_id}/file")
def get_portfolio_image_file(id: str, image_id: str, request: Request):
    _check_auth(request)
    _bind_current_user_from_session(request)

    db_dir = _resolve_db_dir(request)
    if not db_dir:
        raise HTTPException(status_code=500, detail="Database not configured")

    with _db_session(db_dir) as conn:
        ensure_portfolio_tables(conn)
        ensure_indexes(conn)

        row = conn.execute(
            """
            SELECT image_path
            FROM portfolio_images
            WHERE id = ? AND project_id = ?
            """,
            (image_id, id),
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Image not found")

    image_path = Path(row[0])
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Image file missing")

    return FileResponse(image_path)