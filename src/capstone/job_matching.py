# capstone/job_matching.py

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

from .storage import open_db, fetch_latest_snapshot

# Simple dictionary of skills and common variants you expect in job posts
# You can grow this over time
JOB_SKILL_KEYWORDS: Dict[str, List[str]] = {
    # Programming languages
    "python": ["python"],
    "java": ["java"],
    "javascript": ["javascript", "js"],
    "typescript": ["typescript", "ts"],
    "c": ["c language", " c ", "embedded c"],
    "c++": ["c++", "modern c++"],
    "c#": ["c#", "c sharp"],
    "go": ["go", "golang"],
    "rust": ["rust"],
    "php": ["php"],
    "ruby": ["ruby", "rails"],
    "swift": ["swift", "ios swift"],
    "kotlin": ["kotlin", "android kotlin"],
    "r": [" r language ", " r studio "],
    "sql": ["sql", "postgres", "postgresql", "mysql", "mariadb", "sql server", "oracle sql"],
    "bash": ["bash", "shell scripting", "shell script"],
    "powershell": ["powershell"],

    # Web frontend
    "html": ["html", "html5"],
    "css": ["css", "css3", "scss", "sass"],
    "react": ["react", "react.js", "reactjs"],
    "vue": ["vue", "vue.js", "vuejs"],
    "angular": ["angular", "angular.js", "angularjs"],
    "next.js": ["next.js", "nextjs"],
    "redux": ["redux"],
    "tailwind": ["tailwind", "tailwind css"],

    # Backend and frameworks
    "node.js": ["node", "node.js", "nodejs"],
    "express": ["express", "express.js"],
    "django": ["django"],
    "flask": ["flask"],
    "fastapi": ["fastapi"],
    "spring": ["spring", "spring boot"],
    ".net": [".net", "dotnet", "asp.net", "asp net"],
    "laravel": ["laravel"],
    "rails": ["rails", "ruby on rails"],
    "graphql": ["graphql"],

    # Data, analytics, machine learning
    "pandas": ["pandas"],
    "numpy": ["numpy"],
    "matplotlib": ["matplotlib"],
    "scikit learn": ["scikit learn", "sklearn"],
    "tensorflow": ["tensorflow"],
    "pytorch": ["pytorch"],
    "machine learning": ["machine learning", "ml models", "ml engineer"],
    "deep learning": ["deep learning", "neural network"],
    "data analysis": ["data analysis", "data analyst", "data analytics"],
    "data engineering": ["data engineering", "etl pipelines", "etl"],
    "power bi": ["power bi"],
    "tableau": ["tableau"],
    "excel": ["excel", "microsoft excel"],

    # Databases and storage
    "relational databases": ["relational database", "rdbms"],
    "nosql": ["nosql", "document store"],
    "mongodb": ["mongodb"],
    "redis": ["redis"],
    "elasticsearch": ["elasticsearch", "elastic search"],
    "firebase": ["firebase"],
    "snowflake": ["snowflake"],

    # Cloud and devops
    "aws": ["aws", "amazon web services"],
    "azure": ["azure", "microsoft azure"],
    "gcp": ["gcp", "google cloud"],
    "docker": ["docker", "containerization"],
    "kubernetes": ["kubernetes", "k8s"],
    "ci cd": ["ci cd", "continuous integration", "continuous delivery"],
    "jenkins": ["jenkins"],
    "github actions": ["github actions"],
    "terraform": ["terraform"],
    "linux": ["linux", "linux administration"],
    "kafka": ["kafka", "apache kafka"],

    # Testing and quality
    "unit testing": ["unit testing", "unit tests"],
    "integration testing": ["integration testing"],
    "pytest": ["pytest"],
    "jest": ["jest"],
    "selenium": ["selenium"],
    "cypress": ["cypress"],

    # Security and infra
    "security": ["application security", "appsec", "secure coding"],
    "oauth": ["oauth", "openid connect"],
    "rest api": ["rest api", "restful api", "rest services"],
    "microservices": ["microservice", "microservices"],

    # General tools and practices
    "git": ["git", "version control"],
    "github": ["github"],
    "gitlab": ["gitlab"],
    "jira": ["jira"],
    "agile": ["agile", "scrum", "kanban"],
    "object oriented design": ["object oriented", "oop"],
    "design patterns": ["design patterns"],
}



@dataclass
class JobMatchResult:
    project_id: str
    job_skills: List[str]
    matched_skills: List[Dict]
    missing_skills: List[str]


def extract_job_skills(text: str) -> List[str]:
    """Pull out skills from a raw job description string."""

    text_lower = text.lower()
    found: set[str] = set()

    for skill, variants in JOB_SKILL_KEYWORDS.items():
        for term in variants:
            if term in text_lower:
                found.add(skill)
                break

    return sorted(found)


def load_project_skills(project_id: str, db_dir: Path | None = None) -> List[Dict]:
    """Load skills list from the latest snapshot for a project."""

    conn = open_db(db_dir)
    snapshot = fetch_latest_snapshot(conn, project_id)
    if not snapshot:
        return []

    # summary JSON from zip_analyzer already has a "skills" list
    return snapshot.get("skills", []) or []


def match_job_to_project(
    job_text: str,
    project_id: str,
    db_dir: Path | None = None,
) -> JobMatchResult:
    """Compare job description skills with project skills."""

    job_skills = extract_job_skills(job_text)
    project_skills = load_project_skills(project_id, db_dir)

    job_set = {s.lower() for s in job_skills}
    matched: List[Dict] = []
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
    """Create a resume style text block for this job match."""

    if not match.matched_skills:
        # zero overlap, be nicer in the real UI than "suck to suck" lol
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

