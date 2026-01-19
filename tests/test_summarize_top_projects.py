import unittest
from unittest.mock import patch
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
from capstone.cli import _handle_summarize_projects


class TestSummarizeTopProjects(unittest.TestCase):
    @patch("capstone.cli.close_db")
    @patch("capstone.cli.open_db")
    @patch("capstone.cli.fetch_latest_snapshots")
    def test_summarize_top_projects_no_llm(
        self,
        mock_fetch_latest_snapshots,
        mock_open_db,
        mock_close_db,
    ):
        # Arrange: fake snapshot data shaped for ranking
        mock_fetch_latest_snapshots.return_value = {
            "project-a": {
                "project_id": "project-a",
                "metrics": {"files": 10},
                "skills": ["python"],
            },
            "project-b": {
                "project_id": "project-b",
                "metrics": {"files": 5},
                "skills": ["java"],
            },
        }

        args = argparse.Namespace(
            command="summarize-top-projects",
            db_dir=None,
            user=None,
            limit=2,
            use_llm=False,
            format="markdown",
        )

        # Act
        exit_code = _handle_summarize_projects(args)

        # Assert
        self.assertEqual(exit_code, 0)
        mock_fetch_latest_snapshots.assert_called_once()
        mock_open_db.assert_called_once()
        mock_close_db.assert_called_once()
