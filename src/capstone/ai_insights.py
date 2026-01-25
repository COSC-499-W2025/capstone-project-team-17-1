from pathlib import Path
from typing import Optional

from .storage import open_db, fetch_latest_snapshot
from .project_ranking import rank_projects_from_snapshots
from .llm_client import LLMClient
from .project_insight import build_project_insight_prompt


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

    llm = LLMClient()
    return llm.ask(prompt)
