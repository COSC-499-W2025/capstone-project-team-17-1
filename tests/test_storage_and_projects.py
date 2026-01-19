import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from capstone import storage  # noqa: E402
from capstone.project_detection import detect_node_electron_project  # noqa: E402


class StorageTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)

    def test_open_db_creates_directory_and_reuses_connection(self) -> None:
        base_dir = Path(self._tmpdir.name) / "db"
        conn1 = storage.open_db(base_dir)
        self.assertTrue(base_dir.exists())
        self.assertIsInstance(conn1, sqlite3.Connection)
        conn2 = storage.open_db(base_dir)
        self.assertIs(conn1, conn2)

    def test_store_snapshot_validates_and_exports(self) -> None:
        base_dir = Path(self._tmpdir.name) / "db"
        conn = storage.open_db(base_dir)
        snapshot = {"file_summary": {"file_count": 1}}
        storage.store_analysis_snapshot(conn, project_id="demo", classification="individual", primary_contributor="alice", snapshot=snapshot)

        latest = storage.fetch_latest_snapshot(conn, "demo")
        self.assertEqual(latest["project_id"], "demo")
        self.assertEqual(latest["classification"], "individual")
        self.assertEqual(latest["primary_contributor"], "alice")

        backup_path = Path(self._tmpdir.name) / "backup" / "db-copy.db"
        result_path = storage.backup_database(conn, backup_path)
        self.assertTrue(result_path.exists())
        self.assertGreater(result_path.stat().st_size, 0)

        export_path = Path(self._tmpdir.name) / "exports" / "snapshots.json"
        count = storage.export_snapshots_to_json(conn, export_path)
        self.assertEqual(count, 1)
        exported = json.loads(export_path.read_text(encoding="utf-8"))
        self.assertEqual(exported[0]["project_id"], "demo")
        self.assertIn("snapshot", exported[0])

    def test_store_and_rank_contributor_stats(self) -> None:
        base_dir = Path(self._tmpdir.name) / "db"
        conn = storage.open_db(base_dir)

        storage.store_contributor_stats(
            conn,
            project_id="demo",
            contributor="alice",
            commits=5,
            pull_requests=2,
            issues=1,
            reviews=0,
            score=12.5,
            source="github",
        )
        storage.store_contributor_stats(
            conn,
            project_id="demo",
            contributor="bob",
            commits=8,
            pull_requests=1,
            issues=0,
            reviews=3,
            score=10.0,
            source="github",
        )
        # Update alice with a newer row to ensure latest selection.
        storage.store_contributor_stats(
            conn,
            project_id="demo",
            contributor="alice",
            commits=6,
            pull_requests=3,
            issues=1,
            reviews=2,
            score=14.0,
            source="github",
        )

        latest = storage.fetch_latest_contributor_stats(conn, "demo")
        latest_by_name = {row["contributor"]: row for row in latest}
        self.assertEqual(latest_by_name["alice"]["commits"], 6)
        self.assertEqual(latest_by_name["bob"]["reviews"], 3)

        ranked_score = storage.fetch_contributor_rankings(conn, "demo")
        self.assertEqual(ranked_score[0]["contributor"], "alice")
        ranked_commits = storage.fetch_contributor_rankings(conn, "demo", sort_by="commits")
        self.assertEqual(ranked_commits[0]["contributor"], "bob")

    def tearDown(self) -> None:
        storage.close_db()


class ProjectDetectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self._tmpdir.name)
        self.addCleanup(self._tmpdir.cleanup)

    def test_detects_electron_project_and_generates_markdown(self) -> None:
        package_json = {
            "name": "sample-app",
            "dependencies": {"react": "^18.0.0", "electron": "^25.0.0"},
            "devDependencies": {"eslint": "^8.0.0"},
            "scripts": {"start": "electron .", "test": "npm test"},
        }
        (self.root / "package.json").write_text(json.dumps(package_json), encoding="utf-8")

        is_project, markdown = detect_node_electron_project(self.root)
        self.assertTrue(is_project)
        self.assertIn("Electron desktop application", markdown)
        self.assertIn("`start`", markdown)

    def test_returns_false_when_no_package_json(self) -> None:
        is_project, markdown = detect_node_electron_project(self.root)
        self.assertFalse(is_project)
        self.assertEqual(markdown, "")


if __name__ == "__main__":
    unittest.main()
