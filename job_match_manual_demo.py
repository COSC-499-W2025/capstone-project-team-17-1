from __future__ import annotations

import capstone
from capstone.job_matching import rank_projects_for_job
from capstone.skills import SkillScore

print("DEBUG: running job_match_manual_demo.py")
print("DEBUG: capstone loaded from:", capstone.__file__)

def main() -> None:
    print("DEBUG: inside main()")

    jd_profile = {
        "title": "Backend Python Intern",
        "required_skills": ["python", "flask", "sql"],
        "preferred_skills": ["docker", "linux"],
        "keywords": ["backend", "rest api"],
    }

    project_snapshots = [
        {
            "project_id": "flask_backend",
            "skills": [
                SkillScore("python", 0.5, "language"),
                SkillScore("flask", 0.3, "framework"),
                SkillScore("sql", 0.2, "database"),
            ],
            "metrics": {"recency_days": 30},
        },
        {
            "project_id": "data_science_notebook",
            "skills": [
                SkillScore("python", 0.7, "language"),
                SkillScore("pandas", 0.3, "library"),
            ],
            "metrics": {"recency_days": 5},
        },
        {
            "project_id": "old_php_site",
            "skills": [
                SkillScore("php", 0.8, "language"),
                SkillScore("mysql", 0.2, "database"),
            ],
            "metrics": {"recency_days": 800},
        },
    ]

    matches = rank_projects_for_job(jd_profile, project_snapshots)

    print("\\n=== Job:", jd_profile["title"], "===\\n")
    for m in matches:
        print(f"Project: {m.project_id}")
        print(f"  Total score:        {m.score:.3f}")
        print(f"  Required coverage:  {m.required_coverage:.3f}")
        print(f"  Preferred coverage: {m.preferred_coverage:.3f}")
        print(f"  Keyword overlap:    {m.keyword_overlap:.3f}")
        print(f"  Recency factor:     {m.recency_factor:.3f}")
        print(f"  Matched required:   {m.matched_required}")
        print(f"  Matched preferred:  {m.matched_preferred}")
        print(f"  Matched keywords:   {m.matched_keywords}")
        print()

if __name__ == "__main__":
    print("DEBUG: __name__ is __main__, calling main()")
    main()
