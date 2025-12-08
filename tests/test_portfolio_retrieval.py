# tests/test_portfolio_retrieval.py
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
