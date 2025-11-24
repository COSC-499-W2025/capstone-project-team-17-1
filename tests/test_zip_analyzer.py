import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from capstone import config, storage
from capstone.config import load_config
from capstone.consent import grant_consent
from capstone.modes import ModeResolution, resolve_mode
from capstone.zip_analyzer import InvalidArchiveError, ZipAnalyzer


class ZipAnalyzerIntegrationTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmpdir.name)
        config_dir = self.tmp_path / "config"
        config_path = config_dir / "user_config.json"
        self._patchers = [
            patch.object(config, "CONFIG_DIR", config_dir),
            patch.object(config, "CONFIG_PATH", config_path),
        ]
        for patcher in self._patchers:
            patcher.start()
            self.addCleanup(patcher.stop)
        self.addCleanup(self._tmpdir.cleanup)
        self.addCleanup(storage.close_db)

    def _make_archive(self, name: str = "sample.zip") -> Path:
        archive_path = self.tmp_path / name
        with ZipFile(archive_path, "w") as zf:
            zf.writestr("src/app.py", "print('hello world')\n")
            zf.writestr("README.md", "# Sample\n")
            zf.writestr("requirements.txt", "flask==2.2.0\n")
            git_log = (
                "0000000000000000000000000000000000000000 "
                "1111111111111111111111111111111111111111 "
                "Alice Example <alice@example.com> 1700000000 +0000\tcommit\n"
                "1111111111111111111111111111111111111111 "
                "2222222222222222222222222222222222222222 "
                "Bob Example <bob@example.com> 1700000500 +0000\tcommit\n"
            )
            zf.writestr(".git/logs/HEAD", git_log)
        return archive_path

    def test_analyze_archive_generates_metadata_and_summary(self) -> None:
        archive_path = self._make_archive()
        metadata_path = self.tmp_path / "out" / "metadata.jsonl"
        summary_path = self.tmp_path / "out" / "summary.json"

        grant_consent()
        consent = load_config().consent
        mode = resolve_mode("auto", consent)
        analyzer = ZipAnalyzer()

        summary = analyzer.analyze(
            zip_path=archive_path,
            metadata_path=metadata_path,
            summary_path=summary_path,
            mode=mode,
            preferences=load_config().preferences,
            project_id="sample",
            db_dir=self.tmp_path / "db",
        )

        self.assertEqual(summary["resolved_mode"], "local")
        self.assertIn("local mode", summary["mode_reason"].lower())
        self.assertEqual(summary["collaboration"]["classification"], "collaborative")
        self.assertIn("Flask", summary["frameworks"])
        self.assertIn("Python", summary["languages"])
        self.assertTrue(summary["skills"])

        self.assertTrue(metadata_path.exists())
        records = [json.loads(line) for line in metadata_path.read_text("utf-8").splitlines() if line]
        self.assertEqual(len(records), 4)
        self.assertTrue(all(record["analysis_mode"] == "local" for record in records))

        self.assertTrue(summary_path.exists())
        summary_data = json.loads(summary_path.read_text("utf-8"))
        file_summary = summary_data["file_summary"]
        self.assertEqual(file_summary["file_count"], 4)
        self.assertGreaterEqual(file_summary["total_bytes"], 4)
        self.assertGreaterEqual(file_summary["activity_breakdown"].get("documentation", 0), 1)

        updated_prefs = load_config().preferences
        self.assertEqual(updated_prefs.analysis_mode, "local")
        self.assertIsNotNone(updated_prefs.last_opened_path)

        conn = storage.open_db(self.tmp_path / "db")
        cursor = conn.execute("SELECT COUNT(*) FROM project_analysis WHERE project_name = ?", ("sample",))
        self.assertEqual(cursor.fetchone()[0], 1)

    def test_invalid_extension_raises(self) -> None:
        analyzer = ZipAnalyzer()
        bogus = self.tmp_path / "not_a_zip.txt"
        bogus.write_text("oops", "utf-8")
        metadata_path = self.tmp_path / "meta.jsonl"
        summary_path = self.tmp_path / "summary.json"
        mode = ModeResolution(requested="local", resolved="local", reason="test")

        with self.assertRaises(InvalidArchiveError) as ctx:
            analyzer.analyze(bogus, metadata_path, summary_path, mode, load_config().preferences)

        self.assertEqual(ctx.exception.payload["error"], "InvalidInput")
        self.assertIn("Expected a .zip", ctx.exception.payload["detail"])


if __name__ == "__main__":
    unittest.main()
