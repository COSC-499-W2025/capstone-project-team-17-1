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
from capstone.modes import ModeResolution  # noqa: E402


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
        )

        with patch("sys.stderr", new_callable=io.StringIO) as fake_err:
            exit_code = cli._handle_analyze(args)

        self.assertEqual(exit_code, 5)
        self.assertIn("Archive path must not be empty", fake_err.getvalue())


if __name__ == "__main__":
    unittest.main()
