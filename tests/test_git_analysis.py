import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from capstone import storage  # noqa: E402
from capstone.git_analysis import analyze_repository, parse_git_log_stream, summarize_to_json  # noqa: E402


_SAMPLE_GIT_LOG = """commit:abcd1234|Alice Example|alice@example.com|1700000000|Initial commit
10	0	src/app.py
5	1	README.md
commit:abcd5678|Bot Runner|bot@example.com|1700000100|Automated build
1	1	build.yml
commit:abcd9abc|Bob Collaborator|bob@example.com|1700000200|Review: adjust styles
0	0	src/app.py
"""


class GitLogParsingTests(unittest.TestCase):
    def test_parse_git_log_stream(self) -> None:
        entries = parse_git_log_stream(_SAMPLE_GIT_LOG)
        self.assertEqual(len(entries), 3)
        self.assertEqual(entries[0]["author"], "Alice Example")
        self.assertEqual(entries[0]["lines"], 16)
        self.assertTrue(entries[2]["reviews"])
        self.assertEqual(entries[1]["kind"], "commit")


class RepositoryAnalysisTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.repo_dir = Path(self._tmpdir.name) / "repo"
        self.repo_dir.mkdir()
        self.addCleanup(self._tmpdir.cleanup)

    def tearDown(self) -> None:
        storage.close_db()

    def test_analyze_repository_persists_snapshot(self) -> None:
        db_dir = Path(self._tmpdir.name) / "db"
        with patch("capstone.git_analysis.run_git_log", return_value=_SAMPLE_GIT_LOG):
            snapshot = analyze_repository(
                self.repo_dir,
                project_id="sample",
                include_bots=False,
                main_user="Alice Example",
                db_dir=db_dir,
            )

        self.assertEqual(snapshot["classification"], "collaborative")
        self.assertEqual(snapshot["primary_contributor"], "Alice Example")
        self.assertIn("csv", snapshot["exports"])

        conn = storage.open_db(db_dir)
        cursor = conn.execute("SELECT COUNT(*) FROM project_analysis WHERE project_id = ?", ("sample",))
        row = cursor.fetchone()
        self.assertEqual(row[0], 1)

        latest = storage.fetch_latest_snapshot(conn, "sample")
        self.assertIsNotNone(latest)
        self.assertEqual(latest["project_id"], "sample")
        self.assertIn("scores", latest)

    def test_summarize_to_json(self) -> None:
        payload = {"project_id": "demo", "classification": "individual"}
        rendered = summarize_to_json(payload)
        self.assertIn("project_id", rendered)
        parsed = json.loads(rendered)
        self.assertEqual(parsed["classification"], "individual")


if __name__ == "__main__":
    unittest.main()
