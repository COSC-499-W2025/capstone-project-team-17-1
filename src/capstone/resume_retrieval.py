from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from .logging_utils import get_logger

logger = get_logger(__name__)


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def build_resume_project_summary(project_id: str, snapshot: Mapping[str, Any]) -> str:
    name = str(snapshot.get("project_name") or snapshot.get("project") or snapshot.get("project_id") or project_id)
    classification = snapshot.get("classification") or snapshot.get("project_type")
    file_summary = snapshot.get("file_summary") if isinstance(snapshot.get("file_summary"), dict) else {}

    file_count = _coerce_int(file_summary.get("file_count"))
    active_days = _coerce_int(file_summary.get("active_days") or file_summary.get("duration_days"))

    languages = snapshot.get("languages") if isinstance(snapshot.get("languages"), dict) else {}
    frameworks = snapshot.get("frameworks") or []
    skills = snapshot.get("skills") or []

    stack_items: List[str] = []
    for name_item in _normalise_list(frameworks):
        stack_items.append(name_item)
    _lang_list = [{"skill": k, "confidence": float(v)} for k, v in languages.items()]
    for name_item in _pick_top_skill_names(_lang_list, limit=2):
        stack_items.append(name_item)
    for name_item in _pick_top_skill_names(skills, limit=2):
        stack_items.append(name_item)

    stack_items = _dedupe_preserve_order(stack_items)
    stack_text = f" using {', '.join(stack_items[:3])}" if stack_items else ""
    if classification:
        opening = f"Built {name}, a {classification} project{stack_text}."
    else:
        opening = f"Built {name}{stack_text}."

    impact_parts: List[str] = []
    if file_count:
        impact_parts.append(f"{file_count} files")
    if active_days:
        impact_parts.append(f"{active_days} active days")
    if impact_parts:
        return f"{opening} Delivered {', '.join(impact_parts)}."
    return opening


def build_resume_project_item(
    project_id: str,
    snapshot: Mapping[str, Any],
    *,
    contributor_name: str = "",
    data_user_id: Optional[int] = None,
    contributor_stats_map: Optional[Mapping[str, Any]] = None,
) -> dict:
    """Return a rich project item dict for resume sections.

    Populates title, subtitle, start_date, end_date, content, and bullets
    from the analysis snapshot, replacing the bare single-sentence summary.
    """
    name = str(snapshot.get("project_name") or snapshot.get("project") or snapshot.get("project_id") or project_id)
    file_summary = snapshot.get("file_summary") if isinstance(snapshot.get("file_summary"), dict) else {}
    collaboration = snapshot.get("collaboration") if isinstance(snapshot.get("collaboration"), dict) else {}

    # Prefer git commit dates (accurate) over ZIP file modification timestamps (unreliable)
    earliest = str(collaboration.get("first_commit_date") or file_summary.get("earliest_modification") or "")
    latest = str(collaboration.get("last_commit_date") or file_summary.get("latest_modification") or "")

    languages = snapshot.get("languages") if isinstance(snapshot.get("languages"), dict) else {}
    frameworks = snapshot.get("frameworks") or []

    # --- subtitle: frameworks first, then top languages, then skills ---
    stack_items: List[str] = []
    for fw in _normalise_list(frameworks):
        stack_items.append(fw)
    _lang_list = [{"skill": k, "confidence": float(v)} for k, v in languages.items()]
    for lang in _pick_top_skill_names(_lang_list, limit=3):
        stack_items.append(lang)
    _raw_skills = snapshot.get("skills") or []
    if isinstance(_raw_skills, dict):
        _raw_skills = [{"skill": k, "confidence": float(v)} for k, v in _raw_skills.items()]
    for sk in _pick_top_skill_names(_raw_skills, limit=3):
        stack_items.append(sk)
    stack_items = _dedupe_preserve_order(stack_items)[:5]
    subtitle = ", ".join(stack_items)

    # --- dates: Mon YYYY (e.g. "Jan 2026") ---
    _MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

    def _to_mon_year(iso: str) -> str:
        try:
            year = int(iso[:4])
            month = int(iso[5:7])
            return f"{_MONTHS[month - 1]} {year}"
        except Exception:
            return ""

    start_date = _to_mon_year(earliest)
    end_date = _to_mon_year(latest)

    # --- role inference from skills ---
    _BACKEND_SKILLS = {"python", "java", "go", "rust", "php", "ruby", "c", "c++",
                       "kotlin", "swift", "scala", "shell", "sql", "r"}
    _FRONTEND_SKILLS = {"javascript", "typescript", "css", "html", "scss", "less",
                        "vue", "svelte"}
    skills_dict = snapshot.get("skills") if isinstance(snapshot.get("skills"), dict) else {}
    # Merge with languages for role detection
    all_skill_keys = {k.lower() for k in list(skills_dict.keys()) + list(languages.keys())}
    _has_backend = bool(all_skill_keys & _BACKEND_SKILLS)
    _has_frontend = bool(all_skill_keys & _FRONTEND_SKILLS)
    if _has_backend and _has_frontend:
        role_label = "full-stack "
    elif _has_backend:
        role_label = "backend "
    elif _has_frontend:
        role_label = "frontend "
    else:
        role_label = ""

    # --- primary language phrase (Template 1) ---
    # Prefer skills dict (ZIP) or languages dict (GitHub), pick top 2 by count
    _skill_counts: List[tuple] = []
    for k, v in skills_dict.items():
        try:
            _skill_counts.append((k, int(v)))
        except Exception:
            pass
    for k, v in languages.items():
        if not any(k == s for s, _ in _skill_counts):
            try:
                _skill_counts.append((k, int(float(v))))
            except Exception:
                pass
    _skill_counts.sort(key=lambda x: -x[1])
    top_langs = [_normalise_lang_name(s) for s, _ in _skill_counts[:2] if s]
    lang_sentence = ""
    if top_langs:
        lang_sentence = f" Primarily built with {' and '.join(top_langs)}."

    # --- contribution stats ---
    # contributor_name (passed in) takes priority; fall back to snapshot's primary_contributor
    _snapshot_primary = str(collaboration.get("primary_contributor") or "")
    target_contributor = contributor_name.strip() or _snapshot_primary

    total_commits = primary_commits = contributor_count = 0
    total_prs = primary_prs = total_issues = primary_issues = total_reviews = primary_reviews = 0
    _has_prs_schema = False

    if contributor_stats_map:
        # contributor_stats table has full GitHub API data (commits + PRs + issues + reviews)
        _has_prs_schema = True
        contributor_count = len(contributor_stats_map)
        for cname, cstats in contributor_stats_map.items():
            c  = _coerce_int(cstats.get("commits"))
            p  = _coerce_int(cstats.get("pull_requests"))
            ii = _coerce_int(cstats.get("issues"))
            rv = _coerce_int(cstats.get("reviews"))
            total_commits += c
            total_prs     += p
            total_issues  += ii
            total_reviews += rv
            # Match by user_id first (reliable), then fall back to name comparison
            uid_set = cstats.get("user_ids") or set()
            is_target = (
                (data_user_id and data_user_id in uid_set)
                or (target_contributor and cname.lower() == target_contributor.lower())
            )
            if is_target:
                primary_commits = c
                primary_prs     = p
                primary_issues  = ii
                primary_reviews = rv
    else:
        # Fall back to snapshot collaboration dict (git-log only: commits + line_changes)
        _prs_key = "contributors (commits, PRs, issues, reviews)"
        _lines_key = "contributors (commits, line changes, reviews)"
        contrib_raw = collaboration.get(_prs_key) or collaboration.get(_lines_key) or {}
        _has_prs_schema = _prs_key in collaboration

        if isinstance(contrib_raw, dict):
            contributor_count = len(contrib_raw)
            for cname, cdata in contrib_raw.items():
                if isinstance(cdata, str):
                    import ast as _ast
                    try:
                        cdata = _ast.literal_eval(cdata)
                    except Exception:
                        cdata = _coerce_int(cdata)
                if isinstance(cdata, (list, tuple)):
                    c  = _coerce_int(cdata[0]) if len(cdata) > 0 else 0
                    p  = _coerce_int(cdata[1]) if len(cdata) > 1 else 0
                    ii = _coerce_int(cdata[2]) if len(cdata) > 2 and _has_prs_schema else 0
                    rv = _coerce_int(cdata[3] if _has_prs_schema else cdata[2]) if len(cdata) > (3 if _has_prs_schema else 2) else 0
                else:
                    c = _coerce_int(cdata)
                    p = ii = rv = 0
                total_commits += c
                total_prs     += p
                total_issues  += ii
                total_reviews += rv
                if target_contributor and cname.lower() == target_contributor.lower():
                    primary_commits = c
                    primary_prs     = p
                    primary_issues  = ii
                    primary_reviews = rv

    # --- contribution sentence ---
    contrib_sentence = ""
    if contributor_count <= 1:
        contrib_sentence = " Sole contributor with 100% contribution."
    elif total_commits:
        if _has_prs_schema:
            _total_activity = total_prs + total_issues + total_reviews
            _primary_activity = primary_prs + primary_issues + primary_reviews
            if _total_activity:
                pct = round(_primary_activity / _total_activity * 100)
            elif primary_commits:
                pct = round(primary_commits / total_commits * 100)
            else:
                pct = round(100 / contributor_count)
        elif primary_commits:
            pct = round(primary_commits / total_commits * 100)
        else:
            pct = round(100 / contributor_count)
        details: List[str] = []
        if _has_prs_schema:
            # GitHub API data: show PRs / issues / reviews
            if total_prs:     details.append(f"{primary_prs}/{total_prs} PRs")
            if total_issues:  details.append(f"{primary_issues}/{total_issues} issues")
            if total_reviews: details.append(f"{primary_reviews}/{total_reviews} reviews")
        else:
            # git-log data: show commits count as the breakdown
            details.append(f"{primary_commits}/{total_commits} commits")
        detail_str = f" ({', '.join(details)})" if details else ""
        _article = "an" if str(contributor_count)[0] in "8" or contributor_count in (11, 18) else "a"
        contrib_sentence = f" Contributed ~{pct}% in {_article} {contributor_count}-person team{detail_str}."

    # --- role sentence (separate, omit if undetected) ---
    if role_label == "full-stack ":
        role_sentence = " Worked as a full-stack developer."
    elif role_label == "backend ":
        role_sentence = " Worked as a backend developer."
    elif role_label == "frontend ":
        role_sentence = " Worked as a frontend developer."
    else:
        role_sentence = ""

    # --- content: professional sentences ---
    if contributor_count <= 1:
        type_label = "individual "
    else:
        type_label = "collaborative "
    content = f"Developed {type_label}project.{lang_sentence}{role_sentence}{contrib_sentence}"

    # --- contribution pct for summary aggregation ---
    if contributor_count <= 1:
        _contrib_pct = 100
    elif _has_prs_schema:
        _total_activity = total_prs + total_issues + total_reviews
        _primary_activity = primary_prs + primary_issues + primary_reviews
        if _total_activity:
            _contrib_pct = round(_primary_activity / _total_activity * 100)
        elif total_commits:
            _contrib_pct = round(primary_commits / total_commits * 100) if primary_commits else round(100 / contributor_count)
        else:
            _contrib_pct = round(100 / contributor_count)
    elif total_commits:
        _contrib_pct = round(primary_commits / total_commits * 100) if primary_commits else round(100 / contributor_count)
    else:
        _contrib_pct = round(100 / contributor_count) if contributor_count else 0

    # --- bullets ---
    bullets: List[str] = []

    return {
        "title": name,
        "subtitle": subtitle,
        "start_date": start_date,
        "end_date": end_date,
        "content": content,
        "bullets": bullets,
        "_contribution_pct": _contrib_pct,
        "_team_size": contributor_count,
    }


def _coerce_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


# Canonical display names for languages (lowercase key → display name).
# Built from language_detection._EXTENSION_LANGUAGE values plus extras.
_LANG_DISPLAY: dict[str, str] = {
    "python": "Python", "javascript": "JavaScript", "typescript": "TypeScript",
    "java": "Java", "ruby": "Ruby", "go": "Go", "rust": "Rust",
    "c": "C", "c++": "C++", "c#": "C#", "swift": "Swift", "kotlin": "Kotlin",
    "objective-c": "Objective-C", "php": "PHP", "html": "HTML", "css": "CSS",
    "scss": "CSS", "markdown": "Markdown", "json": "JSON", "yaml": "YAML",
    "sql": "SQL", "shell": "Shell", "batchfile": "Batchfile",
    "powershell": "PowerShell", "scala": "Scala", "r": "R",
}


_SUMMARY_NOISE_SKILLS = {
    "json", "markdown", "yaml", "batchfile", "powershell", "shell",
    "makefile", "text", "rst", "csv", "xml", "svg",
}

_DEGREE_PREFIX_RE = None  # lazy-compiled


def _extract_major(degree: str) -> str:
    """Strip common degree prefixes (BSc, M.Sc, Bachelor of …) and return the major."""
    import re as _re
    global _DEGREE_PREFIX_RE
    if _DEGREE_PREFIX_RE is None:
        _DEGREE_PREFIX_RE = _re.compile(
            r"^(bachelor\s+of\s+\S+\s*|master\s+of\s+\S+\s*|"
            r"b\.?\s*sc\.?|b\.?\s*a\.?|b\.?\s*eng\.?|b\.?\s*cs\.?|"
            r"m\.?\s*sc\.?|m\.?\s*a\.?|m\.?\s*eng\.?|"
            r"ph\.?\s*d\.?)\s*",
            _re.IGNORECASE,
        )
    cleaned = _DEGREE_PREFIX_RE.sub("", degree.strip()).strip()
    return cleaned if cleaned and cleaned.lower() != degree.strip().lower() else ""


def build_resume_summary(
    education: List[dict],
    skills: List[str],
    projects: List[dict],
    *,
    role_label: str = "",
) -> str:
    """Generate a 2–3 sentence professional summary from available profile data.

    Sentence 1 — identity (degree + university + role, if education available).
    Sentence 2 — top skills.
    Sentence 3 — project count + notable names.
    """
    import re as _re

    parts: List[str] = []

    # ── Sentence 1: identity ─────────────────────────────────────
    edu = education[0] if education else None
    role = role_label.strip().rstrip()
    role_desc = f"{role} development" if role else "software development"

    if edu:
        university = (edu.get("university") or "").strip()
        degree     = (edu.get("degree")     or "").strip()
        end_date   = (edu.get("end_date")   or "").strip().lower()
        start_date = (edu.get("start_date") or "").strip()

        is_current = not end_date or end_date == "present"

        # Infer year label from start_date
        year_label = "student" if is_current else "graduate"
        if is_current and start_date:
            m = _re.search(r"\d{4}", start_date)
            if m:
                elapsed = datetime.now().year - int(m.group())
                year_label = {0: "freshman", 1: "sophomore", 2: "junior", 3: "senior"}.get(elapsed, "senior")

        major = _extract_major(degree) if degree else ""
        label = major or degree

        if label and university:
            s1 = f"{label} {year_label} at {university} with experience in {role_desc}."
        elif university:
            s1 = f"{year_label.capitalize()} at {university} with experience in {role_desc}."
        else:
            s1 = f"Experienced in {role_desc}."
    else:
        role_word = role or "software"
        s1 = f"Experienced {role_word} developer with hands-on project experience."

    parts.append(s1)

    # ── Sentence 2: skills ───────────────────────────────────────
    clean_skills = [s for s in skills if s.lower() not in _SUMMARY_NOISE_SKILLS][:5]
    if clean_skills:
        if len(clean_skills) == 1:
            parts.append(f"Skilled in {clean_skills[0]}.")
        elif len(clean_skills) == 2:
            parts.append(f"Skilled in {clean_skills[0]} and {clean_skills[1]}.")
        else:
            parts.append(
                f"Skilled in {', '.join(clean_skills[:-1])}, and {clean_skills[-1]}."
            )

    # ── Sentence 3: projects ─────────────────────────────────────
    n = len(projects)
    if n > 0:
        max_team = max((p.get("_team_size", 0) for p in projects), default=0)

        # Projects where user contributed above average (>= 100/team_size)
        def _is_primary(p: dict) -> bool:
            pct = p.get("_contribution_pct") or 0
            team = p.get("_team_size") or 1
            return pct >= (100 / team)

        primary_projects = [
            p.get("title", "").strip()
            for p in projects
            if _is_primary(p) and (p.get("title") or "").strip()
        ]

        base = f"Developed {n} project{'s' if n > 1 else ''}"

        primary_phrase = ""
        if primary_projects:
            joined = " and ".join(primary_projects[:2])
            primary_phrase = f"as a primary contributor of {joined}"

        team_phrase = (
            f"collaborating with teams of up to {max_team} developer{'s' if max_team != 1 else ''}"
            if max_team > 1 else ""
        )

        if primary_phrase and team_phrase:
            parts.append(f"{base}, {primary_phrase}, {team_phrase}.")
        elif primary_phrase:
            parts.append(f"{base}, {primary_phrase}.")
        elif team_phrase:
            parts.append(f"{base}, {team_phrase}.")
        else:
            parts.append(f"{base}.")

    return " ".join(parts)


def _normalise_lang_name(name: str) -> str:
    """Return the canonical display name for a language, preserving case for unknowns."""
    return _LANG_DISPLAY.get(name.strip().lower(), name.strip())


def _normalise_list(value: Any) -> List[str]:
    if isinstance(value, list):
        items = value
    elif value is None:
        items = []
    else:
        items = [value]
    results: List[str] = []
    for item in items:
        if item is None:
            continue
        results.append(str(item))
    return results



def _pick_top_skill_names(skills: Any, limit: int = 2) -> List[str]:
    items: List[tuple[str, float]] = []
    if not isinstance(skills, list):
        skills = [] if skills is None else [skills]
    for skill in skills:
        if isinstance(skill, dict):
            name = str(skill.get("skill") or skill.get("name") or "")
            if not name:
                continue
            score = 0.0
            try:
                score = float(skill.get("confidence") or 0.0)
            except Exception:
                score = 0.0
            items.append((name, score))
            continue
        if skill is not None:
            items.append((str(skill), 0.0))
    items.sort(key=lambda item: (-item[1], item[0].lower()))
    return [_normalise_lang_name(name) for name, _ in items[:limit]]


def _dedupe_preserve_order(items: List[str]) -> List[str]:
    seen = set()
    results: List[str] = []
    for item in items:
        key = item.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        results.append(item)
    return results



__all__ = [
    "build_resume_project_summary",
    "build_resume_project_item",
    "build_resume_summary",
]
