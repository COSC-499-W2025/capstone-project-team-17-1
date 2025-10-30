import io
import sys
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from capstone import cli  # noqa: E402
from capstone.project_ranking import rank_projects_from_snapshots  # noqa: E402
from capstone.storage import open_db, store_analysis_snapshot  # noqa: E402


class ProjectRankingTests(unittest.TestCase):
    def test_rank_projects_prefers_recent_and_diverse_projects(self) -> None:
        now = datetime(2025, 1, 1, tzinfo=timezone.utc)
        snapshots = {
            "alpha": {
                "file_summary": {
                    "file_count": 20,
                    "total_bytes": 50_000,
                    "latest_modification": (now - timedelta(days=2)).isoformat(),
                    "active_days": 10,
                    "activity_breakdown": {"code": 15, "documentation": 5},
                },
                "languages": {"Python": 10, "HTML": 5},
                "frameworks": ["FastAPI"],
                "collaboration": {
                    "contributors": {"alice": 8, "bob": 2},
                    "primary_contributor": "alice",
                },
            },
            "beta": {
                "file_summary": {
                    "file_count": 5,
                    "total_bytes": 10_000,
                    "latest_modification": (now - timedelta(days=60)).isoformat(),
                    "active_days": 2,
                    "activity_breakdown": {"code": 5},
                },
                "languages": {"Python": 5},
                "frameworks": [],
                "collaboration": {
                    "contributors": {"alice": 1},
                    "primary_contributor": "alice",
                },
            },
        }

        rankings = rank_projects_from_snapshots(snapshots, user="alice", now=now)
        self.assertEqual([record.project_id for record in rankings], ["alpha", "beta"])
        top = rankings[0]
        self.assertGreater(top.score, rankings[1].score)
        self.assertAlmostEqual(top.breakdown["recency"], 1.0 / (1.0 + (2 / 30.0)))
        self.assertGreater(top.breakdown["diversity"], rankings[1].breakdown["diversity"])

    def test_cli_rank_projects_output(self) -> None:
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        db_dir = Path(tmpdir.name)
        conn = open_db(db_dir)
        snapshot = {
            "file_summary": {
                "file_count": 3,
                "total_bytes": 1200,
                "latest_modification": datetime.now(tz=timezone.utc).isoformat(),
                "active_days": 3,
                "activity_breakdown": {"code": 2, "documentation": 1},
            },
            "languages": {"Python": 2, "Markdown": 1},
            "frameworks": ["Flask"],
            "collaboration": {
                "contributors": {"me": 3},
                "primary_contributor": "me",
            },
        }
        store_analysis_snapshot(conn, project_id="gamma", classification="individual", primary_contributor="me", snapshot=snapshot)

        args = type("Args", (), {"db_dir": db_dir, "user": "me", "limit": None})
        with io.StringIO() as buffer, mock.patch("sys.stdout", buffer):
            exit_code = cli._handle_rank_projects(args)
            output = buffer.getvalue()

        self.assertEqual(exit_code, 0)
        self.assertIn("gamma", output)
        self.assertIn("contribution_ratio", output)


if __name__ == "__main__":
    unittest.main()
