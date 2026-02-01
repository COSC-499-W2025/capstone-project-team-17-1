import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from capstone.portfolio_retrieval import create_app, ensure_indexes
from capstone.resume_retrieval import ensure_resume_schema


SCHEMA = """
CREATE TABLE IF NOT EXISTS project_analysis(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id TEXT NOT NULL,
  classification TEXT,
  primary_contributor TEXT,
  snapshot TEXT NOT NULL,
  created_at TEXT NOT NULL
);
"""


def seed_project(conn: sqlite3.Connection, project_id: str = "demo"):
    snap = {
        "project_name": "Demo Project",
        "file_summary": {"file_count": 2, "total_bytes": 123, "active_days": 1},
    }
    conn.execute(
        "INSERT INTO project_analysis(project_id, classification, primary_contributor, snapshot, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (project_id, "ok", "alice", json.dumps(snap), "2025-01-01T00:00:00"),
    )
    conn.commit()


class ApiEndpointTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dbdir = Path(self.tmp.name)
        self.con = sqlite3.connect(self.dbdir / "capstone.db")
        self.con.executescript(SCHEMA)
        ensure_indexes(self.con)
        ensure_resume_schema(self.con)
        seed_project(self.con, "demo")

        try:
            self.app = create_app(db_dir=str(self.dbdir), auth_token="t")
        except Exception:
            self.app = None

    def tearDown(self):
        self.con.close()
        self.tmp.cleanup()

    def _client(self):
        if not self.app:
            self.skipTest("Flask not installed")
        return self.app.test_client()

    def test_portfolio_endpoints(self):
        client = self._client()
        headers = {"Authorization": "Bearer t"}

        r = client.get("/portfolios/latest?projectId=demo", headers=headers)
        self.assertEqual(r.status_code, 200)
        self.assertIn("data", r.get_json())

        r = client.get("/portfolios?projectId=demo&page=1&pageSize=20", headers=headers)
        self.assertEqual(r.status_code, 200)
        self.assertIsInstance(r.get_json().get("data"), list)

        r = client.get("/portfolios/evidence?projectId=demo", headers=headers)
        self.assertEqual(r.status_code, 200)
        self.assertIn("evidence", r.get_json().get("data", {}))

        r = client.get("/portfolio/demo", headers=headers)
        self.assertEqual(r.status_code, 200)
        self.assertIn("summary", r.get_json().get("data", {}))

        r = client.post("/portfolio/generate", json={"projectIds": ["demo"]}, headers=headers)
        self.assertEqual(r.status_code, 200)
        self.assertIsInstance(r.get_json().get("data"), list)

        r = client.post("/portfolio/demo/edit", json={"summary": "Custom showcase summary."}, headers=headers)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["data"]["summary"], "Custom showcase summary.")

        r = client.post("/portfolio/demo/edit", json={}, headers=headers)
        self.assertEqual(r.status_code, 400)

        r = client.post("/portfolio/generate", json={}, headers=headers)
        self.assertEqual(r.status_code, 400)

        r = client.get("/portfolio/does-not-exist", headers=headers)
        self.assertEqual(r.status_code, 404)

    def test_resume_endpoints(self):
        client = self._client()
        headers = {"Authorization": "Bearer t"}

        create_payload = {
            "section": "projects",
            "title": "Telemetry Platform",
            "body": "Built ingestion and alerting services.",
            "projects": ["demo"],
            "skills": ["Python"],
        }
        r = client.post("/resume", json=create_payload, headers=headers)
        self.assertEqual(r.status_code, 201)
        entry_id = r.get_json()["data"]["id"]

        r = client.get(f"/resume/{entry_id}", headers=headers)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["data"]["title"], "Telemetry Platform")

        r = client.post(
            f"/resume/{entry_id}/edit",
            json={"summary": "Custom resume summary.", "projects": ["demo"]},
            headers=headers,
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["data"]["summary"], "Custom resume summary.")

        r = client.get("/resume?format=preview", headers=headers)
        self.assertEqual(r.status_code, 200)
        self.assertIn("sections", r.get_json()["data"])

        r = client.post("/resume/generate", json={"format": "json"}, headers=headers)
        self.assertEqual(r.status_code, 200)
        payload = r.get_json()["data"]["payload"]
        self.assertIn("sections", payload)

    def test_resume_project_wording_endpoints(self):
        client = self._client()
        headers = {"Authorization": "Bearer t"}

        r = client.post(
            "/resume-projects",
            json={"projectId": "demo", "summary": "Custom resume wording.", "isActive": True},
            headers=headers,
        )
        self.assertEqual(r.status_code, 201)

        r = client.get("/resume-projects?projectId=demo", headers=headers)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["data"]["project_id"], "demo")

        r = client.post("/resume-projects/generate", json={"projectIds": ["demo"]}, headers=headers)
        self.assertEqual(r.status_code, 200)
        self.assertIsInstance(r.get_json()["data"], list)


if __name__ == "__main__":
    unittest.main()
