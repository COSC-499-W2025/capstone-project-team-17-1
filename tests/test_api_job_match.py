import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient

from capstone.api.server import app

client = TestClient(app)

class TestJobMatchEndpoints(unittest.TestCase):
    @patch("capstone.job_matching.match_job_to_project")
    @patch("capstone.job_matching.build_resume_snippet")
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
                "job_description": "Looking for a Python developer with Docker experience."
            }
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
            }
        )
        
        self.assertEqual(response.status_code, 422)
        
    @patch("capstone.storage.open_db")
    @patch("capstone.job_matching.rank_projects_for_job")
    @patch("capstone.job_matching.build_jd_profile")
    def test_rank_endpoint_success(self, mock_build_profile, mock_rank, mock_open_db):
        class FakeConn:
            def execute(self, *_):
                return self
            
            def fetchall(self):
                import json
                return [("demo", json.dumps({"skills": ["python", "docker"], "metrics": {}}))]
        
        mock_open_db.return_value = FakeConn()
        mock_build_profile.return_value = {
            "required_skills": ["python"],
            "preferred_skills": ["docker"],
            "keywords": ["python", "docker"],
        }
        
        mock_rank.return_value = []
        
        response = client.post(
            "/job-matching/rank",
            json={
                "job_description": "Looking for a Python developer with Docker experience."
            }
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertIn("matches", response.json())
        
    def test_rank_endpoint_fail(self):
        response = client.post("/job-matching/rank", json={})
        self.assertEqual(response.status_code, 422)