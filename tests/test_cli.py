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


if __name__ == "__main__":
    unittest.main()
