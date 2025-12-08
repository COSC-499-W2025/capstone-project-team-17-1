"""Skill scoring utilities for dynamic confidence calculations and timelines."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Iterable, List, Tuple


@dataclass(frozen=True)
class SkillObservation:
    skill: str
    weight: float
    category: str = "technical"


@dataclass
class SkillScore:
    skill: str
    confidence: float
    category: str


def compute_skill_scores(
    observations: Iterable[SkillObservation],
    *,
    min_confidence: float = 0.05,
) -> List[SkillScore]:
    """Aggregate observations into normalized confidence values."""

    totals: dict[str, tuple[float, str]] = {}
    total_weight = 0.0

    for obs in observations:
        if obs.weight <= 0:
            continue
        total_weight += obs.weight
        current_weight, category = totals.get(obs.skill, (0.0, obs.category))
        totals[obs.skill] = (current_weight + obs.weight, category)

    if total_weight == 0:
        return []

    scores = [
        SkillScore(skill=skill, confidence=weight / total_weight, category=category)
        for skill, (weight, category) in totals.items()
        if (weight / total_weight) >= min_confidence
    ]

    scores.sort(key=lambda score: (-score.confidence, score.skill))
    return scores


def drop_under_threshold(rows: Iterable[SkillScore], threshold: float) -> List[SkillScore]:
    """Filter out scores whose confidence is below the threshold."""

    return [row for row in rows if row.confidence >= threshold]


def build_skill_timeline(events: Iterable[Tuple[str, str, datetime, float]]) -> Dict[str, Dict[str, object]]:
    """
    aggregate skill, category, timestamp, weight into
    first/last seen metadata plus per-year and per-quarter counts
    returns a mapping of skill -> timeline payload ready for export
    """
    buckets: Dict[str, Dict[str, object]] = {}
    for skill, category, ts, weight in events:
        if not skill or ts is None:
            continue
        if isinstance(ts, str):
            try:
                ts = datetime.fromisoformat(ts)
            except ValueError:
                continue
        entry = buckets.setdefault(
            skill,
            {
                "skill": skill,
                "category": category or "unspecified",
                "first_seen": None,
                "last_seen": None,
                "total_weight": 0.0,
                "year_counts": defaultdict(float),
                "quarter_counts": defaultdict(float),
            },
        )
        entry["total_weight"] += float(weight or 0)
        entry["first_seen"] = ts.isoformat() if not entry["first_seen"] or ts.isoformat() < entry["first_seen"] else entry["first_seen"]
        entry["last_seen"] = ts.isoformat() if not entry["last_seen"] or ts.isoformat() > entry["last_seen"] else entry["last_seen"]
        year_key = str(ts.year)
        quarter_key = f"{ts.year}-Q{((ts.month - 1) // 3) + 1}"
        entry["year_counts"][year_key] += float(weight or 0)
        entry["quarter_counts"][quarter_key] += float(weight or 0)

    if not buckets:
        return {}

    max_weight = max(v["total_weight"] for v in buckets.values()) or 1.0
    for entry in buckets.values():
        # Normalize intensity between 0 and 1 based on total weight.
        entry["intensity"] = entry["total_weight"] / max_weight
        entry["year_counts"] = dict(sorted(entry["year_counts"].items()))
        entry["quarter_counts"] = dict(sorted(entry["quarter_counts"].items()))
    return buckets


__all__ = [
    "SkillObservation",
    "SkillScore",
    "compute_skill_scores",
    "drop_under_threshold",
    "build_skill_timeline",
]
