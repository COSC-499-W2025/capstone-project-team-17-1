"""Project ranking utilities based on stored analysis snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional

from .logging_utils import get_logger


logger = get_logger(__name__)


@dataclass
class ProjectFeatureSet:
    """Snapshot-derived features used to compute ranking weights."""

    project_id: str
    artifact_count: int
    total_bytes: int
    latest_modification: Optional[datetime]
    active_days: int
    activity_kinds: int
    language_diversity: int
    contribution_ratio: float


@dataclass
class ProjectRanking:
    project_id: str
    score: float
    breakdown: Dict[str, float]
    details: Dict[str, float]


# Each factor holds equal weight so per-project scores stay easy to interpret when
# we normalise metrics against the current comparison set.
WEIGHTS = {
    "artifact": 0.2,
    "bytes": 0.2,
    "recency": 0.2,
    "activity": 0.2,
    "diversity": 0.2,
}


def _parse_latest_timestamp(value: str | None) -> Optional[datetime]:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:  # pragma: no cover - defensive parsing
        logger.warning("Invalid timestamp encountered during ranking: %s", value)
        return None


def extract_features(
    project_id: str,
    snapshot: Dict[str, object],
    *,
    user: str | None = None,
) -> ProjectFeatureSet:
    """Build a feature set from a stored project snapshot."""

    file_summary = snapshot.get("file_summary", {}) or {}
    artifact_count = int(file_summary.get("file_count", 0) or 0)
    total_bytes = int(file_summary.get("total_bytes", 0) or 0)
    latest_modification = _parse_latest_timestamp(file_summary.get("latest_modification"))
    active_days = int(file_summary.get("active_days", 0) or 0)
    activity_breakdown = file_summary.get("activity_breakdown", {}) or {}

    # Treat languages and frameworks as distinct diversity knobs.
    languages = snapshot.get("languages", {}) or {}
    frameworks = snapshot.get("frameworks", []) or []
    language_diversity = len(languages) + len(frameworks)
    activity_kinds = len(activity_breakdown)

    collaboration = snapshot.get("collaboration", {}) or {}
    contributors = collaboration.get("contributors", {}) or {}
    total_contributions = sum(int(value) for value in contributors.values())
    contribution_ratio = 1.0
    if total_contributions > 0:
        target = None
        if user:
            target = user
        else:
            target = collaboration.get("primary_contributor")
            if not target and contributors:
                target = max(contributors, key=lambda name: contributors[name])
        contribution_ratio = contributors.get(target, 0) / total_contributions if target else 0.0
        if contribution_ratio == 0.0:
            contribution_ratio = 0.1

    # Guarantee a minimum multiplier so sparse data still yields a sortable score.
    # This avoids a user with shared ownership being penalised into a zero-score project.
    contribution_ratio = max(contribution_ratio, 0.1)

    return ProjectFeatureSet(
        project_id=project_id,
        artifact_count=artifact_count,
        total_bytes=total_bytes,
        latest_modification=latest_modification,
        active_days=active_days,
        activity_kinds=activity_kinds,
        language_diversity=language_diversity,
        contribution_ratio=contribution_ratio,
    )


def _normalise(values: Iterable[int]) -> Dict[int, float]:
    values_list = list(values)
    if not values_list:
        return {}
    max_value = max(values_list)
    if max_value <= 0:
        return {value: 0.0 for value in values_list}
    return {value: value / max_value for value in values_list}


def _recency_weight(latest: Optional[datetime], *, now: datetime) -> float:
    # Hyperbolic decay keeps very recent work near 1 while tapering smoothly over time.
    if not latest:
        return 0.0
    delta = now - latest
    days = max(delta.total_seconds() / 86400.0, 0.0)
    return 1.0 / (1.0 + (days / 30.0))


def rank_projects(
    features: List[ProjectFeatureSet],
    *,
    now: Optional[datetime] = None,
) -> List[ProjectRanking]:
    if not features:
        return []

    now = now or datetime.now(tz=timezone.utc)

    # Normalise counts per factor so the weights act as relative importance only.
    artifact_norm = _normalise(feature.artifact_count for feature in features)
    byte_norm = _normalise(feature.total_bytes for feature in features)
    activity_norm = _normalise(feature.active_days for feature in features)
    diversity_metric = [feature.language_diversity + feature.activity_kinds for feature in features]
    diversity_norm = _normalise(diversity_metric)

    rankings: List[ProjectRanking] = []
    for feature, diversity_value in zip(features, diversity_metric):
        recency = _recency_weight(feature.latest_modification, now=now)
        breakdown = {
            "artifact": artifact_norm.get(feature.artifact_count, 0.0),
            "bytes": byte_norm.get(feature.total_bytes, 0.0),
            "recency": recency,
            "activity": activity_norm.get(feature.active_days, 0.0),
            "diversity": diversity_norm.get(diversity_value, 0.0),
        }
        weighted_sum = sum(WEIGHTS[key] * breakdown[key] for key in WEIGHTS)
        score = round(weighted_sum * feature.contribution_ratio, 6)
        details = {
            "artifact_count": float(feature.artifact_count),
            "total_bytes": float(feature.total_bytes),
            "recency_days": (
                0.0
                if not feature.latest_modification
                else max((now - feature.latest_modification).total_seconds() / 86400.0, 0.0)
            ),
            "active_days": float(feature.active_days),
            "diversity_elements": float(diversity_value),
            "contribution_ratio": round(feature.contribution_ratio, 4),
        }
        rankings.append(ProjectRanking(project_id=feature.project_id, score=score, breakdown=breakdown, details=details))

    rankings.sort(key=lambda record: record.score, reverse=True)
    return rankings


def rank_projects_from_snapshots(
    snapshots: Dict[str, Dict[str, object]],
    *,
    user: str | None = None,
    now: Optional[datetime] = None,
) -> List[ProjectRanking]:
    features = [extract_features(project_id, snapshot, user=user) for project_id, snapshot in snapshots.items()]
    return rank_projects(features, now=now)


__all__ = [
    "WEIGHTS",
    "ProjectFeatureSet",
    "ProjectRanking",
    "extract_features",
    "rank_projects",
    "rank_projects_from_snapshots",
]
