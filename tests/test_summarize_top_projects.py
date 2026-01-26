import unittest
from unittest.mock import patch
import argparse
import sys
from pathlib import Path
import importlib
import io

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


class TestSummarizeTopProjects(unittest.TestCase):
    def test_summarize_top_projects_no_llm(self):
        cli = importlib.import_module("capstone.cli")

        handler = (
            getattr(cli, "_handle_summarize_projects", None)
            or getattr(cli, "handle_summarize_projects", None)
        )
        self.assertIsNotNone(handler, "Could not find summarize handler in capstone.cli")

        fake_conn = object()

        fake_rows = [
            {
                "project_id": "project-a",
                "classification": "unknown",
                "primary_contributor": None,
                "created_at": "2026-01-01 00:00:00",
                "snapshot": {"project_id": "project-a", "metrics": {"files": 10}, "skills": ["python"]},
            },
            {
                "project_id": "project-b",
                "classification": "unknown",
                "primary_contributor": None,
                "created_at": "2026-01-02 00:00:00",
                "snapshot": {"project_id": "project-b", "metrics": {"files": 5}, "skills": ["java"]},
            },
        ]

        args = argparse.Namespace(
            command="summarize-top-projects",
            db_dir=None,
            user=None,
            limit=2,
            use_llm=False,
            format="markdown",
        )

        # Patch the *actual imported module* so it works even if these
        # names aren't defined at module scope (create=True).
        with (
            patch.object(cli, "open_db", return_value=fake_conn, create=True) as mock_open_db,
            patch.object(cli, "close_db", create=True) as mock_close_db,
            patch.object(cli, "fetch_latest_snapshots", return_value=fake_rows, create=True) as mock_fetch,
            patch("sys.stdout", new_callable=io.StringIO) as fake_out,
        ):
            exit_code = handler(args)
            out = fake_out.getvalue()

        self.assertEqual(exit_code, 0)

        # open_db usually called with args.db_dir (None here)
        mock_open_db.assert_called_once()
        open_args, open_kwargs = mock_open_db.call_args
        self.assertEqual(open_args[0], None)

        # tolerate both fetch_latest_snapshots(conn) and fetch_latest_snapshots(conn, limit=2)
        mock_fetch.assert_called_once()
        call_args, call_kwargs = mock_fetch.call_args
        self.assertIs(call_args[0], fake_conn)
        self.assertIn(call_kwargs.get("limit", None), (None, 2))

        mock_close_db.assert_called_once()

        # Your handler prints project ids (not necessarily summaries)
        self.assertIn("project-a", out)
        self.assertIn("project-b", out)
