"""Advanced collaboration analysis utilities."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Sequence

from .collaboration import _normalize_email


@dataclass
class ContributionRecord:
    """Structured contribution information to feed the analysis pipeline."""

    author: str
    email: str
    kind: str = "commit"  # commit, review, other
    commits: int = 0
    reviews: int = 0
    lines: int = 0
    coauthors: Sequence[str] = field(default_factory=list)
    is_bot: bool = False
    shared_account: bool = False


@dataclass
class ContributionSummary:
    classification: str
    primary_contributor: str | None
    human_contributors: Dict[str, int]
    bot_contributors: Dict[str, int]
    scores: Dict[str, float]
    coauthors: Dict[str, List[str]]
    review_totals: Dict[str, int]
    exports: Dict[str, str]
    flags: Dict[str, List[str]]


_BOT_TOKENS = {"bot", "ci", "automation"}


def _is_bot_author(author: str, email: str) -> bool:
    lowered = f"{author} {email}".lower()
    return any(token in lowered for token in _BOT_TOKENS)


def collect_git_contributions(
    raw_entries: Iterable[dict],
    *,
    main_user: str | None = None,
    include_bots: bool = False,
) -> dict[str, object]:
    """Aggregate git contributions while filtering bot accounts."""

    def _key(author: str, email: str) -> str:
        email_key = _normalize_email(email)
        if email_key:
            return email_key
        return (author or "Unknown").strip().lower()

    humans_by_key: Dict[str, int] = {}
    bots_by_key: Dict[str, int] = {}
    display_counts: Dict[str, Dict[str, int]] = {}
    local_map: Dict[str, str] = {}

    for entry in raw_entries:
        author = entry.get("author") or "Unknown"
        email = entry.get("email") or ""
        commits = int(entry.get("commits", 1))
        reviews = int(entry.get("reviews", 0))
        kind = entry.get("kind", "commit")
        score = commits + (reviews if kind == "review" else 0)
        is_bot = entry.get("is_bot") or _is_bot_author(author, email)
        normalized_email = _normalize_email(email)
        local = normalized_email.split("@", 1)[0] if normalized_email else ""
        key = _key(author, email)
        if normalized_email.endswith("users.noreply.github.com") and local:
            key = f"local:{local}"
        elif local and local.lower() in local_map:
            key = local_map[local.lower()]
        if local and local.lower() not in local_map:
            local_map[local.lower()] = key
        if key not in display_counts:
            display_counts[key] = {}
        if author:
            display_counts[key][author] = display_counts[key].get(author, 0) + score

        if is_bot:
            bots_by_key[key] = bots_by_key.get(key, 0) + score
            if not include_bots:
                continue

        if not is_bot:
            humans_by_key[key] = humans_by_key.get(key, 0) + score

    humans: Dict[str, int] = {}
    for key, count in humans_by_key.items():
        names = display_counts.get(key, {})
        name = sorted(names.items(), key=lambda item: (-item[1], item[0]))[0][0] if names else key
        humans[name] = humans.get(name, 0) + count

    bots: Dict[str, int] = {}
    for key, count in bots_by_key.items():
        names = display_counts.get(key, {})
        name = sorted(names.items(), key=lambda item: (-item[1], item[0]))[0][0] if names else key
        bots[name] = bots.get(name, 0) + count

    human_count = len(humans_by_key)
    classification = "unknown"
    if human_count == 0 and bots:
        classification = "bot-only"
    elif human_count == 0:
        classification = "unknown"
    elif human_count == 1:
        classification = "individual"
    else:
        classification = "collaborative"

    primary: str | None = None
    if humans_by_key:
        normalized_main = (main_user or "").strip().lower()
        if normalized_main:
            for key, names in display_counts.items():
                for candidate in names:
                    if candidate.lower() == normalized_main or key == normalized_main:
                        primary = candidate
                        break
                if primary:
                    break
        if not primary:
            primary_key = max(humans_by_key.items(), key=lambda item: item[1])[0]
            names = display_counts.get(primary_key, {})
            primary = sorted(names.items(), key=lambda item: (-item[1], item[0]))[0][0] if names else primary_key

    return {
        "classification": classification,
        "primary_contributor": primary,
        "human_contributors": humans,
        "bot_contributors": bots,
    }


def build_collaboration_analysis(
    raw_entries: Iterable[dict],
    *,
    weights: dict[str, float] | None = None,
    include_bots: bool = False,
    main_user: str | None = None,
) -> ContributionSummary:
    """Produce a rich collaboration summary with weighted scoring and exports."""

    weights = weights or {"commit": 1.0, "review": 0.5, "lines": 0.001}
    humans: Dict[str, int] = {}
    bots: Dict[str, int] = {}
    scores: Dict[str, float] = {}
    coauthors: Dict[str, List[str]] = {}
    review_totals: Dict[str, int] = {}
    flags: Dict[str, List[str]] = {"shared_accounts": []}

    processed: List[ContributionRecord] = []
    bot_scores: Dict[str, float] = {}
    for entry in raw_entries:
        record = ContributionRecord(
            author=entry.get("author", "Unknown"),
            email=entry.get("email", ""),
            kind=entry.get("kind", "commit"),
            commits=int(entry.get("commits", 1)),
            reviews=int(entry.get("reviews", 0)),
            lines=int(entry.get("lines", 0)),
            coauthors=entry.get("coauthors", []) or [],
            is_bot=bool(entry.get("is_bot")),
            shared_account=bool(entry.get("shared", False)),
        )
        if record.shared_account and record.author not in flags["shared_accounts"]:
            flags["shared_accounts"].append(record.author)
        processed.append(record)

        is_bot = record.is_bot or _is_bot_author(record.author, record.email)
        weight = (
            record.commits * weights.get("commit", 1.0)
            + record.reviews * weights.get("review", 0.5)
            + record.lines * weights.get("lines", 0.0)
        )

        if is_bot:
            bots[record.author] = bots.get(record.author, 0) + int(weight)
            bot_scores[record.author] = bot_scores.get(record.author, 0.0) + weight
            if not include_bots:
                continue

        humans[record.author] = humans.get(record.author, 0) + record.commits
        review_totals[record.author] = review_totals.get(record.author, 0) + record.reviews
        coauthors.setdefault(record.author, [])
        for name in record.coauthors:
            if name not in coauthors[record.author]:
                coauthors[record.author].append(name)
        scores[record.author] = scores.get(record.author, 0.0) + weight

    score_sum = sum(scores.values())
    if score_sum > 0:
        for author in list(scores):
            scores[author] = round(scores[author] / score_sum, 4)

    base_summary = collect_git_contributions(
        [r.__dict__ for r in processed],
        main_user=main_user,
        include_bots=include_bots,
    )

    summary = ContributionSummary(
        classification=base_summary["classification"],
        primary_contributor=base_summary["primary_contributor"],
        human_contributors=base_summary["human_contributors"],
        bot_contributors=base_summary["bot_contributors"],
        scores=scores,
        coauthors=coauthors,
        review_totals=review_totals,
        exports={},
        flags=flags,
    )

    csv_export = format_analysis_as_csv(summary, include_bots=include_bots)
    summary.exports["csv"] = csv_export

    return summary


def format_analysis_as_csv(
    analysis: ContributionSummary,
    *,
    include_bots: bool = False,
) -> str:
    """Render the collaboration analysis as a CSV string."""

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["author", "classification", "score", "reviews", "kind"])

    for author, score in analysis.scores.items():
        writer.writerow(
            [
                author,
                analysis.classification,
                score,
                analysis.review_totals.get(author, 0),
                "human",
            ]
        )

    if include_bots:
        for bot_author, count in analysis.bot_contributors.items():
            writer.writerow([bot_author, analysis.classification, count, 0, "bot"])

    return output.getvalue().strip()
