from typing import Mapping, Optional
from .top_project_summaries import gather_evidence
from .project_ranking import ProjectRanking


def _infer_user_role(snapshot: Mapping[str, object], user: Optional[str]) -> str:
    """
    Role inference for Issue #138:
    - primary_contributor if user matches primary contributor
    - collaborator if primary contributor exists and user != primary
    - collaborator if user appears in contributors/coauthors (if present)
    - unknown otherwise
    """
    if not user:
        return "unknown"

    def _norm(x: object) -> str:
        return str(x).strip().lower()

    collaboration = snapshot.get("collaboration", {}) or {}
    primary = collaboration.get("primary_contributor")

    # If we know primary contributor, then user is either primary or collaborator.
    if primary and _norm(primary) != "unknown":
        return "primary_contributor" if _norm(primary) == _norm(user) else "collaborator"

    # If primary is missing/unknown, try optional fields.
    contributors = collaboration.get("contributors") or {}
    if isinstance(contributors, dict) and any(_norm(k) == _norm(user) for k in contributors.keys()):
        return "collaborator"

    coauthors = collaboration.get("coauthors") or {}
    # coauthors can be dict or list; handle both
    if isinstance(coauthors, dict):
        # keys might be emails, values might be names/lists — check both
        if any(_norm(k) == _norm(user) for k in coauthors.keys()):
            return "collaborator"
        for v in coauthors.values():
            if isinstance(v, list) and any(_norm(x) == _norm(user) for x in v):
                return "collaborator"
            if isinstance(v, str) and _norm(v) == _norm(user):
                return "collaborator"
    elif isinstance(coauthors, list):
        if any(_norm(x) == _norm(user) for x in coauthors):
            return "collaborator"

    return "unknown"


def infer_user_role(snapshot: Mapping[str, object], user: Optional[str]) -> str:
    """
    Public wrapper for user role inference.
    """
    # Expose a stable helper for API
    return _infer_user_role(snapshot, user)


def build_project_insight_prompt(
    snapshot: Mapping[str, object],
    question: str,
    ranking: Optional[ProjectRanking] = None,
    user: Optional[str] = None,
) -> str:
    evidence = gather_evidence(snapshot)

    evidence_text = "\n".join(f"[{i+1}] {e.detail}" for i, e in enumerate(evidence))

    collaboration = snapshot.get("collaboration", {}) or {}
    primary = collaboration.get("primary_contributor", "unknown")

    user_role = _infer_user_role(snapshot, user)

    file_summary = snapshot.get("file_summary", {}) or {}
    active_days = file_summary.get("active_days", 0)

    languages = snapshot.get("languages", {}) or {}
    frameworks = snapshot.get("frameworks", []) or []

    score_line = (
        f"Project ranking score: {ranking.score:.2f}"
        if ranking
        else "Project ranking score: unavailable"
    )

    return (
        "You are analyzing a software project based on derived metadata.\n\n"
        f"{score_line}\n\n"
        "Ownership:\n"
        f"- Primary contributor: {primary}\n"
        f"- Requesting user's role: {user_role}\n\n"
        "Activity:\n"
        f"- Active days: {active_days}\n\n"
        "Stack:\n"
        f"- Languages: {', '.join(languages.keys()) or 'None'}\n"
        f"- Frameworks: {', '.join(frameworks) or 'None'}\n\n"
        "Evidence:\n"
        f"{evidence_text}\n\n"
        "User question:\n"
        f"{question}\n\n"
        "Instructions:\n"
        "- Answer concisely and technically\n"
        "- Base claims only on the provided evidence\n"
        "- If something cannot be inferred, say so clearly\n"
    )
