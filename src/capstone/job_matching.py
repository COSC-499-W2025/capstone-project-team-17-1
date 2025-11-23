from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Dict, Any, Optional
import math

from .skills import SkillScore  # existing class from skills.py


@dataclass
class ProjectMatch:
    project_id: str
    score: float
    required_coverage: float
    preferred_coverage: float
    keyword_overlap: float
    recency_factor: float
    matched_required: List[str]
    matched_preferred: List[str]
    matched_keywords: List[str]


def _normalise(tokens: Iterable[str]) -> List[str]:
    """
    Normalise a sequence of tokens:
    - strip whitespace
    - lowercase
    - drop empty items
    - deduplicate
    - return sorted list
    """
    return sorted({t.strip().lower() for t in tokens if t and t.strip()})


def _coverage(jd_terms: List[str], project_terms: List[str]) -> tuple[float, List[str]]:
    """
    Simple coverage: how many JD terms appear in project terms.

    Returns:
        (coverage_score, matched_terms)
    """
    if not jd_terms:
        return 0.0, []

    proj_set = set(project_terms)
    matched = [t for t in jd_terms if t in proj_set]
    cov = len(matched) / len(jd_terms)
    return cov, matched


def _recency_factor(recency_days: Optional[float], half_life_days: float = 365.0) -> float:
    """
    Map recency (days since last activity) to [0, 1].

    - 0 days          -> ~1.0
    - half_life_days  -> ~0.5
    - older           -> decays smoothly towards 0

    If recency_days is missing or invalid, return a neutral value of 0.5.
    """
    if recency_days is None or recency_days < 0:
        return 0.5
    # exponential decay: 0.5 ** (days / half_life)
    return math.pow(0.5, recency_days / half_life_days)


def _iter_skill_names(skill_rows: Iterable[Any]) -> List[str]:
    """
    Extract skill names from a heterogeneous list of skill records.

    Supports:
      - SkillScore instances
      - dicts with a "skill" key
      - objects with a .skill attribute
    """
    names: List[str] = []
    for row in skill_rows:
        if isinstance(row, SkillScore):
            names.append(row.skill)
        elif isinstance(row, dict):
            val = row.get("skill")
            if isinstance(val, str):
                names.append(val)
        else:
            val = getattr(row, "skill", None)
            if isinstance(val, str):
                names.append(val)
    return names


def score_project_for_job(
    jd_profile: Dict[str, Any],
    project_snapshot: Dict[str, Any],
    weights: Optional[Dict[str, float]] = None,
) -> ProjectMatch:
    """
    Compute a relevance score between one job description and one project.

    Expects jd_profile to contain:
      - required_skills: list[str]
      - preferred_skills: list[str]
      - keywords: list[str]

    Expects project_snapshot to contain:
      - project_id: str
      - skills: list[SkillScore] or list[dict]/objects with "skill" / .skill
      - metrics.recency_days: optional[float]
    """
    if weights is None:
        weights = {
            "required": 0.6,
            "preferred": 0.2,
            "keywords": 0.1,
            "recency": 0.1,
        }

    # --- JD side ---
    jd_required = _normalise(jd_profile.get("required_skills", []))
    jd_preferred = _normalise(jd_profile.get("preferred_skills", []))
    jd_keywords = _normalise(jd_profile.get("keywords", []))

    # --- Project side: skills from SkillScore list or dict list ---
    raw_skills = project_snapshot.get("skills", []) or []
    proj_skill_terms = _normalise(_iter_skill_names(raw_skills))

    # For now, reuse skills as "keywords". Later we can add tags/descriptions.
    proj_keyword_terms = proj_skill_terms

    # coverage
    required_cov, matched_required = _coverage(jd_required, proj_skill_terms)
    preferred_cov, matched_preferred = _coverage(jd_preferred, proj_skill_terms)
    keyword_ov, matched_keywords = _coverage(jd_keywords, proj_keyword_terms)

    # recency
    metrics = project_snapshot.get("metrics", {}) or {}
    recency_days = metrics.get("recency_days")
    rec_factor = _recency_factor(recency_days)

    # weighted total score
    score = (
        weights["required"] * required_cov
        + weights["preferred"] * preferred_cov
        + weights["keywords"] * keyword_ov
        + weights["recency"] * rec_factor
    )

    return ProjectMatch(
        project_id=str(project_snapshot.get("project_id", "unknown")),
        score=score,
        required_coverage=required_cov,
        preferred_coverage=preferred_cov,
        keyword_overlap=keyword_ov,
        recency_factor=rec_factor,
        matched_required=matched_required,
        matched_preferred=matched_preferred,
        matched_keywords=matched_keywords,
    )


def rank_projects_for_job(
    jd_profile: Dict[str, Any],
    project_snapshots: List[Dict[str, Any]],
    weights: Optional[Dict[str, float]] = None,
) -> List[ProjectMatch]:
    """
    Score all projects and return them sorted best -> worst.
    """
    matches = [
        score_project_for_job(jd_profile, snap, weights=weights)
        for snap in project_snapshots
    ]
    matches.sort(key=lambda m: m.score, reverse=True)
    return matches


def matches_to_json(matches: List[ProjectMatch]) -> Dict[str, Any]:
    """
    Convert a list of ProjectMatch objects into a JSON-friendly dict.
    """
    return {
        "matches": [
            {
                "project_id": m.project_id,
                "score": m.score,
                "required_coverage": m.required_coverage,
                "preferred_coverage": m.preferred_coverage,
                "keyword_overlap": m.keyword_overlap,
                "recency_factor": m.recency_factor,
                "matched_required_skills": m.matched_required,
                "matched_preferred_skills": m.matched_preferred,
                "matched_keywords": m.matched_keywords,
            }
            for m in matches
        ]
    }
