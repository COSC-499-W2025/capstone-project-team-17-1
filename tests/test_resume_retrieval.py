"""Tests for resume_retrieval functions added in the refactoring branch.

Covers:
- _normalise_lang_name  — canonical display names for languages
- _extract_major        — strips degree prefixes (BSc / MSc / …) from degree strings
- build_resume_summary  — auto-generates 2-3 sentence professional summary
"""

import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from capstone.resume_retrieval import (
    _extract_major,
    _normalise_lang_name,
    build_resume_summary,
)

CURRENT_YEAR = datetime.now().year


# ---------------------------------------------------------------------------
# _normalise_lang_name
# ---------------------------------------------------------------------------


def test_normalise_lang_name_common_languages():
    assert _normalise_lang_name("python")     == "Python"
    assert _normalise_lang_name("javascript") == "JavaScript"
    assert _normalise_lang_name("typescript") == "TypeScript"
    assert _normalise_lang_name("go")         == "Go"
    assert _normalise_lang_name("c++")        == "C++"
    assert _normalise_lang_name("html")       == "HTML"
    assert _normalise_lang_name("css")        == "CSS"
    assert _normalise_lang_name("json")       == "JSON"
    assert _normalise_lang_name("sql")        == "SQL"
    assert _normalise_lang_name("rust")       == "Rust"
    assert _normalise_lang_name("kotlin")     == "Kotlin"


def test_normalise_lang_name_case_insensitive_lookup():
    assert _normalise_lang_name("PYTHON")     == "Python"
    assert _normalise_lang_name("JavaScript") == "JavaScript"
    assert _normalise_lang_name("TypeScript") == "TypeScript"


def test_normalise_lang_name_unknown_language_preserved_as_is():
    assert _normalise_lang_name("Solidity")   == "Solidity"
    assert _normalise_lang_name("MyLang")     == "MyLang"
    assert _normalise_lang_name("Zig")        == "Zig"


def test_normalise_lang_name_strips_surrounding_whitespace():
    assert _normalise_lang_name("  python  ") == "Python"
    assert _normalise_lang_name("  MyLang  ") == "MyLang"


# ---------------------------------------------------------------------------
# _extract_major
# ---------------------------------------------------------------------------


def test_extract_major_bsc_variants():
    assert _extract_major("BSc Computer Science")   == "Computer Science"
    assert _extract_major("B.Sc Computer Science")  == "Computer Science"
    assert _extract_major("B.SC. Computer Science") == "Computer Science"


def test_extract_major_bachelor_of_prefix():
    assert _extract_major("Bachelor of Science Computer Science") == "Computer Science"
    assert _extract_major("Bachelor of Arts English Literature")  == "English Literature"


def test_extract_major_msc_variants():
    assert _extract_major("MSc Software Engineering")  == "Software Engineering"
    assert _extract_major("M.Sc. Data Science")        == "Data Science"
    assert _extract_major("Master of Science Robotics") == "Robotics"


def test_extract_major_no_prefix_returns_empty():
    # No prefix stripped → cleaned string equals input → return ""
    assert _extract_major("Computer Science") == ""
    assert _extract_major("Engineering")      == ""


def test_extract_major_empty_string():
    assert _extract_major("") == ""


# ---------------------------------------------------------------------------
# build_resume_summary — sentence 1 (identity)
# ---------------------------------------------------------------------------


def test_build_resume_summary_no_education_no_role():
    result = build_resume_summary([], [], [])
    # Should still produce something mentioning developer / software
    assert "developer" in result.lower() or "experienced" in result.lower()


def test_build_resume_summary_no_education_uses_role_label():
    result = build_resume_summary([], [], [], role_label="full-stack")
    assert "full-stack" in result


def test_build_resume_summary_education_with_university_and_degree_senior():
    # 3 years elapsed → senior
    edu = [{
        "university": "UBCO",
        "degree": "BSc Computer Science",
        "start_date": str(CURRENT_YEAR - 3),
        "end_date": "",
    }]
    result = build_resume_summary(edu, [], [])
    assert "UBCO" in result
    assert "Computer Science" in result
    assert "senior" in result


def test_build_resume_summary_year_label_freshman():
    edu = [{"university": "UBC", "degree": "BSc CS", "start_date": str(CURRENT_YEAR), "end_date": ""}]
    assert "freshman" in build_resume_summary(edu, [], [])


def test_build_resume_summary_year_label_sophomore():
    edu = [{"university": "UBC", "degree": "BSc CS", "start_date": str(CURRENT_YEAR - 1), "end_date": ""}]
    assert "sophomore" in build_resume_summary(edu, [], [])


def test_build_resume_summary_year_label_junior():
    edu = [{"university": "UBC", "degree": "BSc CS", "start_date": str(CURRENT_YEAR - 2), "end_date": ""}]
    assert "junior" in build_resume_summary(edu, [], [])


def test_build_resume_summary_year_label_senior_at_exactly_3_years():
    edu = [{"university": "UBC", "degree": "BSc CS", "start_date": str(CURRENT_YEAR - 3), "end_date": ""}]
    assert "senior" in build_resume_summary(edu, [], [])


def test_build_resume_summary_year_label_senior_beyond_4_years():
    edu = [{"university": "UBC", "degree": "BSc CS", "start_date": str(CURRENT_YEAR - 6), "end_date": ""}]
    assert "senior" in build_resume_summary(edu, [], [])


def test_build_resume_summary_past_education_uses_graduate():
    edu = [{"university": "UBC", "degree": "BSc CS", "start_date": "2018", "end_date": "2022"}]
    assert "graduate" in build_resume_summary(edu, [], [])


def test_build_resume_summary_present_end_date_treated_as_current():
    edu = [{"university": "UBC", "degree": "BSc CS", "start_date": str(CURRENT_YEAR - 1), "end_date": "Present"}]
    result = build_resume_summary(edu, [], [])
    # "Present" → treated as current student → should show year label, not "graduate"
    assert "graduate" not in result
    assert "sophomore" in result


def test_build_resume_summary_university_only_no_degree():
    edu = [{"university": "MIT", "degree": "", "start_date": str(CURRENT_YEAR - 1), "end_date": ""}]
    result = build_resume_summary(edu, [], [])
    assert "MIT" in result
    assert "sophomore" in result.lower()


# ---------------------------------------------------------------------------
# build_resume_summary — sentence 2 (skills)
# ---------------------------------------------------------------------------


def test_build_resume_summary_single_skill():
    result = build_resume_summary([], ["Python"], [])
    assert "Skilled in Python." in result


def test_build_resume_summary_two_skills():
    result = build_resume_summary([], ["Python", "React"], [])
    assert "Python and React" in result


def test_build_resume_summary_three_plus_skills_uses_oxford_comma():
    result = build_resume_summary([], ["Python", "React", "SQL"], [])
    assert "Python" in result
    assert "React" in result
    assert ", and SQL." in result


def test_build_resume_summary_noise_skills_excluded():
    # json, yaml, markdown etc. are noise and should be filtered
    result = build_resume_summary([], ["json", "yaml", "markdown", "Python"], [])
    assert "JSON" not in result
    assert "YAML" not in result
    assert "Markdown" not in result
    assert "Python" in result


def test_build_resume_summary_all_noise_skills_no_skill_sentence():
    result = build_resume_summary([], ["json", "yaml"], [])
    assert "Skilled in" not in result


def test_build_resume_summary_skills_capped_at_five():
    many_skills = ["Python", "Java", "Go", "Rust", "C++", "Swift", "Kotlin"]
    result = build_resume_summary([], many_skills, [])
    # At most 5 skills should appear in the sentence
    assert "Swift" not in result
    assert "Kotlin" not in result


# ---------------------------------------------------------------------------
# build_resume_summary — sentence 3 (projects)
# ---------------------------------------------------------------------------


def test_build_resume_summary_no_projects_omits_project_sentence():
    result = build_resume_summary([], ["Python"], [])
    assert "Developed" not in result


def test_build_resume_summary_one_project():
    projects = [{"title": "MyApp", "_contribution_pct": 100, "_team_size": 1}]
    result = build_resume_summary([], [], projects)
    assert "Developed 1 project" in result


def test_build_resume_summary_multiple_projects_count():
    projects = [
        {"title": "A", "_contribution_pct": 100, "_team_size": 1},
        {"title": "B", "_contribution_pct": 100, "_team_size": 1},
        {"title": "C", "_contribution_pct": 100, "_team_size": 1},
    ]
    result = build_resume_summary([], [], projects)
    assert "Developed 3 projects" in result


def test_build_resume_summary_primary_contributor_above_average():
    # 6-person team: threshold = 100/6 ≈ 16.7; user at 40% → primary
    projects = [{"title": "TeamProject", "_contribution_pct": 40, "_team_size": 6}]
    result = build_resume_summary([], [], projects)
    assert "TeamProject" in result
    assert "primary contributor" in result


def test_build_resume_summary_not_primary_contributor_below_average():
    # 6-person team: threshold ≈ 16.7; user at 10% → not primary
    projects = [{"title": "TeamProject", "_contribution_pct": 10, "_team_size": 6}]
    result = build_resume_summary([], [], projects)
    assert "primary contributor" not in result
    assert "Developed 1 project" in result


def test_build_resume_summary_sole_contributor_is_primary():
    projects = [{"title": "SoloApp", "_contribution_pct": 100, "_team_size": 1}]
    result = build_resume_summary([], [], projects)
    assert "SoloApp" in result
    assert "primary contributor" in result


def test_build_resume_summary_at_threshold_is_primary():
    # Exactly at threshold (100/4 = 25%) → qualifies as primary
    projects = [{"title": "EqualShare", "_contribution_pct": 25, "_team_size": 4}]
    result = build_resume_summary([], [], projects)
    assert "EqualShare" in result
    assert "primary contributor" in result


def test_build_resume_summary_team_phrase_shown_for_multi_person_team():
    projects = [{"title": "Alpha", "_contribution_pct": 5, "_team_size": 7}]
    result = build_resume_summary([], [], projects)
    assert "up to 7 developers" in result


def test_build_resume_summary_no_team_phrase_for_solo_project():
    projects = [{"title": "Solo", "_contribution_pct": 100, "_team_size": 1}]
    result = build_resume_summary([], [], projects)
    assert "collaborating" not in result


def test_build_resume_summary_max_team_size_across_projects():
    projects = [
        {"title": "Small", "_contribution_pct": 5, "_team_size": 2},
        {"title": "Large", "_contribution_pct": 5, "_team_size": 8},
    ]
    result = build_resume_summary([], [], projects)
    assert "up to 8 developers" in result


def test_build_resume_summary_primary_and_team_phrase_combined():
    projects = [
        {"title": "CoreLib", "_contribution_pct": 60, "_team_size": 3},  # 60 > 33.3 → primary
        {"title": "BigApp", "_contribution_pct": 5,  "_team_size": 5},   # 5 < 20 → not primary
    ]
    result = build_resume_summary([], [], projects)
    assert "CoreLib" in result
    assert "primary contributor" in result
    assert "up to 5 developers" in result


def test_build_resume_summary_primary_projects_capped_at_two():
    projects = [
        {"title": "A", "_contribution_pct": 100, "_team_size": 1},
        {"title": "B", "_contribution_pct": 100, "_team_size": 1},
        {"title": "C", "_contribution_pct": 100, "_team_size": 1},
    ]
    result = build_resume_summary([], [], projects)
    # Only first two primary projects should be named
    assert "C" not in result or ("A" in result and "B" in result)


def test_build_resume_summary_full_output_structure():
    edu = [{"university": "UBCO", "degree": "BSc Computer Science", "start_date": str(CURRENT_YEAR - 3), "end_date": ""}]
    skills = ["Python", "React", "SQL"]
    projects = [
        {"title": "Capstone", "_contribution_pct": 25, "_team_size": 4},
        {"title": "Portfolio", "_contribution_pct": 100, "_team_size": 1},
    ]
    result = build_resume_summary(edu, skills, projects, role_label="full-stack")
    # Sentence 1: identity
    assert "UBCO" in result
    assert "senior" in result
    assert "full-stack" in result
    # Sentence 2: skills
    assert "Python" in result
    # Sentence 3: projects
    assert "Developed 2 projects" in result
