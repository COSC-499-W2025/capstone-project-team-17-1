# capstone/company_qualities.py
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, List

<<<<<<< Updated upstream
=======

@dataclass
class CompanyQuery:
    """
    Normalized representation of a user's target company.

    raw_input       - whatever the user typed
    normalized_name - cleaned-up version we will use downstream
    """
    raw_input: str
    normalized_name: str

    def to_json(self) -> dict:
        return asdict(self)


def normalize_company_name(raw: str) -> str:
    """
    Normalize a free-text company name.

    - trim whitespace
    - collapse multiple spaces
    - strip trailing commas/periods
    - drop leading 'the ' (case-insensitive)
    """
    s = " ".join(raw.split())              # collapse internal spaces
    s = s.strip().strip(",. ")             # trim + trailing comma/period

    if s.lower().startswith("the "):
        s = s[4:]

    return s


def build_company_query(user_input: str) -> CompanyQuery:
    """
    Convert raw user input into a CompanyQuery object.
    Frontend / CLI can call this as the first step.
    """
    normalized = normalize_company_name(user_input)
    return CompanyQuery(raw_input=user_input, normalized_name=normalized)

>>>>>>> Stashed changes
# Simple dictionaries of phrases -> normalized qualities.
COMPANY_VALUE_KEYWORDS: Dict[str, List[str]] = {
    "innovation": [
        "innovative",
        "innovation",
        "cutting-edge",
        "disruptive",
        "future focused",
        "forward thinking",
        "pushing boundaries",
    ],
    "customer_focus": [
        "customer obsessed",
        "customer-obsessed",
        "customer focused",
        "customer first",
        "user first",
        "client focused",
        "client centric",
        "customer centric",
    ],
    "diversity": [
        "diverse",
        "diversity",
        "inclusion",
        "inclusive",
        "equity",
        "belonging",
        "equal opportunity",
        "inclusive culture",
    ],
    "ownership": [
        "ownership",
        "take ownership",
        "owner mindset",
        "act like an owner",
        "accountability",
        "own your work",
        "end to end ownership",
    ],
    "learning": [
        "continuous learning",
        "continuous improvement",
        "learn quickly",
        "growth mindset",
        "self directed learning",
        "curiosity",
        "learning culture",
        "lifelong learner",
    ],
    "collaboration": [
        "collaborative",
        "cross functional",
        "cross-functional",
        "teamwork",
        "partner with",
        "work closely with",
        "strong communicator",
        "communication skills",
    ],
    "impact": [
        "make an impact",
        "impactful work",
        "meaningful work",
        "change the world",
        "mission driven",
        "mission driven organization",
    ],
    "integrity": [
        "integrity",
        "ethical",
        "ethics",
        "honesty",
        "do the right thing",
        "trustworthy",
        "transparent",
    ],
    "sustainability": [
        "sustainability",
        "sustainable",
        "environmental",
        "climate",
        "carbon",
        "green initiatives",
    ],
    "excellence": [
        "excellence",
        "high standards",
        "bar raiser",
        "raise the bar",
        "world class",
        "best in class",
    ],
    "results_oriented": [
        "results oriented",
        "results driven",
        "data driven outcomes",
        "deliver results",
        "outcome focused",
        "performance driven",
    ],
    "work_life_balance": [
        "work life balance",
        "wellbeing",
        "well being",
        "mental health support",
        "flexible time off",
    ],
}

WORK_STYLE_KEYWORDS: Dict[str, List[str]] = {
    "remote": [
        "remote",
        "work from home",
        "fully remote",
        "remote first",
        "distributed team",
        "work anywhere",
    ],
    "hybrid": [
        "hybrid",
        "partly remote",
        "few days in office",
        "split between home and office",
    ],
    "onsite": [
        "on-site",
        "on site",
        "in office",
        "office based",
        "campus based",
        "relocation required",
    ],
    "fast_paced": [
        "fast-paced",
        "fast paced",
        "high growth",
        "rapidly growing",
        "dynamic environment",
        "startup like",
        "start up environment",
    ],
    "agile": [
        "agile environment",
        "scrum",
        "kanban",
        "sprint planning",
        "agile ceremonies",
        "stand ups",
    ],
    "collaborative": [
        "cross functional teams",
        "pair programming",
        "collaborative culture",
        "matrixed environment",
    ],
    "mentorship": [
        "mentorship",
        "mentor",
        "coaching",
        "buddy program",
        "learning from senior engineers",
    ],
    "data_driven": [
        "data driven",
        "metrics driven",
        "evidence based",
        "measure outcomes",
    ],
    "flexible_hours": [
        "flexible hours",
        "flexible schedule",
        "flex time",
        "core hours",
    ],
}

# tech skill dict from job_matching
from .job_matching import JOB_SKILL_KEYWORDS


@dataclass
class CompanyQualities:
    company_name: str | None
    values: List[str]
    work_style: List[str]
    preferred_skills: List[str]
    keywords: List[str]  # 👈 MUST exist

    def to_json(self) -> dict:
        return asdict(self)


def _extract_from_dict(text_lower: str, mapping: Dict[str, List[str]]) -> List[str]:
    found: set[str] = set()
    for key, phrases in mapping.items():
        for phrase in phrases:
            if phrase in text_lower:
                found.add(key)
                break
    return sorted(found)


def extract_company_qualities(
    text: str,
    company_name: str | None = None,
) -> CompanyQualities:
    """Extract company values, work style, and preferred skills from raw text."""
    tl = text.lower()

    values = _extract_from_dict(tl, COMPANY_VALUE_KEYWORDS)
    work_style = _extract_from_dict(tl, WORK_STYLE_KEYWORDS)
    preferred_skills = _extract_from_dict(tl, JOB_SKILL_KEYWORDS)

    # combined keyword universe for resume matching
    keywords = sorted(set(values + work_style + preferred_skills))

    return CompanyQualities(
        company_name=company_name,
        values=values,
        work_style=work_style,
        preferred_skills=preferred_skills,
        keywords=keywords,
    )
