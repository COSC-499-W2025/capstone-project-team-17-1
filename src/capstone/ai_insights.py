from pathlib import Path
from typing import Optional, Iterable

from .storage import open_db, fetch_latest_snapshot
from .project_ranking import rank_projects_from_snapshots
from .llm_client import LLMClient
from .project_insight import build_project_insight_prompt
from .consent import ensure_external_permission, ExternalPermissionDenied
from .llm_client import OpenAILlmClient, build_default_llm
from .code_bundle import bundle_code_from_zip
from .deep_review_prompt import build_deep_review_prompt

def ask_deep_review_question(
    project_id: str,
    question: str,
    zip_path: Path,
    include_paths: Iterable[str],
    db_dir: Optional[Path] = None,
    llm: Optional[OpenAILlmClient] = None,
) -> str:
    conn = open_db(db_dir)
    snapshot = fetch_latest_snapshot(conn, project_id)
    if not snapshot:
        raise ValueError(f"No snapshot found for project '{project_id}'")

    files = bundle_code_from_zip(zip_path, include_paths)
    prompt = build_deep_review_prompt(snapshot, question, files)

    try:
        ensure_external_permission(
            service="llm",
            data_types=[
                "project metadata",
                "derived evidence",
                "user selected source code snippets",
            ],
            purpose="Generate AI based code review and bug investigation",
            destination="OpenAI API",
            privacy="Only user selected files are sent. Lines that look like secrets are redacted.",
            source="ai_insights",
        )
    except ExternalPermissionDenied:
        return (
            "[Offline Summary]\n\n"
            "Deep analysis was skipped because external LLM access was not authorized. "
            "You can still use local snapshot metrics and project summaries."
        )

    client = llm or build_default_llm()
    if not client:
        return (
            "[Offline Summary]\n\n"
            "Deep analysis was skipped because the OpenAI client is not configured. "
            "Set OPENAI_API_KEY to enable this feature."
        )

    return client.generate_summary(prompt)

def ask_project_question(
    project_id: str,
    question: str,
    db_dir: Optional[Path] = None,
) -> str:
    conn = open_db(db_dir)
    snapshot = fetch_latest_snapshot(conn, project_id)

    if not snapshot:
        raise ValueError(f"No snapshot found for project '{project_id}'")

    rankings = rank_projects_from_snapshots({project_id: snapshot})
    ranking = rankings[0] if rankings else None

    prompt = build_project_insight_prompt(snapshot, question, ranking)

    # Gate LLM usage behind consent
    try:
        ensure_external_permission(
            service="llm",
            data_types=["project metadata", "derived evidence"],
            purpose="Generate AI-based project insights",
            destination="OpenAI API",
            source="ai_insights",
        )
    except ExternalPermissionDenied:
        # Graceful offline fallback
        return (
            "[Offline Summary]\n\n"
            "AI-based analysis was skipped because external LLM access was not authorized. "
            "The project summary and insights remain available through offline analysis "
            "and deterministic metrics."
        )

    llm = LLMClient()
    return llm.ask(prompt)
