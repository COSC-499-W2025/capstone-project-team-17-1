from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, List

from capstone.project_detection import detect_node_electron_project
from capstone.job_matching import rank_projects_for_job as match_projects_to_jobs
from capstone.company_profile import build_company_profile
from capstone.company_qualities import extract_company_qualities


# Step 4 will later fill this in
# from capstone.resume_generator import generate_resume_json   # placeholder


def _detect_projects_wrapper(projects_dir: str) -> List[Dict[str, Any]]:
    """
    Thin wrapper around detect_node_electron_project so the pipeline
    can treat 'projects' as a list of project snapshots.

    For now, we assume projects_dir points at a single Node/Electron project.
    We fabricate a minimal project_snapshot structure that
    score_project_for_job / rank_projects_for_job can work with.
    """
    root = Path(projects_dir)
    is_project, summary = detect_node_electron_project(root)

    # Minimal project snapshot the matching code can handle:
    # - project_id: str
    # - skills: list[...]  (empty for now)
    # - metrics: dict      (empty for now)
    return [
        {
            "project_id": root.name,
            "root": str(root),
            "is_project": is_project,
            "summary": summary,
            "skills": [],     # no mined skills yet
            "metrics": {},    # no recency info yet
        }
    ]


def run_full_pipeline(
    company_name: str,
    company_url: str | None,
    projects_dir: str,
) -> Dict[str, Any]:
    """
    Integrates Steps 1–4 into a single pipeline.

    For now (while Step 4 is not implemented), this returns an
    intermediate JSON bundle with:
      - detected projects (from project_detection)
      - job matching results (from job_matching.rank_projects_for_job)
      - company profile (from company_profile.build_company_profile)
      - company qualities (from company_qualities.extract_company_qualities)
    """

    # --- STEP 1: User Portfolio / Project Detection ---
    project_snapshots = _detect_projects_wrapper(projects_dir)

    # --- STEP 2: Match Projects to Company Job Listing ---
    company_profile = build_company_profile(company_name, company_url)
    matches = match_projects_to_jobs(
        jd_profile=company_profile,
        project_snapshots=project_snapshots,
    )

    # --- STEP 3: Extract Company Qualities (values, style, preferred skills) ---
    text = "\n".join(company_profile["keywords"])
    qualities = extract_company_qualities(text, company_name)

    # --- STEP 4: Generate Resume JSON (to be implemented later) ---
    # resume_json = generate_resume_json(
    #     company_profile=company_profile,
    #     qualities=qualities,
    #     matches=matches,
    #     projects=project_snapshots,
    # )

    # Temporary integration output
    return {
        "company": company_name,
        "projects": project_snapshots,
        "matches": [m.__dict__ for m in matches],
        "company_profile": company_profile,
        "company_qualities": qualities.to_json(),
        # "resume": resume_json,  # will be added once Step 4 is ready
    }


if __name__ == "__main__":
    # TODO: replace this with the actual path where your sample project lives
    demo_projects_dir = "demo_db"  # e.g. "demo/projects" or some local Node project

    result = run_full_pipeline(
        company_name="McDonalds",
        company_url=None,
        projects_dir=demo_projects_dir,
    )
    print(json.dumps(result, indent=2))
