import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
from capstone.cli import build_parser


class TestCliSummarizeTopProjects(unittest.TestCase):
    def test_command_is_registered(self):
        parser = build_parser()
        args = parser.parse_args(
            ["summarize-top-projects", "--limit", "3", "--format", "markdown"]
        )

        self.assertEqual(args.command, "summarize-top-projects")
        self.assertEqual(args.limit, 3)
        self.assertEqual(args.format, "markdown")
