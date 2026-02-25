import unittest
from unittest.mock import patch
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
    
from capstone.job_matching import (
    extract_job_skills,
    JobMatchResult,
    match_job_to_project,
    build_resume_snippet,
    compute_weights_from_jd,
    score_project_for_job,
    rank_projects_for_job
)


class TestExtractJobSkills(unittest.TestCase):
    def test_extract_job_skills_basic(self):
        text = """
        We are looking for a Python and React developer
        with experience in SQL databases and Docker.
        """
        skills = extract_job_skills(text)

        # Just make sure obvious ones are picked up
        self.assertIn("python", skills)
        self.assertIn("react", skills)
        self.assertIn("sql", skills)
        self.assertIn("docker", skills)

    def test_extract_job_skills_no_match(self):
        text = "We are looking for a highly motivated individual with strong communication skills."
        skills = extract_job_skills(text)

        self.assertEqual(skills, [])


class TestBuildResumeSnippet(unittest.TestCase):
    def test_build_resume_snippet_with_matches(self):
        match = JobMatchResult(
            project_id="demo",
            job_skills=["python", "docker"],
            matched_skills=[
                {"skill": "python", "category": "language", "confidence": 0.95},
                {"skill": "docker", "category": "devops", "confidence": 0.80},
            ],
            missing_skills=[],
        )

        snippet = build_resume_snippet(match)

        # Should mention the skills and some basic labels
        self.assertIn("Relevant Skills for this Role", snippet)
        self.assertIn("python", snippet.lower())
        self.assertIn("docker", snippet.lower())
        self.assertIn("language", snippet.lower())
        self.assertIn("devops", snippet.lower())

    def test_build_resume_snippet_no_matches(self):
        match = JobMatchResult(
            project_id="demo",
            job_skills=["python", "docker"],
            matched_skills=[],
            missing_skills=["python", "docker"],
        )

        snippet = build_resume_snippet(match).lower()

        # This is the nice version of "sucks to suck"
        self.assertIn("could not find strong matches", snippet)
        self.assertIn("job posting", snippet)


class TestMatchJobToProject(unittest.TestCase):
    @patch("capstone.job_matching.load_project_skills")
    def test_match_job_to_project_finds_overlap(self, mock_load_project_skills):
        # Fake the skills we stored for this project in the DB snapshot
        mock_load_project_skills.return_value = [
            {"skill": "python", "category": "language", "confidence": 0.9},
            {"skill": "react", "category": "frontend", "confidence": 0.8},
        ]

        job_text = "This job requires strong Python skills and experience with React."
        result = match_job_to_project(job_text, project_id="demo", db_dir=None)

        # Job skills
        self.assertIn("python", result.job_skills)
        self.assertIn("react", result.job_skills)

        # We should have two matched skills
        self.assertEqual(len(result.matched_skills), 2)
        matched_names = {row["skill"].lower() for row in result.matched_skills}
        self.assertIn("python", matched_names)
        self.assertIn("react", matched_names)

        # No missing skills because project covers everything job asked for here
        self.assertEqual(result.missing_skills, [])

    @patch("capstone.job_matching.load_project_skills")
    def test_match_job_to_project_no_overlap(self, mock_load_project_skills):
        mock_load_project_skills.return_value = [
            {"skill": "java", "category": "language", "confidence": 0.9},
        ]

        job_text = "We are looking for a Python developer with React experience."
        result = match_job_to_project(job_text, project_id="demo", db_dir=None)

        # Job wants python and react
        self.assertIn("python", result.job_skills)
        self.assertIn("react", result.job_skills)

        # Project only has java, so zero matched skills
        self.assertEqual(len(result.matched_skills), 0)

        # Both job skills should show up as missing
        self.assertIn("python", result.missing_skills)
        self.assertIn("react", result.missing_skills)

class TestComputeWeights(unittest.TestCase):
    def test_weights_sum_to_one(self):
        jd_profile = {
            "required_skills": ["python", "sql"],
            "preferred_skills": ["docker"],
            "keywords": ["backend", "api"]
        }
        
        weights = compute_weights_from_jd(jd_profile)
        total = sum(weights.values())
        self.assertAlmostEqual(total, 1.0, places=5)
        
        self.assertIn("required", weights)
        self.assertIn("preferred", weights)
        self.assertIn("keywords", weights)
        self.assertIn("recency", weights)
        
    def test_weights_no_skills(self):
        jd_profile = {
            "required_skills": [],
            "preferred_skills": [],
            "keywords": []
        }
        
        weights = compute_weights_from_jd(jd_profile)
        total = sum(weights.values())
        self.assertAlmostEqual(total, 1.0, places=5)
        
        # Should fall back to defaults
        self.assertEqual(weights["required"], 0.4)
        self.assertEqual(weights["preferred"], 0.4)
        self.assertEqual(weights["keywords"], 0.1)
        self.assertEqual(weights["recency"], 0.1)
        
class TestScoreProjectForJob(unittest.TestCase):
    def test_score_project_for_job(self):
        jd_profile = {
            "required_skills": ["python", "sql"],
            "preferred_skills": ["docker"],
            "keywords": ["backend", "api"]
        }
        
        project_snapshot = {
            "project_id": "demo",
            "skills": [{"skill": "python", "category": "language", "confidence": 0.9}],
            "metrics": {"recency_days": 0}
        }
        
        result = score_project_for_job(jd_profile, project_snapshot)
        self.assertGreaterEqual(result.score, 0.0)
        self.assertLessEqual(result.score, 1.0)
        self.assertEqual(result.project_id, "demo")
        self.assertGreater(result.required_coverage, 0.0)
        
class TestRankProjects(unittest.TestCase):
    def test_ranking_orders_by_score(self):
        jd_profile = {
            "required_skills": ["python", "sql"],
            "preferred_skills": ["docker"],
            "keywords": ["backend", "api"]
        }
        
        projA = {
            "project_id": "A",
            "skills": [{"skill": "python"}],
            "metrics": {"recency_days": 0}
        }
        
        projB = {
            "project_id": "B",
            "skills": [{"skill": "java"}],
            "metrics": {"recency_days": 0}
        }
        
        matches = rank_projects_for_job(jd_profile, [projA, projB])
        
        self.assertEqual(matches[0].project_id, "A")
        self.assertGreaterEqual(matches[0].score, matches[1].score)

if __name__ == "__main__":
    unittest.main()
