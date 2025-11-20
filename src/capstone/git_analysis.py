"""Repository collaboration analysis built from git log --numstat output."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, List

from .collaboration_analysis import build_collaboration_analysis
from .logging_utils import get_logger
from .storage import open_db, store_analysis_snapshot

logger = get_logger(__name__)

GIT_LOG_FORMAT = "commit:%H|%an|%ae|%ct|%s"


@dataclass
class GitEntry:
    sha: str
    author: str
    email: str
    timestamp: int
    subject: str
    lines_added: int
    lines_deleted: int
    files_changed: int
    is_review: bool
    is_shared_account: bool


_SHARED_TOKENS = {"shared", "team", "pair"}


def _is_shared_account(author: str, email: str) -> bool:
    lowered = f"{author} {email}".lower()
    return any(token in lowered for token in _SHARED_TOKENS)


def _parse_git_log_lines(lines: Iterable[str]) -> Iterator[GitEntry]:
    current_metadata = None
    lines_added = 0
    lines_deleted = 0
    files_changed = 0

    for raw_line in lines:
        line = raw_line.rstrip("\n")
        if line.startswith("commit:"):
            if current_metadata is not None:
                yield GitEntry(
                    sha=current_metadata[0],
                    author=current_metadata[1],
                    email=current_metadata[2],
                    timestamp=int(current_metadata[3]),
                    subject=current_metadata[4],
                    lines_added=lines_added,
                    lines_deleted=lines_deleted,
                    files_changed=files_changed,
                    is_review="review" in current_metadata[4].lower(),
                    is_shared_account=_is_shared_account(current_metadata[1], current_metadata[2]),
                )
            payload = line.split(":", 1)[1]
            current_metadata = payload.split("|")
            lines_added = 0
            lines_deleted = 0
            files_changed = 0
            continue

        if line.strip() == "" or current_metadata is None:
            continue

        parts = line.split("\t")
        if len(parts) >= 3:
            add_str, del_str, _ = parts[:3]
            try:
                add = int(add_str) if add_str != "-" else 0
                delete = int(del_str) if del_str != "-" else 0
            except ValueError:
                add = delete = 0
            lines_added += add
            lines_deleted += delete
            files_changed += 1

    if current_metadata is not None:
        yield GitEntry(
            sha=current_metadata[0],
            author=current_metadata[1],
            email=current_metadata[2],
            timestamp=int(current_metadata[3]),
            subject=current_metadata[4],
            lines_added=lines_added,
            lines_deleted=lines_deleted,
            files_changed=files_changed,
            is_review="review" in current_metadata[4].lower(),
            is_shared_account=_is_shared_account(current_metadata[1], current_metadata[2]),
        )


def parse_git_log_stream(stream: str) -> List[dict]:
    """Parse a git log --numstat stream and return contribution dicts."""

    entries: List[dict] = []
    for record in _parse_git_log_lines(stream.splitlines()):
        entry = {
            "author": record.author,
            "email": record.email,
            "commits": 1,
            "lines": record.lines_added + record.lines_deleted,
            "reviews": 1 if record.is_review else 0,
            "kind": "review" if record.is_review else "commit",
            "shared": record.is_shared_account,
        }
        entries.append(entry)
    return entries


def run_git_log(repo_path: Path) -> str:
    """Execute git log --numstat with the expected format and return its output."""

    command = [
        "git",
        "log",
        f"--pretty=format:{GIT_LOG_FORMAT}",
        "--numstat",
    ]
    logger.info("Running git log in %s", repo_path)
    result = subprocess.run(command, cwd=str(repo_path), capture_output=True, text=True, check=True)
    return result.stdout


def analyze_repository(
    repo_path: Path,
    *,
    project_id: str,
    include_bots: bool = False,
    main_user: str | None = None,
    db_dir: Path | None = None,
) -> dict:
    """Analyze a repository, persist the snapshot, and return the summary."""

    stream = run_git_log(repo_path)
    entries = parse_git_log_stream(stream)
    analysis = build_collaboration_analysis(
        entries,
        include_bots=include_bots,
        main_user=main_user,
    )
    snapshot = {
        "project_id": project_id,
        "classification": analysis.classification,
        "primary_contributor": analysis.primary_contributor,
        "human_contributors": analysis.human_contributors,
        "bot_contributors": analysis.bot_contributors,
        "scores": analysis.scores,
        "coauthors": analysis.coauthors,
        "review_totals": analysis.review_totals,
        "exports": analysis.exports,
    }

    conn = open_db(db_dir)
    store_analysis_snapshot(
        conn,
        project_name=project_id,
        classification=analysis.classification,
        primary_contributor=analysis.primary_contributor,
        snapshot=snapshot,
    )
    logger.info("Stored collaboration snapshot for %s", project_id)
    return snapshot


def summarize_to_json(snapshot: dict) -> str:
    """Return a JSON string containing the snapshot (for IPC or API use)."""

    return json.dumps(snapshot, indent=2)


__all__ = [
    "parse_git_log_stream",
    "run_git_log",
    "analyze_repository",
    "summarize_to_json",
    "GitEntry",
]
