from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Mapping, Optional

from .project_ranking import extract_features


@dataclass
class ProjectHealth:
    project_id: str
    score: int
    errors: int
    warnings: int
    last_active_days: Optional[int]
    contribution_ratio: float
    diversity: int
    status: str  # healthy, moderate, critical


def _compute_recency_days(snapshot: Mapping[str, object]) -> Optional[int]:
    file_summary = snapshot.get("file_summary", {}) or {}
    latest = file_summary.get("latest_modification")
    if not latest:
        return None

    try:
        dt = datetime.fromisoformat(latest)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        now = datetime.now(tz=timezone.utc)
        delta = now - dt
        return int(delta.total_seconds() / 86400)
    except Exception:
        return None


def compute_health(
    project_id: str,
    snapshot: Mapping[str, object],
    error_report: Mapping[str, int] | None = None,
) -> ProjectHealth:

    error_report = error_report or {}
    errors = int(error_report.get("errors", 0))
    warnings = int(error_report.get("warnings", 0))

    score = 100

    # Error penalties
    score -= errors * 5
    score -= warnings * 2

    # Recency bonus
    last_active_days = _compute_recency_days(snapshot)
    if last_active_days is not None:
        if last_active_days <= 7:
            score += 5
        elif last_active_days <= 30:
            score += 2

    # Collaboration
    features = extract_features(project_id, snapshot)
    contribution_ratio = features.contribution_ratio

    if contribution_ratio >= 0.9:
        score -= 5
    elif 0.4 <= contribution_ratio <= 0.7:
        score += 3

    # Diversity
    diversity = features.language_diversity
    if diversity >= 3:
        score += 3

    score = max(0, min(100, score))

    if score >= 70:
        status = "healthy"
    elif score >= 40:
        status = "moderate"
    else:
        status = "critical"

    return ProjectHealth(
        project_id=project_id,
        score=score,
        errors=errors,
        warnings=warnings,
        last_active_days=last_active_days,
        contribution_ratio=contribution_ratio,
        diversity=diversity,
        status=status,
    )


def compute_health_for_all(
    snapshots: Dict[str, Mapping[str, object]],
    error_reports: Dict[str, Mapping[str, int]] | None = None,
) -> List[ProjectHealth]:

    results: List[ProjectHealth] = []

    for project_id, snapshot in snapshots.items():
        report = (error_reports or {}).get(project_id)
        health = compute_health(project_id, snapshot, report)
        results.append(health)

    results.sort(key=lambda h: h.score, reverse=True)
    return results