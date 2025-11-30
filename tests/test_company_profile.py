import unittest
from unittest.mock import patch
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import List

# adjust sys.path
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from capstone.company_profile import (
    extract_traits,
    build_company_jd_profile,
    build_company_resume_bullets,
)


@dataclass
class FakeMatch:
    project_id: str
    score: float
    required_coverage: float
    preferred_coverage: float
    keyword_overlap: float
    recency_factor: float
    matched_required: List[str]
    matched_preferred: List[str]
    matched_keywords: List[str]


class CompanyMatchingTests(unittest.TestCase):
    def test_extract_traits_basic(self):
        text = """
        We value strong communication and collaboration.
        You should be a real team player who takes ownership of your work.
        """

        traits = extract_traits(text)

        self.assertIn("communication", traits)
        self.assertIn("teamwork", traits)
        self.assertIn("ownership", traits)
        self.assertEqual(len(traits), len(set(traits)))  # no duplicates

    @patch("capstone.company_profile.fetch_company_text")
    def test_build_company_jd_profile_from_company_name(self, mock_fetch):
        mock_fetch.return_value = """
        At Acme Corp we build backend services in Python and Django.
        We deploy on AWS and use SQL databases.
        We value strong communication and teamwork.
        """

        jd_profile = build_company_jd_profile("Acme Corp")

        required_skills = jd_profile["required_skills"]
        preferred_skills = jd_profile["preferred_skills"]
        keywords = jd_profile["keywords"]

        for skill in ["python", "django", "aws", "sql"]:
            self.assertIn(skill, required_skills)
            self.assertIn(skill, preferred_skills)

        self.assertIn("communication", keywords)
        self.assertIn("teamwork", keywords)

        for item in ["python", "django", "aws", "sql", "communication", "teamwork"]:
            self.assertIn(item, keywords)

    @patch("capstone.company_profile.fetch_company_text")
    def test_build_company_jd_profile_empty_text(self, mock_fetch):
        mock_fetch.return_value = "   "

        jd_profile = build_company_jd_profile("Some Company")

        self.assertEqual(jd_profile["required_skills"], [])
        self.assertEqual(jd_profile["preferred_skills"], [])
        self.assertEqual(jd_profile["keywords"], [])

    def test_build_company_resume_bullets_basic(self):
        company_name = "Acme Corp"

        jd_profile = {
            "required_skills": ["python", "django", "sql"],
            "preferred_skills": ["python", "django", "sql"],
            "keywords": ["python", "django", "sql", "communication", "teamwork"],
        }

        matches = [
            FakeMatch(
                project_id="payments-api",
                score=0.9,
                required_coverage=1.0,
                preferred_coverage=1.0,
                keyword_overlap=0.8,
                recency_factor=0.9,
                matched_required=["python", "django", "sql"],
                matched_preferred=["python", "django", "sql"],
                matched_keywords=["python", "django", "sql"],
            ),
            FakeMatch(
                project_id="infra-tools",
                score=0.6,
                required_coverage=0.33,
                preferred_coverage=0.33,
                keyword_overlap=0.3,
                recency_factor=0.8,
                matched_required=["python"],
                matched_preferred=["python"],
                matched_keywords=["python"],
            ),
        ]

        bullets = build_company_resume_bullets(
            company_name=company_name,
            jd_profile=jd_profile,
            matches=matches,
            max_projects=2,
            max_skills_per_project=3,
        )

        self.assertEqual(len(bullets), 2)

        self.assertIn("payments-api", bullets[0])
        self.assertIn("python", bullets[0])
        self.assertIn("django", bullets[0])
        self.assertIn("sql", bullets[0])

        self.assertIn("infra-tools", bullets[1])
        self.assertIn("python", bullets[1])

        self.assertIn("Acme Corp", bullets[0])
        self.assertIn("Acme Corp", bullets[1])


if __name__ == "__main__":
    unittest.main()
