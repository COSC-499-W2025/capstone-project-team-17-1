from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Dict, Any, Optional

import math

from .skills import SkillScore  # existing class from skills.py
from .storage import open_db, fetch_latest_snapshot


# Expand / tweak this as needed
JOB_SKILL_KEYWORDS: Dict[str, List[str]] = {
    # Programming languages
    "python": ["python"],
    "java": ["java"],
    "javascript": ["javascript", "js"],
    "typescript": ["typescript", "ts"],
    "c": [" c ", " c,", " c.", "embedded c"],
    "c++": ["c++", "modern c++"],
    "c#": ["c#", "c sharp"],
    "go": ["golang", " go "],
    "rust": ["rust"],
    "php": ["php"],
    "ruby": ["ruby", "ruby on rails"],
    "swift": ["swift"],
    "kotlin": ["kotlin"],
    "r": [" r ", " r language "],
    "sql": ["sql", "postgres", "postgresql", "mysql", "mariadb", "sql server", "oracle"],
    "bash": ["bash", "shell scripting"],
    "powershell": ["powershell"],

    # Web frontend
    "html": ["html", "html5"],
    "css": ["css", "css3", "scss", "sass"],
    "react": ["react", "react.js", "reactjs"],
    "vue": ["vue", "vue.js", "vuejs"],
    "angular": ["angular", "angular.js", "angularjs"],
    "next.js": ["next.js", "nextjs"],
    "tailwind": ["tailwind", "tailwind css"],

    # Backend and frameworks
    "node.js": ["node", "node.js", "nodejs"],
    "express": ["express", "express.js"],
    "django": ["django"],
    "flask": ["flask"],
    "fastapi": ["fastapi"],
    "spring": ["spring", "spring boot"],
    ".net": [".net", "asp.net", "asp net", "dotnet"],
    "laravel": ["laravel"],
    "rails": ["rails", "ruby on rails"],

    # Data and ML
    "pandas": ["pandas"],
    "numpy": ["numpy"],
    "scikit learn": ["scikit learn", "sklearn"],
    "tensorflow": ["tensorflow"],
    "pytorch": ["pytorch"],
    "machine learning": ["machine learning", "ml engineer"],
    "deep learning": ["deep learning", "neural network"],

    # Cloud and devops
    "aws": ["aws", "amazon web services"],
    "azure": ["azure", "microsoft azure"],
    "gcp": ["gcp", "google cloud"],
    "docker": ["docker", "containerization"],
    "kubernetes": ["kubernetes", "k8s"],
    "ci cd": ["ci cd", "continuous integration", "continuous delivery"],
    "linux": ["linux"],

    # General tools
    "git": ["git", "version control"],
    "github": ["github"],
    "gitlab": ["gitlab"],
    "jira": ["jira"],
    "agile": ["agile", "scrum", "kanban"],
}


@dataclass
class JobMatchResult:
    """
    Simple match result for one project versus one free text job description.
    Used for step 1+2: "do any of our project skills match the JD skills".
    """

    project_id: str
    job_skills: List[str]
    matched_skills: List[Dict[str, Any]]
    missing_skills: List[str]


def extract_job_skills(text: str) -> List[str]:
    """Pull out skills from a raw job description string using JOB_SKILL_KEYWORDS."""
    tl = text.lower()
    found: set[str] = set()
    for skill, variants in JOB_SKILL_KEYWORDS.items():
        for term in variants:
            if term in tl:
                found.add(skill)
                break
    return sorted(found)


def load_project_skills(project_id: str, db_dir: Path | None = None) -> List[Dict[str, Any]]:
    """
    Load the skills list from the latest snapshot for a project.

    This reuses the existing mining pipeline: we just read the JSON snapshot
    that zip_analyzer stored in the database.
    """
    conn = open_db(db_dir)
    snapshot = fetch_latest_snapshot(conn, project_id)
    if not snapshot:
        return []
    return snapshot.get("skills", []) or []


def match_job_to_project(
    job_text: str,
    project_id: str,
    db_dir: Path | None = None,
) -> JobMatchResult:
    """
    Compare a free text job description with one project and return
    which job skills are matched or missing.
    """

    job_skills = extract_job_skills(job_text)
    project_skills = load_project_skills(project_id, db_dir)

    job_set = {s.lower() for s in job_skills}

    matched: List[Dict[str, Any]] = []
    for row in project_skills:
        name = str(row.get("skill", "")).lower()
        if name in job_set:
            matched.append(row)

    matched_names = {row.get("skill", "").lower() for row in matched}
    missing = sorted(job_set - matched_names)

    return JobMatchResult(
        project_id=project_id,
        job_skills=job_skills,
        matched_skills=matched,
        missing_skills=missing,
    )


def build_resume_snippet(match: JobMatchResult) -> str:
    """
    Tiny helper to turn a JobMatchResult into human readable text.
    You can feed this into the UI or into the later resume generator.
    """

    if not match.matched_skills:
        return (
            "For this job posting we could not find strong matches between your "
            "project skills and the required skills. You may want to add more "
            "relevant projects or build new experience for this role."
        )

    lines: List[str] = []
    lines.append("Relevant Skills for this Role:")

    for row in match.matched_skills:
        name = row.get("skill", "Unknown")
        category = row.get("category", "technical")
        confidence = float(row.get("confidence", 0.0))
        lines.append(f"• {name} ({category}, confidence {confidence:.2f})")

    if match.missing_skills:
        lines.append("")
        lines.append("Skills the job mentions that are not clearly shown in this project:")
        for name in match.missing_skills:
            lines.append(f"• {name}")

    return "\n".join(lines)


def has_matching_skills(job_text: str, project_id: str, db_dir: Path | None = None) -> bool:
    """Convenience helper: just yes or no."""
    result = match_job_to_project(job_text, project_id, db_dir)
    return bool(result.matched_skills)


@dataclass
class ProjectMatch:
    project_id: str
    score: float
    required_coverage: float
    preferred_coverage: float
    keyword_overlap: float
    recency_factor: float
    matched_required: List[str]
    matched_preferred: List[str]
    matched_keywords: List[str]


def _normalise(tokens: Iterable[str]) -> List[str]:
    """
    Normalise a sequence of tokens:
      strip whitespace
      lowercase
      drop empty items
      deduplicate
      return sorted list
    """
    return sorted({t.strip().lower() for t in tokens if t and t.strip()})


def _coverage(jd_terms: List[str], project_terms: List[str]) -> tuple[float, List[str]]:
    """
    Simple coverage: how many JD terms appear in project terms.

    Returns:
        (coverage_score, matched_terms)
    """
    if not jd_terms:
        return 0.0, []

    proj_set = set(project_terms)
    matched = [t for t in jd_terms if t in proj_set]
    cov = len(matched) / len(jd_terms)
    return cov, matched


def _recency_factor(recency_days: Optional[float], half_life_days: float = 365.0) -> float:
    """
    Map recency (days since last activity) to [0, 1].

    0 days          -> ~1.0
    half_life_days  -> ~0.5
    older           -> decays smoothly towards 0

    If recency_days is missing or invalid, return a neutral value of 0.5.
    """
    if recency_days is None or recency_days < 0:
        return 0.5
    # exponential decay: 0.5 ** (days / half_life)
    return math.pow(0.5, recency_days / half_life_days)


def _iter_skill_names(skill_rows: Iterable[Any]) -> List[str]:
    """
    Extract skill names from a heterogeneous list of skill records.

    Supports:
      - SkillScore instances
      - dicts with a "skill" key
      - objects with a .skill attribute
    """
    names: List[str] = []
    for row in skill_rows:
        if isinstance(row, SkillScore):
            names.append(row.skill)
        elif isinstance(row, dict):
            val = row.get("skill")
            if isinstance(val, str):
                names.append(val)
        else:
            val = getattr(row, "skill", None)
            if isinstance(val, str):
                names.append(val)
    return names


def score_project_for_job(
    jd_profile: Dict[str, Any],
    project_snapshot: Dict[str, Any],
    weights: Optional[Dict[str, float]] = None,
) -> ProjectMatch:
    """
    Compute a relevance score between one job description and one project.

    Expects jd_profile to contain:
      - required_skills: list[str]
      - preferred_skills: list[str]
      - keywords: list[str]

    Expects project_snapshot to contain:
      - project_id: str
      - skills: list[SkillScore] or list[dict]/objects with "skill" / .skill
      - metrics.recency_days: optional[float]
    """
    if weights is None:
        weights = {
            "required": 0.6,
            "preferred": 0.2,
            "keywords": 0.1,
            "recency": 0.1,
        }

    # JD side
    jd_required = _normalise(jd_profile.get("required_skills", []))
    jd_preferred = _normalise(jd_profile.get("preferred_skills", []))
    jd_keywords = _normalise(jd_profile.get("keywords", []))

    # Project side: skills from SkillScore list or dict list
    raw_skills = project_snapshot.get("skills", []) or []
    proj_skill_terms = _normalise(_iter_skill_names(raw_skills))

    # For now, reuse skills as "keywords".
    proj_keyword_terms = proj_skill_terms

    required_cov, matched_required = _coverage(jd_required, proj_skill_terms)
    preferred_cov, matched_preferred = _coverage(jd_preferred, proj_skill_terms)
    keyword_ov, matched_keywords = _coverage(jd_keywords, proj_keyword_terms)

    metrics = project_snapshot.get("metrics", {}) or {}
    recency_days = metrics.get("recency_days")
    rec_factor = _recency_factor(recency_days)

    score = (
        weights["required"] * required_cov
        + weights["preferred"] * preferred_cov
        + weights["keywords"] * keyword_ov
        + weights["recency"] * rec_factor
    )

    return ProjectMatch(
        project_id=str(project_snapshot.get("project_id", "unknown")),
        score=score,
        required_coverage=required_cov,
        preferred_coverage=preferred_cov,
        keyword_overlap=keyword_ov,
        recency_factor=rec_factor,
        matched_required=matched_required,
        matched_preferred=matched_preferred,
        matched_keywords=matched_keywords,
    )


def rank_projects_for_job(
    jd_profile: Dict[str, Any],
    project_snapshots: List[Dict[str, Any]],
    weights: Optional[Dict[str, float]] = None,
) -> List[ProjectMatch]:
    """Score all projects and return them sorted best to worst."""
    matches = [
        score_project_for_job(jd_profile, snap, weights=weights)
        for snap in project_snapshots
    ]
    matches.sort(key=lambda m: m.score, reverse=True)
    return matches


def matches_to_json(matches: List[ProjectMatch]) -> Dict[str, Any]:
    """Convert a list of ProjectMatch objects into a JSON friendly dict."""
    return {
        "matches": [
            {
                "project_id": m.project_id,
                "score": m.score,
                "required_coverage": m.required_coverage,
                "preferred_coverage": m.preferred_coverage,
                "keyword_overlap": m.keyword_overlap,
                "recency_factor": m.recency_factor,
                "matched_required_skills": m.matched_required,
                "matched_preferred_skills": m.matched_preferred,
                "matched_keywords": m.matched_keywords,
            }
            for m in matches
        ]
    }
