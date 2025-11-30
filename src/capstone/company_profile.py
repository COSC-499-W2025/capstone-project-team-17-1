from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from urllib.request import urlopen
from urllib.error import URLError, HTTPError

from capstone.job_matching import extract_job_skills

# softskills dictionary
TRAIT_KEYWORDS: Dict[str, List[str]] = {
    "teamwork": ["teamwork", "team player", "collaboration", "collaborative"],
    "communication": ["strong communication", "communication skills", "communicator"],
    "ownership": ["ownership", "takes initiative", "self starter"],
    "leadership": ["leadership", "mentor", "coaching"],
    "problem solving": ["problem solving", "analytical", "critical thinking"],
    "adaptability": ["fast paced environment", "adaptable", "fast-paced"],
    "quality mindset": ["best practices", "clean code", "testing culture", "quality focused"],
}

# extract softskills
def extract_softskills(text: str) -> List[str]:
    tl = text.lower()
    found: set[str] = set()
    for trait, phrases in TRAIT_KEYWORDS.items():
        for phrase in phrases:
            if phrase in tl:
                found.add(trait)
                break
    return sorted(found)

# find possible company urls based on user inputted company name
def _guess_company_urls(company_name: str) -> List[str]:
    slug = company_name.lower().replace(" ", "")
    bases = [f"https://{slug}.com", f"https://{slug}.co", f"https://{slug}.io"]

    urls: List[str] = []
    for base in bases:
        urls.append(base)
        urls.append(base + "/careers")
        urls.append(base + "/jobs")
        urls.append(base + "/about")

    # remove duplicates but keep ordered
    seen: set[str] = set()
    unique: List[str] = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            unique.append(u)
    return unique

# fetch url page
def _http_get(url: str, timeout: int = 8) -> Optional[str]:
    try:
        with urlopen(url, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except (URLError, HTTPError):
        return None

# convert html format to text for parsing
def _html_to_text(raw: str) -> str:
    # remove script and style blocks
    no_script = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw, flags=re.DOTALL | re.IGNORECASE)
    # remove all tags
    text = re.sub(r"<[^>]+>", " ", no_script)
    # remove whitespace
    text = re.sub(r"\s+", " ", text)
    return text.strip()

# plain text of all fetched info
def fetch_company_text(company_name: str) -> str:
    urls = _guess_company_urls(company_name)
    chunks: List[str] = []

    for url in urls:
        raw = _http_get(url)
        if not raw:
            continue
        if "<html" in raw.lower():
            chunks.append(_html_to_text(raw))
        else:
            chunks.append(raw)

    return "\n\n".join(chunks)

# builds profile for company
def build_company_jd_profile(company_name: str) -> Dict[str, Any]:
    text = fetch_company_text(company_name)
    if not text.strip():
        return {
            "required_skills": [],
            "preferred_skills": [],
            "keywords": [],
        }

    skills = extract_job_skills(text)
    traits = extract_traits(text)

    # treat all detected skills as required and preferred so it stays simple
    required_skills = skills
    preferred_skills = skills

    # keywords = skills + traits
    keywords = sorted(set(skills + traits))

    return {
        "required_skills": required_skills,
        "preferred_skills": preferred_skills,
        "keywords": keywords,
    }

# convert matched traits into resume bullet points
def build_company_resume_bullets(
    company_name: str,
    jd_profile: Dict[str, Any],
    matches: List[Any],
    max_projects: int = 3,
    max_skills_per_project: int = 4,
) -> List[str]:

    bullets: List[str] = []

    company_skills = jd_profile.get("required_skills") or jd_profile.get("preferred_skills") or []
    company_skills = list(dict.fromkeys(company_skills))  # dedupe

    for m in matches[:max_projects]:
        # collect all matched skills for this project
        raw = list(getattr(m, "matched_required", [])) \
            + list(getattr(m, "matched_preferred", [])) \
            + list(getattr(m, "matched_keywords", []))

        proj_skills = list(dict.fromkeys(raw))
        if not proj_skills:
            continue

        main_skills = proj_skills[:max_skills_per_project]

        # show focused skills
        focus = company_skills[:3]
        focus_part = ""
        if focus:
            focus_part = f", aligning with {company_name}'s focus on " + ", ".join(focus)

        if len(main_skills) > 1:
            skills_part = ", ".join(main_skills[:-1]) + f" and {main_skills[-1]}"
        else:
            skills_part = main_skills[0]

        bullet = f"• Built {m.project_id} using {skills_part}{focus_part}."
        bullets.append(bullet)

    return bullets
