from __future__ import annotations

from typing import Mapping, Sequence
from .code_bundle import BundledFile

def build_deep_review_prompt(
    snapshot: Mapping[str, object],
    question: str,
    files: Sequence[BundledFile],
) -> str:
    file_summary = snapshot.get("file_summary", {}) or {}
    languages = snapshot.get("languages", {}) or {}
    frameworks = snapshot.get("frameworks", []) or []
    collab = snapshot.get("collaboration", {}) or {}

    header = [
        "You are a senior engineer doing a code review and bug investigation.",
        "Return JSON only with keys: summary, bugs, improvements, patch, tests, git_issue.",
        "",
        "Project context derived from metadata.",
        f"File count: {file_summary.get('file_count')}",
        f"Languages: {sorted(list(languages.keys()))}",
        f"Frameworks: {frameworks}",
        f"Collaboration: {collab}",
        "",
        "User question.",
        question.strip(),
        "",
        "Selected source files.",
    ]

    body = []
    for bf in files:
        body.append(f"\nFILE: {bf.path}\nTRUNCATED: {bf.truncated}\nBEGIN\n{bf.text}\nEND\n")

    return "\n".join(header) + "\n".join(body)
