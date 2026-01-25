from typing import Mapping, Optional
from .top_project_summaries import gather_evidence
from .project_ranking import ProjectRanking


def build_project_insight_prompt(
    snapshot: Mapping[str, object],
    question: str,
    ranking: Optional[ProjectRanking] = None,
) -> str:
    evidence = gather_evidence(snapshot)

    evidence_text = "\n".join(
        f"[{i+1}] {e.detail}"
        for i, e in enumerate(evidence)
    )

    collaboration = snapshot.get("collaboration", {}) or {}
    primary = collaboration.get("primary_contributor", "unknown")

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
        f"- Primary contributor: {primary}\n\n"
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
