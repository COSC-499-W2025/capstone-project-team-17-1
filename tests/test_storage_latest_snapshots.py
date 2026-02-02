import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from capstone.storage import open_db, close_db, fetch_latest_snapshots


def _insert_row(conn, project_id: str, created_at: str, snapshot_obj, classification: str = "solo"):
    if isinstance(snapshot_obj, str):
        snapshot_payload = snapshot_obj
    else:
        snapshot_payload = json.dumps(snapshot_obj)

    conn.execute(
        """
        INSERT INTO project_analysis (project_id, classification, primary_contributor, snapshot, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (project_id, classification, "tester", snapshot_payload, created_at),
    )
    conn.commit()


class TestFetchLatestSnapshots(unittest.TestCase):
    def _open_temp_db(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)

        db_dir = Path(td.name)
        conn = open_db(db_dir)

        # close must happen before td.cleanup
        self.addCleanup(close_db)
        return conn

    def test_empty_db_returns_empty_list(self):
        conn = self._open_temp_db()
        got = fetch_latest_snapshots(conn)
        self.assertEqual(got, [])

    def test_picks_latest_per_project(self):
        conn = self._open_temp_db()

        _insert_row(conn, "A", "2025-01-01 00:00:00", {"v": 1})
        _insert_row(conn, "A", "2025-01-02 00:00:00", {"v": 2})
        _insert_row(conn, "B", "2025-01-01 12:00:00", {"b": True})

        got = fetch_latest_snapshots(conn)
        by_id = {item["project_id"]: item for item in got}

        self.assertEqual(set(by_id.keys()), {"A", "B"})
        self.assertEqual(by_id["A"]["snapshot"]["v"], 2)
        self.assertEqual(by_id["B"]["snapshot"]["b"], True)

    def test_limit_returns_most_recent_projects(self):
        conn = self._open_temp_db()

        _insert_row(conn, "C", "2025-01-01 00:00:00", {"id": "C"})
        _insert_row(conn, "B", "2025-01-02 00:00:00", {"id": "B"})
        _insert_row(conn, "A", "2025-01-03 00:00:00", {"id": "A"})

        got = fetch_latest_snapshots(conn, limit=2)
        self.assertEqual([x["project_id"] for x in got], ["A", "B"])

    def test_invalid_json_becomes_empty_snapshot(self):
        conn = self._open_temp_db()

        _insert_row(conn, "OK", "2025-01-02 00:00:00", {"ok": 1})
        _insert_row(conn, "BAD", "2025-01-03 00:00:00", "not valid json")

        got = fetch_latest_snapshots(conn)

