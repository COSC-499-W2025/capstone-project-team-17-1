import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from capstone import cli  # noqa: E402
from capstone.consent import ExternalPermissionDenied  # noqa: E402
from capstone.modes import ModeResolution  # noqa: E402


class _ConfigState(SimpleNamespace):
    pass


class CLITestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)

    def test_analyze_missing_file_returns_json_error(self) -> None:
        args = SimpleNamespace(
            archive=str(Path(self._tmpdir.name) / "missing.zip"),
            metadata_output=Path(self._tmpdir.name) / "out" / "metadata.jsonl",
            summary_output=Path(self._tmpdir.name) / "out" / "summary.json",
            analysis_mode="auto",
            summary_to_stdout=False,
            quiet=False,
            project_id=None,
            db_dir=None,
        )

        with patch("sys.stderr", new_callable=io.StringIO) as fake_err:
            exit_code = cli._handle_analyze(args)

        self.assertEqual(exit_code, 4)
        error_payload = fake_err.getvalue().strip()
        self.assertIn("FileNotFound", error_payload)
        self.assertIn("missing.zip", error_payload)

    def test_analyze_summary_to_stdout(self) -> None:
        archive_path = Path(self._tmpdir.name) / "sample.zip"
        from zipfile import ZipFile

        with ZipFile(archive_path, "w"):
            pass

        args = SimpleNamespace(
            archive=str(archive_path),
            metadata_output=Path(self._tmpdir.name) / "out" / "metadata.jsonl",
            summary_output=Path(self._tmpdir.name) / "out" / "summary.json",
            analysis_mode="auto",
            summary_to_stdout=True,
            quiet=False,
            project_id="sample",
            db_dir=Path(self._tmpdir.name) / "db",
        )

        summary_payload = {
            "local_mode_label": "Local Analysis Mode",
            "resolved_mode": "local",
            "metadata_output": str(args.metadata_output),
            "file_summary": {"file_count": 1, "total_bytes": 10},
            "languages": {"Python": 1},
            "frameworks": [],
            "collaboration": {"classification": "unknown"},
            "scan_duration_seconds": 0.1,
        }

        with patch.object(cli, "ensure_consent", return_value=SimpleNamespace(granted=True, decision="allow")), \
            patch.object(cli, "load_config", return_value=SimpleNamespace(preferences=SimpleNamespace(labels={"local_mode": "Local Analysis Mode"}))), \
            patch.object(cli, "resolve_mode", return_value=ModeResolution(requested="auto", resolved="local", reason="Local analysis enforced")), \
            patch.object(cli.ZipAnalyzer, "analyze", return_value=summary_payload), \
            patch("sys.stdout", new_callable=io.StringIO) as fake_out:
            exit_code = cli._handle_analyze(args)

        self.assertEqual(exit_code, 0)
        output = fake_out.getvalue()
        self.assertIn("Local Analysis Mode", output)
        parsed = json.loads(output)
        self.assertEqual(parsed["resolved_mode"], "local")

    def test_analyze_rejects_empty_archive_path(self) -> None:
        args = SimpleNamespace(
            archive="  ",
            metadata_output=Path(self._tmpdir.name) / "meta.jsonl",
            summary_output=Path(self._tmpdir.name) / "summary.json",
            analysis_mode="auto",
            summary_to_stdout=False,
            quiet=False,
            project_id=None,
            db_dir=None,
        )

        with patch("sys.stderr", new_callable=io.StringIO) as fake_err:
            exit_code = cli._handle_analyze(args)

        self.assertEqual(exit_code, 5)
        self.assertIn("Archive path must not be empty", fake_err.getvalue())

    def test_analyze_prompts_for_consent_and_grants(self) -> None:
        archive_path = Path(self._tmpdir.name) / "sample.zip"
        from zipfile import ZipFile

        with ZipFile(archive_path, "w"):
            pass

        args = SimpleNamespace(
            archive=str(archive_path),
            metadata_output=Path(self._tmpdir.name) / "meta.jsonl",
            summary_output=Path(self._tmpdir.name) / "summary.json",
            analysis_mode="auto",
            summary_to_stdout=False,
            quiet=True,
            project_id="sample",
            db_dir=Path(self._tmpdir.name) / "db",
        )

        fake_preferences = SimpleNamespace(labels={"local_mode": "Local Analysis Mode"})
        fake_config = SimpleNamespace(consent=SimpleNamespace(granted=True, decision="allow"), preferences=fake_preferences)

        with patch.object(cli, "ensure_consent", side_effect=cli.ConsentError("Need consent")), \
            patch.object(cli, "prompt_for_consent", return_value="accepted") as prompt_mock, \
            patch.object(cli, "grant_consent", return_value=fake_config) as grant_mock, \
            patch.object(cli, "load_config", return_value=fake_config), \
            patch.object(cli, "resolve_mode", return_value=ModeResolution(requested="auto", resolved="local", reason="Local analysis enforced")), \
            patch.object(cli.ZipAnalyzer, "analyze", return_value={
                "local_mode_label": "Local Analysis Mode",
                "resolved_mode": "local",
                "metadata_output": str(args.metadata_output),
                "file_summary": {},
                "languages": {},
                "frameworks": [],
                "collaboration": {"classification": "individual", "contributors": {}, "primary_contributor": None},
                "scan_duration_seconds": 0.1,
                "skills": [],
            }) as analyze_mock:
            exit_code = cli._handle_analyze(args)

        self.assertEqual(exit_code, 0)
        prompt_mock.assert_called_once()
        grant_mock.assert_called_once()
        analyze_mock.assert_called_once()

    def test_analyze_external_permission_denied_returns_error(self) -> None:
        archive_path = Path(self._tmpdir.name) / "sample.zip"
        from zipfile import ZipFile

        with ZipFile(archive_path, "w"):
            pass

        args = SimpleNamespace(
            archive=str(archive_path),
            metadata_output=Path(self._tmpdir.name) / "meta.jsonl",
            summary_output=Path(self._tmpdir.name) / "summary.json",
            analysis_mode="external",
            summary_to_stdout=False,
            quiet=False,
            project_id=None,
            db_dir=None,
        )

        fake_preferences = SimpleNamespace(labels={"local_mode": "Local Analysis Mode"})
        fake_config = SimpleNamespace(preferences=fake_preferences)

        with patch.object(cli, "ensure_consent", return_value=SimpleNamespace(granted=True, decision="allow")), \
            patch.object(cli, "load_config", return_value=fake_config), \
            patch.object(cli, "resolve_mode", return_value=ModeResolution(requested="external", resolved="external", reason="External allowed")), \
            patch.object(cli, "ensure_external_permission", side_effect=ExternalPermissionDenied("Blocked by user")), \
            patch("sys.stderr", new_callable=io.StringIO) as fake_err:
            exit_code = cli._handle_analyze(args)

        self.assertEqual(exit_code, 6)
        error_output = fake_err.getvalue()
        self.assertIn("ExternalPermissionDenied", error_output)
        self.assertIn("Blocked by user", error_output)

    def test_config_show_and_reset(self) -> None:
        fake_consent = SimpleNamespace(granted=True, decision="allow", timestamp="2024-01-01", source="cli")
        fake_preferences = SimpleNamespace(last_opened_path="/tmp", analysis_mode="local", theme="dark", labels={"local_mode": "Local Analysis Mode"})
        fake_config_state = SimpleNamespace(consent=fake_consent, preferences=fake_preferences)

        args_show = SimpleNamespace(command="config", config_action="show")
        with patch.object(cli, "load_config", return_value=fake_config_state):
            with patch("sys.stdout", new_callable=io.StringIO) as fake_out:
                exit_code = cli._handle_config(args_show)
        self.assertEqual(exit_code, 0)
        self.assertIn("local", fake_out.getvalue())

        args_reset = SimpleNamespace(command="config", config_action="reset")
        with patch.object(cli, "reset_config", return_value=fake_config_state):
            with patch("sys.stdout", new_callable=io.StringIO) as fake_out:
                exit_code = cli._handle_config(args_reset)
        self.assertEqual(exit_code, 0)
        self.assertIn("Configuration reset", fake_out.getvalue())

    # new tests
    def test_summarize_projects_markdown_without_llm(self) -> None:
        """summarize-projects: basic markdown output, no LLM."""
        args = SimpleNamespace(
            db_dir=Path(self._tmpdir.name) / "db",
            user="alice",
            limit=2,
            use_llm=False,
            format="markdown",
        )

        fake_conn = object()
        fake_rows = [
            {"project_id": "p1", "snapshot": {"languages": {"Python": 1}}},
            {"project_id": "p2", "snapshot": {"languages": {"JavaScript": 1}}},
        ]
        fake_rankings = [
            SimpleNamespace(project_id="p1", score=0.9),
            SimpleNamespace(project_id="p2", score=0.8),
        ]
        # Summary objects that work whether you use export_markdown
        # or access .markdown / .title directly.
        fake_summaries = [
            SimpleNamespace(title="Project One", markdown="# Summary for Project One"),
            SimpleNamespace(title="Project Two", markdown="# Summary for Project Two"),
        ]

        with patch.object(cli, "open_db", return_value=fake_conn), \
             patch.object(cli, "fetch_latest_snapshots", return_value=fake_rows), \
             patch.object(cli, "rank_projects_from_snapshots", return_value=fake_rankings), \
             patch.object(cli, "generate_top_project_summaries", return_value=fake_summaries) as gen_mock, \
             patch.object(cli, "export_markdown", side_effect=lambda s: s.markdown), \
             patch.object(cli, "build_default_llm") as build_llm_mock, \
             patch.object(cli, "close_db") as close_db_mock, \
             patch("sys.stdout", new_callable=io.StringIO) as fake_out:
            exit_code = cli._handle_summarize_projects(args)

        self.assertEqual(exit_code, 0)

        # DB opened & closed
        close_db_mock.assert_called_once()

        # summaries generated
        gen_mock.assert_called_once()

        # LLM must NOT be built
        build_llm_mock.assert_not_called()

        out = fake_out.getvalue()
        self.assertIn("Project One", out)
        self.assertIn("Project Two", out)

    def test_summarize_projects_json_with_llm(self) -> None:
        """summarize-projects: JSON output and LLM path is exercised."""
        args = SimpleNamespace(
            db_dir=Path(self._tmpdir.name) / "db",
            user=None,
            limit=1,
            use_llm=True,
            format="json",
        )

        fake_conn = object()
        fake_rows = [
            {"project_id": "p1", "snapshot": {"languages": {"Python": 1}}},
        ]
        fake_rankings = [SimpleNamespace(project_id="p1", score=0.9)]
        fake_llm = object()
        fake_summary_dict = {"title": "Top Project", "score": 0.9}

        with patch.object(cli, "open_db", return_value=fake_conn), \
             patch.object(cli, "fetch_latest_snapshots", return_value=fake_rows), \
             patch.object(cli, "rank_projects_from_snapshots", return_value=fake_rankings), \
             patch.object(cli, "build_default_llm", return_value=fake_llm) as build_llm_mock, \
             patch.object(cli, "generate_top_project_summaries", return_value=[fake_summary_dict]) as gen_mock, \
             patch.object(cli, "close_db") as close_db_mock, \
             patch("sys.stdout", new_callable=io.StringIO) as fake_out:
            exit_code = cli._handle_summarize_projects(args)

        self.assertEqual(exit_code, 0)

        # LLM builder used
        build_llm_mock.assert_called_once()

        # generate_top_project_summaries sees llm + use_llm=True
        _, gen_kwargs = gen_mock.call_args
        self.assertTrue(gen_kwargs.get("use_llm"))
        self.assertIs(gen_kwargs.get("llm"), fake_llm)

        # DB closed
        close_db_mock.assert_called_once()

        # Output is valid JSON and contains the summary fields
        out = fake_out.getvalue()
        parsed = json.loads(out)
        self.assertIsInstance(parsed, list)
        self.assertEqual(parsed[0]["title"], "Top Project")
        self.assertEqual(parsed[0]["score"], 0.9)

    def test_print_human_summary_contributor_label(self) -> None:
        summary = {
            "resolved_mode": "local",
            "metadata_output": "meta.jsonl",
            "file_summary": {"file_count": 1, "total_bytes": 10},
            "languages": {"Python": 1},
            "frameworks": [],
            "collaboration": {
                "classification": "collaborative",
                "contributors (commits, PRs, issues, reviews)": {
                    "alice": "[3, 1, 2, 4]"
                },
            },
            "scan_duration_seconds": 0.1,
        }
        args = SimpleNamespace(summary_output="summary.json", quiet=False)
        with patch("sys.stdout", new_callable=io.StringIO) as fake_out:
            cli._print_human_summary(summary, args)
        output = fake_out.getvalue()
        self.assertIn("Contributors (commits, PRs, issues, reviews):", output)
        self.assertIn(" - alice: 3, 1, 2, 4", output)


if __name__ == "__main__":
    unittest.main()
