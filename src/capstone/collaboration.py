"""Collaboration analysis over git metadata inside the archive."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Iterable


AUTHOR_PATTERN = re.compile(r"^\S+\s+\S+\s+(.+?)\s+<(.+?)>")


@dataclass
class CollaborationSummary:
    classification: str
    contributors: dict[str, int]
    primary_contributor: str | None


def analyze_git_logs(lines: Iterable[str]) -> CollaborationSummary:
    counts: Counter[str] = Counter()
    for line in lines:
        match = AUTHOR_PATTERN.match(line)
        if not match:
            continue
        author = match.group(1).strip()
        if author:
            counts[author] += 1

    if not counts:
        return CollaborationSummary("unknown", {}, None)

    contributor_count = len(counts)
    classification = "individual" if contributor_count == 1 else "collaborative"
    primary_contributor, _ = counts.most_common(1)[0]
    return CollaborationSummary(
        classification=classification,
        contributors=dict(counts),
        primary_contributor=primary_contributor,
    )
