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

        fake_rankings = [
            type("R", (), {"project_id": "project-a"})(),
            type("R", (), {"project_id": "project-b"})(),
        ]
        fake_snapshots = {
            "project-a": {"project_id": "project-a"},
            "project-b": {"project_id": "project-b"},
        }

        args = argparse.Namespace(
            command="summarize-top-projects",
            db_dir=None,
            user=None,
            limit=2,
            use_llm=False,
            format="markdown",
        )

        with (
            patch.object(cli, "SnapshotStore") as store_mock,
            patch.object(cli, "RankingService") as rank_mock,
            patch.object(cli, "generate_top_project_summaries", return_value=[{"project_id": "project-a"}, {"project_id": "project-b"}]),
            patch.object(cli, "export_markdown", side_effect=lambda s: s.get("project_id", "")),
            patch("sys.stdout", new_callable=io.StringIO) as fake_out,
        ):
            rank_instance = rank_mock.return_value
            rank_instance.rank.return_value = (fake_rankings, fake_snapshots)
            exit_code = handler(args)
            out = fake_out.getvalue()

        self.assertEqual(exit_code, 0)

        # Your handler prints project ids (not necessarily summaries)
        self.assertIn("project-a", out)
        self.assertIn("project-b", out)
