# capstone/resume_generator.py
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, TYPE_CHECKING

from .company_profile import (
    build_company_profile,
    build_company_resume_lines,
)
from .top_project_summaries import export_pdf_one_pager  # re-use simple PDF builder :contentReference[oaicite:1]{index=1}

if TYPE_CHECKING:  # type hints only, no runtime dependency
    from .job_matching import JobMatchResult


# ---------- Data models ----------

@dataclass
class ResumeSkill:
    name: str
    in_required: bool
    in_preferred: bool
    in_company_profile: bool


@dataclass
class ResumeProject:
    project_id: str
    relevance_score: float
    matched_required: List[str]
    matched_preferred: List[str]
    matched_keywords: List[str]
    resume_bullet: str


@dataclass
class TailoredResume:
    company: str
    source: str
    generated_at: str
    skills: List[ResumeSkill]
    projects: List[ResumeProject]
    values: List[str]
    work_style: List[str]
    traits: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Plain JSON-ready dict."""
        return {
            "company": self.company,
            "source": self.source,
            "generated_at": self.generated_at,
            "skills": [asdict(s) for s in self.skills],
            "projects": [asdict(p) for p in self.projects],
            "values": list(self.values),
            "work_style": list(self.work_style),
            "traits": list(self.traits),
        }


# ---------- Helpers ----------

def _build_skill_summary(
    jd_profile: Mapping[str, Any],
    company_profile: Mapping[str, Any],
) -> List[ResumeSkill]:
    """
    Merge skills from:
      - JD required / preferred skills (step 2)
      - company preferred skills from website/profile (step 3)
    into a single list of ResumeSkill rows.
    """
    required = set(jd_profile.get("required_skills") or [])
    preferred = set(jd_profile.get("preferred_skills") or [])
    company_pref = set(company_profile.get("preferred_skills_from_profile") or [])

    universe = sorted(required | preferred | company_pref)

    skills: List[ResumeSkill] = []
    for name in universe:
        skills.append(
            ResumeSkill(
                name=name,
                in_required=name in required,
                in_preferred=name in preferred,
                in_company_profile=name in company_pref,
            )
        )
    return skills


def _normalise_matches(matches: Iterable[Any]) -> List[Any]:
    """
    Convert incoming matches to a list sorted by descending score.
    We only rely on a small interface:
      - project_id
      - score (float)
      - matched_required / matched_preferred / matched_keywords
    """
    items = list(matches)
    items.sort(key=lambda m: float(getattr(m, "score", 0.0)), reverse=True)
    return items


# ---------- Public API ----------

def generate_tailored_resume(
    *,
    company_name: str,
    jd_profile: Mapping[str, Any],
    matches: Sequence["JobMatchResult"] | Sequence[Any],
    company_profile: Optional[Mapping[str, Any]] = None,
    max_projects: int = 3,
) -> TailoredResume:
    """
    Combine step 2 + step 3 outputs into a structured resume object.

    Parameters
    ----------
    company_name:
        Display name of the target company (for bullets + header).
    jd_profile:
        The job-description profile built in step 2
        (should contain required_skills / preferred_skills).
    matches:
        Sequence of JobMatchResult-like objects from step 2.
    company_profile:
        Optional pre-computed profile from build_company_profile().
        If omitted we will call build_company_profile(company_name).
    max_projects:
        Maximum number of top projects to surface.

    Returns
    -------
    TailoredResume
        A structured object that can be converted to JSON or PDF.
    """
    # Step 3: fetch / reuse company profile from website text
    # (this is where values, work style, traits come from).
    if company_profile is None:
        company_profile = build_company_profile(company_name)

    # Step 2: rank matches and build bullets that mention company name.
    ranked_matches = _normalise_matches(matches)
    bullets = build_company_resume_lines(
        company_name=company_name,
        jd_profile=dict(jd_profile),
        matches=ranked_matches,
        max_projects=max_projects,
    )

    projects: List[ResumeProject] = []
    for match, bullet in zip(ranked_matches[:max_projects], bullets):
        projects.append(
            ResumeProject(
                project_id=getattr(match, "project_id", ""),
                relevance_score=float(getattr(match, "score", 0.0)),
                matched_required=list(getattr(match, "matched_required", [])),
                matched_preferred=list(getattr(match, "matched_preferred", [])),
                matched_keywords=list(getattr(match, "matched_keywords", [])),
                resume_bullet=bullet,
            )
        )

    skills = _build_skill_summary(jd_profile, company_profile)

    resume = TailoredResume(
        company=company_profile.get("company", company_name),
        source=str(company_profile.get("source", company_name)),
        generated_at=datetime.now(timezone.utc).isoformat(),
        skills=skills,
        projects=projects,
        values=list(company_profile.get("values", [])),
        work_style=list(company_profile.get("work_style", [])),
        traits=list(company_profile.get("traits", [])),
    )
    return resume


def resume_to_json(resume: TailoredResume) -> Dict[str, Any]:
    """
    Convenience wrapper to go straight to a JSON-serializable dict.
    """
    return resume.to_dict()


def resume_to_pdf(resume: TailoredResume, output_path: Path) -> bytes:
    """
    Render the resume as a professionally formatted PDF using Pandoc.
    """
    from .resume_pdf_builder import build_pdf_with_pandoc

    pdf_path = build_pdf_with_pandoc(resume.to_dict(), output_path)
    return pdf_path.read_bytes()
