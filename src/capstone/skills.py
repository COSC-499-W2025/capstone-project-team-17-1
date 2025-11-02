"""Skill scoring utilities for dynamic confidence calculations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List


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


__all__ = [
    "SkillObservation",
    "SkillScore",
    "compute_skill_scores",
    "drop_under_threshold",
]
