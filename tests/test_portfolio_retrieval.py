# tests/test_portfolio_retrieval.py
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from capstone.portfolio_retrieval import ensure_indexes, list_snapshots, get_latest_snapshot, create_app


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


def seed(conn: sqlite3.Connection, project_id: str, n: int = 3):
    for i in range(n):
        snap = {"n": i, "meta": f"s{i}"}
        conn.execute(
            "INSERT INTO project_analysis(project_id, classification, primary_contributor, snapshot, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (project_id, "ok", "alice", json.dumps(snap), f"2025-01-0{i+1}T00:00:00"),
        )
    conn.commit()


class PortfolioRetrievalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dbdir = Path(self.tmp.name)
        self.con = sqlite3.connect(self.dbdir / "capstone.db")
        self.con.executescript(SCHEMA)
        ensure_indexes(self.con)
        seed(self.con, "demo", 5)

    def tearDown(self):
        self.con.close()
        self.tmp.cleanup()

    def test_get_latest_snapshot(self):
        latest = get_latest_snapshot(self.con, "demo")
        self.assertIsInstance(latest, dict)
        self.assertEqual(latest["n"], 4)  # newest

    def test_list_snapshots_pagination(self):
        page1, total = list_snapshots(self.con, "demo", page=1, page_size=2, sort_field="created_at", sort_dir="desc")
        page2, _ = list_snapshots(self.con, "demo", page=2, page_size=2, sort_field="created_at", sort_dir="desc")
        self.assertEqual(total, 5)
        self.assertEqual(len(page1), 2)
        self.assertEqual(len(page2), 2)
        # check ordering (desc)
        self.assertGreaterEqual(page1[0].created_at, page1[1].created_at)

    def test_flask_latest_endpoint(self):
        try:
            app = create_app(db_dir=str(self.dbdir), auth_token="t")
        except Exception:
            self.skipTest("Flask not installed")
            return
        client = app.test_client()
        # Unauthorized
        r = client.get("/portfolios/latest?projectId=demo")
        self.assertEqual(r.status_code, 401)
        # OK with token
        r = client.get("/portfolios/latest?projectId=demo", headers={"Authorization": "Bearer t"})
        self.assertEqual(r.status_code, 200)
        body = r.get_json()
        self.assertIn("data", body)
        self.assertEqual(body["data"]["n"], 4)

    def test_resume_entry_endpoints(self):
        try:
            app = create_app(db_dir=str(self.dbdir), auth_token="t")
        except Exception:
            self.skipTest("Flask not installed")
            return
        client = app.test_client()
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

        r = client.post("/resume/does-not-exist/edit", json={"summary": "x"}, headers=headers)
        self.assertEqual(r.status_code, 404)

        r = client.get("/resume?format=preview", headers=headers)
        self.assertEqual(r.status_code, 200)
        self.assertIn("sections", r.get_json()["data"])

        r = client.post("/resume/generate", json={"format": "json"}, headers=headers)
        self.assertEqual(r.status_code, 200)
        payload = r.get_json()["data"]["payload"]
        self.assertIn("sections", payload)

    def test_resume_wording_priority(self):
        try:
            app = create_app(db_dir=str(self.dbdir), auth_token="t")
        except Exception:
            self.skipTest("Flask not installed")
            return
        client = app.test_client()
        headers = {"Authorization": "Bearer t"}

        r = client.post(
            "/resume",
            json={
                "section": "projects",
                "title": "Demo Project",
                "body": "Default project body.",
                "projects": ["demo"],
            },
            headers=headers,
        )
        self.assertEqual(r.status_code, 201)

        r = client.post("/resume-projects/generate", json={"projectIds": ["demo"]}, headers=headers)
        self.assertEqual(r.status_code, 200)

        r = client.post(
            "/resume-projects",
            json={"projectId": "demo", "summary": "Custom resume wording.", "isActive": True},
            headers=headers,
        )
        self.assertEqual(r.status_code, 201)

        r = client.get("/resume?format=preview", headers=headers)
        self.assertEqual(r.status_code, 200)
        preview = r.get_json()["data"]
        excerpt = preview["sections"][0]["items"][0]["excerpt"]
        source = preview["sections"][0]["items"][0]["source"]
        self.assertEqual(excerpt, "Custom resume wording.")
        self.assertEqual(source, "custom")
        
    # validate missing required parameters
    def test_validate_missing_params(self):
        try:
            app = create_app(db_dir=str(self.dbdir), auth_token="t")
        except Exception:
            self.skipTest("Flask not installed")
            return
        client = app.test_client()
        headers = {"Authorization": "Bearer t"}

        # should rejects missing projectId on portfolios/latest
        r = client.get("/portfolios/latest", headers=headers)
        self.assertIn(r.status_code, {400, 422})
        
        # should reject missing projectId on resume
        r = client.get("/resume-projects/latest", json={}, headers=headers)
        self.assertIn(r.status_code, {400, 404, 422})
        
        # should reject missing projectId on resume
        r = client.get("/resume-projects/latest", json={"summary": "x", "isActive": True}, headers=headers)
        self.assertIn(r.status_code, {400, 404, 422})

if __name__ == "__main__":
    unittest.main()
