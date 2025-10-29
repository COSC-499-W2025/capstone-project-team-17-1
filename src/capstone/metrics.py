"""Metrics extraction for archive analysis."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable


@dataclass
class FileMetric:
    path: str
    size: int
    modified: datetime
    activity: str


@dataclass
class MetricSummary:
    file_count: int
    total_bytes: int
    earliest_modification: str | None
    latest_modification: str | None
    duration_days: int | None
    active_days: int
    activity_breakdown: dict[str, int]
    timeline: dict[str, int]


def compute_metrics(files: Iterable[FileMetric]) -> MetricSummary:
    file_list = list(files)
    if not file_list:
        return MetricSummary(
            file_count=0,
            total_bytes=0,
            earliest_modification=None,
            latest_modification=None,
            duration_days=None,
            active_days=0,
            activity_breakdown={},
            timeline={}
        )

    total_bytes = sum(file.size for file in file_list)
    sorted_dates = sorted(file.modified for file in file_list)
    earliest = sorted_dates[0]
    latest = sorted_dates[-1]
    duration_days = (latest - earliest).days if latest and earliest else None

    activity_counter: Counter[str] = Counter(file.activity for file in file_list)
    timeline_counter: defaultdict[str, int] = defaultdict(int)
    unique_days = set()

    for file in file_list:
        day_key = file.modified.date().isoformat()
        unique_days.add(day_key)
        month_key = file.modified.strftime("%Y-%m")
        timeline_counter[month_key] += 1

    return MetricSummary(
        file_count=len(file_list),
        total_bytes=total_bytes,
        earliest_modification=earliest.isoformat(),
        latest_modification=latest.isoformat(),
        duration_days=duration_days,
        active_days=len(unique_days),
        activity_breakdown=dict(activity_counter),
        timeline=dict(sorted(timeline_counter.items())),
    )
