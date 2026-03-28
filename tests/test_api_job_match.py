import unittest
from unittest.mock import patch
from types import SimpleNamespace
from fastapi.testclient import TestClient

from capstone.api.server import app

client = TestClient(app)


class TestJobMatchEndpoints(unittest.TestCase):
    @patch("capstone.api.routes.job_match.match_job_to_project")
    @patch("capstone.api.routes.job_match.build_resume_snippet")
    def test_match_endpoint_success(self, mock_snippet, mock_match):
        mock_match.return_value.project_id = "demo"
        mock_match.return_value.job_skills = ["python", "docker"]
        mock_match.return_value.matched_skills = [{"skill": "python"}]
        mock_match.return_value.missing_skills = ["docker"]
        mock_snippet.return_value = "Relevant skills for this role: python (language)"

        response = client.post(
            "/job-matching/match",
            json={
                "project_id": "demo",
                "job_description": "Looking for a Python developer with Docker experience.",
            },
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["project_id"], "demo")
        self.assertIn("python", data["job_skills"])
        self.assertIn("resume_snippet", data)

    def test_match_endpoint_fail(self):
        response = client.post(
            "/job-matching/match",
            json={
                # missing project_id
                "job_description": "Looking for a Python developer with Docker experience."
            },
        )
        self.assertEqual(response.status_code, 422)

    @patch("capstone.api.routes.job_match.open_db")
    @patch("capstone.api.routes.job_match.close_db")
    @patch("capstone.api.routes.job_match.build_jd_profile")
    @patch("capstone.api.routes.job_match.rank_projects_for_job")
    @patch("capstone.api.routes.job_match.matches_to_json")
    def test_rank_endpoint_success_and_top_k(
        self,
        mock_matches_to_json,
        mock_rank,
        mock_build_profile,
        mock_close_db,
        mock_open_db,
    ):
        # Fake DB connection
        class FakeConn:
            def execute(self, *_):
                return self

            def fetchall(self):
                import json
                return [("demo", json.dumps({"skills": ["python", "docker"], "metrics": {}}))]

        mock_open_db.return_value = FakeConn()

        # JD parsing returns whatever structure your ranker expects
        mock_build_profile.return_value = {
            "required_skills": ["python"],
            "preferred_skills": ["docker"],
            "keywords": ["python", "docker"],
        }

        # Return 3 ranked matches; endpoint should slice to top_k BEFORE json conversion
        fake_matches = [
            SimpleNamespace(
                project_id="p1",
                score=0.9,
                required_coverage=1.0,
                preferred_coverage=1.0,
                keyword_overlap=1.0,
                recency_factor=1.0,
                matched_required=["python"],
                matched_preferred=["docker"],
                matched_keywords=["python", "docker"],
            ),
            SimpleNamespace(
                project_id="p2",
                score=0.8,
                required_coverage=0.9,
                preferred_coverage=0.8,
                keyword_overlap=0.8,
                recency_factor=0.9,
                matched_required=["python"],
                matched_preferred=["docker"],
                matched_keywords=["python"],
            ),
            SimpleNamespace(
                project_id="p3",
                score=0.7,
                required_coverage=0.7,
                preferred_coverage=0.6,
                keyword_overlap=0.6,
                recency_factor=0.8,
                matched_required=["python"],
                matched_preferred=[],
                matched_keywords=["python"],
            ),
        ]
        mock_rank.return_value = fake_matches

        # Make matches_to_json predictable so we can assert length easily
        mock_matches_to_json.side_effect = lambda matches: {
            "matches": [{"project_id": match.project_id, "score": match.score} for match in matches]
        }

        # Request top_k=2
        response = client.post(
            "/job-matching/rank?top_k=2",
            json={"job_description": "Looking for a Python developer with Docker experience."},
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertIn("matches", data)
        self.assertEqual(len(data["matches"]), 2)
        self.assertEqual(data["matches"][0]["project_id"], "p1")
        self.assertEqual(data["matches"][1]["project_id"], "p2")

    def test_rank_endpoint_fail_body(self):
        response = client.post("/job-matching/rank", json={})
        self.assertEqual(response.status_code, 422)

    def test_rank_top_k_bounds(self):
        payload = {"job_description": "Looking for a Python developer with Docker experience."}

        r1 = client.post("/job-matching/rank?top_k=0", json=payload)
        self.assertEqual(r1.status_code, 422)

        r2 = client.post("/job-matching/rank?top_k=101", json=payload)
        self.assertEqual(r2.status_code, 422)
