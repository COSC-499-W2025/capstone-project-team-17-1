# tests/test_main_menu.py
import io
import sys
import types
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch, Mock

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# Avoid importing the real capstone.cli (it can pull in Flask)
dummy_cli = types.ModuleType("capstone.cli")
dummy_cli.main = lambda argv=None: 0
sys.modules["capstone.cli"] = dummy_cli

import main as app  # noqa: E402


def _entrypoint():
    fn = getattr(app, "app_main", None) or getattr(app, "main", None)
    if fn is None:
        raise RuntimeError("main.py must expose app_main() or main()")
    return fn


class _FakeCursor:
    def __init__(self):
        self.calls = []

    def execute(self, sql, params=()):
        self.calls.append((sql, params))
        return self


class _FakeConn:
    def __init__(self):
        self.cursor_obj = _FakeCursor()
        self.commits = 0

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        self.commits += 1


class _ConnCM:
    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        return self.conn

    def __exit__(self, exc_type, exc, tb):
        return False


class MainMenuTests(unittest.TestCase):
    def run_menu(self, inputs, *, grant=True, rows=None):
        out = io.StringIO()
        conn = _FakeConn()

        if rows is None:
            rows = []

        with (
            patch.object(app, "grant_consent", return_value=grant),
            patch.object(app, "open_db", return_value=_ConnCM(conn)),
            patch.object(app, "fetch_latest_snapshots", return_value=rows),
            patch("builtins.input", side_effect=list(inputs)),
            redirect_stdout(out),
        ):
            _entrypoint()()

        return out.getvalue(), conn

    def test_exits_when_consent_denied(self):
        text, _ = self.run_menu(inputs=[], grant=False)
        self.assertIn("Consent is required", text)

    def test_no_projects(self):
        text, _ = self.run_menu(inputs=["2", "10"], rows=[])
        self.assertIn("No projects found", text)

    def test_lists_projects(self):
        rows = [
            {
                "id": 1,
                "project_id": "p1",
                "snapshot": {"project_id": "p1", "project_name": "Demo"},
                "created_at": "2026-01-11T00:00:00Z",
            }
        ]

        text, _ = self.run_menu(inputs=["2", "10"], rows=rows)

        # Accept either name key depending on your printing logic
        self.assertTrue(("Demo" in text) or ("p1" in text))

    def test_analyze_calls_store(self):
        rows = []
        out = io.StringIO()
        conn = _FakeConn()

        with (
            patch.object(app, "grant_consent", return_value=True),
            patch.object(app, "open_db", return_value=_ConnCM(conn)),
            patch.object(app, "fetch_latest_snapshots", return_value=rows),
            patch.object(app, "store_analysis_snapshot", return_value=None) as store_mock,
            patch.object(app.os.path, "isfile", return_value=True),
            patch("builtins.input", side_effect=["1", "C:\\tmp\\demo.zip", "10"]),
            redirect_stdout(out),
        ):
            _entrypoint()()

        store_mock.assert_called()

    def test_summary_calls_rank_and_template(self):
        rows = [
            {
                "id": 1,
                "project_id": "p1",
                "snapshot": {"project_id": "p1"},
                "created_at": "2026-01-11T00:00:00Z",
            }
        ]

        out = io.StringIO()
        conn = _FakeConn()

        with (
            patch.object(app, "grant_consent", return_value=True),
            patch.object(app, "open_db", return_value=_ConnCM(conn)),
            patch.object(app, "fetch_latest_snapshots", return_value=rows),
            patch.object(app, "_normalize_snapshot", side_effect=lambda x: x, create=True),
            patch.object(app, "rank_projects_from_snapshots", return_value=[{"project_id": "p1"}]),
            patch.object(app, "create_summary_template", return_value="SUMMARY") as tmpl_mock,
            patch("builtins.input", side_effect=["4", "10"]),
            redirect_stdout(out),
        ):
            _entrypoint()()

        tmpl_mock.assert_called()
        self.assertIn("SUMMARY", out.getvalue())

if __name__ == "__main__":
    unittest.main()
