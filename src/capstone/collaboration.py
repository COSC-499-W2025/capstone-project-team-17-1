"""Collaboration analysis over git metadata inside the archive."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Iterable


AUTHOR_PATTERN = re.compile(r"^\S+\s+\S+\s+(.+?)\s+<(.+?)>")
# Fallback for plain git log lines: "<hash> Author Name <email>"
AUTHOR_LOG_PATTERN = re.compile(r"^\S+\s+(.+?)\s+<(.+?)>")


def _normalize_email(email: str) -> str:
    lowered = (email or "").strip().lower()
    match = re.match(r"^\d+\+(.+@users\.noreply\.github\.com)$", lowered)
    if match:
        return match.group(1)
    return lowered


def _local_part(email: str) -> str:
    return (email.split("@", 1)[0] if email else "").strip().lower()


@dataclass
class CollaborationSummary:
    classification: str
    contributors: dict[str, int]
    primary_contributor: str | None


def analyze_git_logs(lines: Iterable[str]) -> CollaborationSummary:
    counts: Counter[str] = Counter()
    name_counts: dict[str, Counter[str]] = {}
    local_map: dict[str, str] = {}
    for line in lines:
        match = AUTHOR_PATTERN.match(line) or AUTHOR_LOG_PATTERN.match(line)
        if not match:
            continue
        author = (match.group(1) or "").strip()
        email_raw = (match.group(2) or "").strip()
        email = email_raw.lower()
        normalized_email = _normalize_email(email)
        local = _local_part(normalized_email)
        key = normalized_email or author.lower()
        if normalized_email.endswith("users.noreply.github.com") and local:
            key = f"local:{local}"
        elif local and local in local_map:
            key = local_map[local]
        if not key:
            continue
        if local and local not in local_map:
            local_map[local] = key
        counts[key] += 1
        if key not in name_counts:
            name_counts[key] = Counter()
        if author:
            name_counts[key][author] += 1

    if not counts:
        return CollaborationSummary("unknown", {}, None)

    contributor_count = len(counts)
    classification = "individual" if contributor_count == 1 else "collaborative"
    primary_key, _ = counts.most_common(1)[0]
    primary_name = name_counts.get(primary_key, Counter()).most_common(1)
    primary_contributor = primary_name[0][0] if primary_name else primary_key

    contributors: dict[str, int] = defaultdict(int)
    for key, count in counts.items():
        name = name_counts.get(key, Counter()).most_common(1)
        display_name = name[0][0] if name else key
        contributors[display_name] += count
    return CollaborationSummary(
        classification=classification,
        contributors=dict(contributors),
        primary_contributor=primary_contributor,
    )
