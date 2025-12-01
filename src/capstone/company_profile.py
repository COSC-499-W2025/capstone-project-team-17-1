from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

from capstone.job_matching import extract_job_skills
from capstone.company_qualities import extract_company_qualities  # 👈 new import

# softskills dictionary
TRAIT_KEYWORDS: Dict[str, List[str]] = {
    "teamwork": ["teamwork", "team player", "collaboration", "collaborative"],
    "communication": ["communication", "strong communication", "communication skills", "communicator"],
    "ownership": ["ownership", "takes initiative", "self starter"],
    "leadership": ["leadership", "mentor", "coaching"],
    "problem solving": ["problem solving", "analytical", "critical thinking"],
    "adaptability": ["fast paced environment", "adaptable", "fast-paced"],
    "company culture": ["best practices", "clean code", "testing culture", "quality focused"],
}

# helper for defining word boundaries for safer matching
def _contains_term(text_lower: str, term: str) -> bool:
    term = term.strip().lower()
    if not term:
        return False

    if " " in term:
        return term in text_lower

    pattern = r"\b" + re.escape(term) + r"\b"
    return re.search(pattern, text_lower) is not None


# extract softskills
def extract_softskills(text: str) -> List[str]:
    tl = text.lower()
    found: set[str] = set()
    for trait, phrases in TRAIT_KEYWORDS.items():
        for phrase in phrases:
            if _contains_term(tl, phrase):
                found.add(trait)
                break
    return sorted(found)


# find possible company urls based on user inputted company name
# NOTE: this can probably be removed as development continues since it's not as
# consistent as using an input url
def _find_company_urls(company_name: str) -> List[str]:
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


# get data if user inputted a company url
def fetch_from_url(url: str) -> str:
    rawData = _http_get(url)
    if not rawData:
        return ""
    if "<html" in rawData.lower():
        return _html_to_text(rawData)
    return rawData


# fetch url page
def _http_get(url: str, timeout: int = 8) -> Optional[str]:
    try:
        req = Request(url, headers={"User-Agent": "capstone-company-profile/1.0"})
        with urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except (URLError, HTTPError):
        print(f"Failed to fetch data from {url} :(")
        return None


# convert html format to text for parsing
def _html_to_text(raw: str) -> str:
    # remove script and style blocks
    no_script = re.sub(
        r"<(script|style)[^>]*>.*?</\1>",
        " ",
        raw,
        flags=re.DOTALL | re.IGNORECASE,
    )
    # remove all tags
    text = re.sub(r"<[^>]+>", " ", no_script)
    # remove whitespace
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# plain text of all fetched info
def fetch_company_text(company_name: str) -> str:
    urls = _find_company_urls(company_name)
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
def build_company_profile(company_name: str, url: str | None = None) -> Dict[str, Any]:
    # fetch raw text either from an explicit URL or by guessing company URLs
    if url:
        text = fetch_from_url(url)
        source = url
    else:
        text = fetch_company_text(company_name)
        source = company_name

    if not text.strip():
        # empty structured JSON – safe default for resume matching
        return {
            "company": company_name,
            "source": source,
            "required_skills": [],
            "preferred_skills": [],
            "keywords": [],
            "values": [],
            "work_style": [],
            "traits": [],
            "preferred_skills_from_profile": [],
        }

    # base technical skills + soft skills
    base_skills = list(dict.fromkeys(extract_job_skills(text)))  # dedupe, keep order
    traits = extract_softskills(text)

    # higher-level company qualities (values, work style, preferred_skills, keywords)
    qualities = extract_company_qualities(text, company_name=company_name)

    # keep existing behaviour: treat all detected skills as required + preferred
    required_skills = base_skills
    preferred_skills = base_skills

    # combined keyword universe for matching (tech + traits + qualities)
    keywords = sorted(set(base_skills + traits + qualities.keywords))

    return {
        # meta
        "company": company_name,
        "source": source,
        # core matching inputs (backwards-compatible)
        "required_skills": required_skills,
        "preferred_skills": preferred_skills,
        "keywords": keywords,
        # extra structured qualities for smarter matching / UI
        "values": qualities.values,
        "work_style": qualities.work_style,
        "traits": traits,
        "preferred_skills_from_profile": qualities.preferred_skills,
    }


# helper for consistent bullet point formatting
def _format_lines(s: str) -> str:
    lowercase = s.lower()
    if lowercase in {"aws", "gcp", "gcs"}:
        return lowercase.upper()
    if lowercase == "sql":
        return "SQL"
    return s.capitalize()


# convert matched traits into resume bullet points
def build_company_resume_lines(
    company_name: str,
    jd_profile: Dict[str, Any],
    matches: List[Any],
    max_projects: int = 3,
    max_skills_per_project: int = 4,
) -> List[str]:
    points: List[str] = []

    company_skills = (
        jd_profile.get("required_skills")
        or jd_profile.get("preferred_skills")
        or []
    )
    company_skills = list(dict.fromkeys(company_skills))  # dedupe

    for m in matches[:max_projects]:
        # collect all matched skills for this project
        raw = (
            list(getattr(m, "matched_required", []))
            + list(getattr(m, "matched_preferred", []))
            + list(getattr(m, "matched_keywords", []))
        )

        proj_skills = list(dict.fromkeys(raw))
        if not proj_skills:
            continue

        main_skills = [
            _format_lines(s) for s in proj_skills[:max_skills_per_project]
        ]

        # show focused company skills (up to 3)
        focus = [_format_lines(s) for s in company_skills[:3]]
        focus_part = ""
        if focus:
            focus_part = (
                f", aligning with {company_name}'s focus on " + ", ".join(focus)
            )

        if len(main_skills) > 1:
            skills_part = ", ".join(main_skills[:-1]) + f" and {main_skills[-1]}"
        else:
            skills_part = main_skills[0]

        line = (
            f"- Built {m.project_id} using {skills_part}"
            f"{focus_part}"
            f" to deliver production-ready features for {company_name}."
        )

        points.append(line)

    return points
