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

from capstone import config, file_store, storage
from capstone.config import load_config
from capstone.consent import grant_consent
from capstone.modes import ModeResolution, resolve_mode
from capstone.zip_analyzer import (
    InvalidArchiveError,
    ZipAnalyzer,
    _build_author_email_map,
    _parse_contrib_data,
)


class ZipAnalyzerIntegrationTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmpdir.name)
        self._original_base_dir = storage.BASE_DIR
        self._original_current_user = storage.CURRENT_USER
        self._original_files_root = file_store.DEFAULT_FILES_ROOT
        storage.close_db()
        storage.BASE_DIR = self.tmp_path
        storage.CURRENT_USER = None
        file_store.DEFAULT_FILES_ROOT = self.tmp_path / "files"
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
        self.addCleanup(setattr, storage, "BASE_DIR", self._original_base_dir)
        self.addCleanup(setattr, storage, "CURRENT_USER", self._original_current_user)
        self.addCleanup(setattr, file_store, "DEFAULT_FILES_ROOT", self._original_files_root)

    def _make_archive(
        self,
        name: str = "sample.zip",
        *,
        git_log_path: str = ".git/logs/git_log",
        git_log_encoding: str = "utf-8",
    ) -> Path:
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
            zf.writestr(git_log_path, git_log.encode(git_log_encoding))
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
        self.assertIsInstance(summary["frameworks"], list)
        self.assertIn("Python", summary["languages"])
        self.assertTrue(summary["skills"])
        self.assertIn("archive_file_id", summary)
        self.assertIsInstance(summary["archive_file_id"], str)
        self.assertFalse(summary["archive_dedup"])

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
        cursor = conn.execute("SELECT COUNT(*) FROM project_analysis WHERE project_id = ?", ("sample",))
        self.assertEqual(cursor.fetchone()[0], 1)
        # uploaded archive should be tracked in files/uploads
        file_row = conn.execute("SELECT ref_count FROM files WHERE file_id = ?", (summary["archive_file_id"],)).fetchone()
        self.assertIsNotNone(file_row)
        upload_count = conn.execute("SELECT COUNT(*) FROM uploads WHERE file_id = ?", (summary["archive_file_id"],)).fetchone()[0]
        self.assertEqual(upload_count, 1)

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

    def test_analyze_archive_supports_utf16_git_log(self) -> None:
        archive_path = self._make_archive(
            name="utf16.zip",
            git_log_path="git_log.txt",
            git_log_encoding="utf-16",
        )
        metadata_path = self.tmp_path / "out" / "metadata_utf16.jsonl"
        summary_path = self.tmp_path / "out" / "summary_utf16.json"

        grant_consent()
        mode = resolve_mode("auto", load_config().consent)
        analyzer = ZipAnalyzer()

        summary = analyzer.analyze(
            zip_path=archive_path,
            metadata_path=metadata_path,
            summary_path=summary_path,
            mode=mode,
            preferences=load_config().preferences,
            project_id="sample_utf16",
            db_dir=self.tmp_path / "db",
        )

        self.assertEqual(summary["collaboration"]["classification"], "collaborative")
        self.assertIn("primary_contributor", summary["collaboration"])
        self.assertFalse(
            any(
                warning.get("error") == "NonUtf8" and warning.get("path", "").endswith("git_log.txt")
                for warning in summary.get("warnings", [])
            )
        )

    def test_duplicate_archive_is_deduplicated(self) -> None:
        archive_path = self._make_archive()
        metadata_path = self.tmp_path / "out" / "metadata.jsonl"
        summary_path = self.tmp_path / "out" / "summary.json"

        grant_consent()
        mode = resolve_mode("auto", load_config().consent)
        analyzer = ZipAnalyzer()

        first = analyzer.analyze(
            zip_path=archive_path,
            metadata_path=metadata_path,
            summary_path=summary_path,
            mode=mode,
            preferences=load_config().preferences,
            project_id="sample",
            db_dir=self.tmp_path / "db",
        )
        second = analyzer.analyze(
            zip_path=archive_path,
            metadata_path=metadata_path,
            summary_path=summary_path,
            mode=mode,
            preferences=load_config().preferences,
            project_id="sample2",
            db_dir=self.tmp_path / "db",
        )

        self.assertEqual(first["archive_file_id"], second["archive_file_id"])
        self.assertTrue(second["archive_dedup"])

        conn = storage.open_db(self.tmp_path / "db")
        ref_count = conn.execute("SELECT ref_count FROM files WHERE file_id = ?", (first["archive_file_id"],)).fetchone()[0]
        self.assertEqual(ref_count, 2)
        upload_count = conn.execute("SELECT COUNT(*) FROM uploads WHERE file_id = ?", (first["archive_file_id"],)).fetchone()[0]
        self.assertEqual(upload_count, 2)


class ParseContribDataTestCase(unittest.TestCase):
    """Unit tests for _parse_contrib_data."""

    def test_list_format(self):
        self.assertEqual(_parse_contrib_data([5, 200, 2]), (5, 200, 2))

    def test_string_format(self):
        self.assertEqual(_parse_contrib_data("[5, 200, 2]"), (5, 200, 2))

    def test_bare_int(self):
        self.assertEqual(_parse_contrib_data(5), (5, 0, 0))

    def test_float_treated_as_int(self):
        self.assertEqual(_parse_contrib_data(3.7), (3, 0, 0))

    def test_empty_string(self):
        self.assertEqual(_parse_contrib_data(""), (0, 0, 0))

    def test_none(self):
        self.assertEqual(_parse_contrib_data(None), (0, 0, 0))

    def test_partial_list_one_element(self):
        self.assertEqual(_parse_contrib_data([3]), (3, 0, 0))

    def test_partial_list_two_elements(self):
        self.assertEqual(_parse_contrib_data([3, 100]), (3, 100, 0))

    def test_string_single_value(self):
        self.assertEqual(_parse_contrib_data("[7]"), (7, 0, 0))

    def test_tuple_format(self):
        self.assertEqual(_parse_contrib_data((1, 2, 3)), (1, 2, 3))

    def test_string_no_spaces(self):
        self.assertEqual(_parse_contrib_data("[10,50,4]"), (10, 50, 4))


class BuildAuthorEmailMapTestCase(unittest.TestCase):
    """Unit tests for _build_author_email_map."""

    def test_extracts_emails_from_commit_lines(self):
        lines = [
            "commit:abc123|Alice Example|alice@example.com|1700000000|Add feature",
            "commit:def456|Bob Smith|bob@example.com|1700000001|Fix bug",
        ]
        result = _build_author_email_map(lines)
        self.assertEqual(result["Alice Example"], "alice@example.com")
        self.assertEqual(result["Bob Smith"], "bob@example.com")

    def test_skips_users_noreply_github_com(self):
        lines = [
            "commit:abc|Alice|12345+alice@users.noreply.github.com|1700000000|msg",
        ]
        result = _build_author_email_map(lines)
        self.assertNotIn("Alice", result)

    def test_skips_noreply_github_com(self):
        lines = [
            "commit:abc|Alice|alice@noreply.github.com|1700000000|msg",
        ]
        result = _build_author_email_map(lines)
        self.assertNotIn("Alice", result)

    def test_skips_bare_noreply_address(self):
        lines = [
            "commit:abc|Alice|noreply@github.com|1700000000|msg",
        ]
        result = _build_author_email_map(lines)
        self.assertNotIn("Alice", result)

    def test_skips_bot_authors(self):
        lines = [
            "commit:abc|dependabot[bot]|dependabot@github.com|1700000000|bump",
        ]
        result = _build_author_email_map(lines)
        self.assertNotIn("dependabot[bot]", result)

    def test_ignores_non_commit_lines(self):
        lines = [
            "Alice Example|alice@example.com|some random line",
            "0000 1111 Alice <alice@example.com> 1700000000 +0000\tcommit",
        ]
        result = _build_author_email_map(lines)
        self.assertEqual(result, {})

    def test_first_occurrence_wins(self):
        lines = [
            "commit:aaa|Alice|first@example.com|1700000000|First",
            "commit:bbb|Alice|second@example.com|1700000001|Second",
        ]
        result = _build_author_email_map(lines)
        self.assertEqual(result["Alice"], "first@example.com")

    def test_empty_input(self):
        result = _build_author_email_map([])
        self.assertEqual(result, {})

    def test_missing_email_field(self):
        # Line has only 2 pipe-separated fields after "commit:"
        lines = ["commit:abc|AliceOnly"]
        result = _build_author_email_map(lines)
        self.assertEqual(result, {})


# ---------------------------------------------------------------------------
# Integration tests: users / user_projects / contributor_stats
# ---------------------------------------------------------------------------

_REFLOG_HEADER = (
    "0000000000000000000000000000000000000000 "
    "1111111111111111111111111111111111111111 "
)


def _reflog_line(name: str, email: str, ts: int = 1700000000) -> str:
    return f"{_REFLOG_HEADER}{name} <{email}> {ts} +0000\tcommit\n"


class ZipContributorStorageTestCase(unittest.TestCase):
    """Integration tests: ZIP analysis writes users/user_projects/contributor_stats."""

    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmpdir.name)
        self._original_base_dir = storage.BASE_DIR
        self._original_current_user = storage.CURRENT_USER
        self._original_files_root = file_store.DEFAULT_FILES_ROOT
        storage.close_db()
        storage.BASE_DIR = self.tmp_path
        storage.CURRENT_USER = None
        file_store.DEFAULT_FILES_ROOT = self.tmp_path / "files"
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
        self.addCleanup(setattr, storage, "BASE_DIR", self._original_base_dir)
        self.addCleanup(setattr, storage, "CURRENT_USER", self._original_current_user)
        self.addCleanup(setattr, file_store, "DEFAULT_FILES_ROOT", self._original_files_root)

    def _make_archive(self, git_log_content: str, name: str = "project.zip") -> Path:
        archive_path = self.tmp_path / name
        with ZipFile(archive_path, "w") as zf:
            zf.writestr("src/main.py", "print('hello')\n")
            zf.writestr("README.md", "# Project\n")
            zf.writestr("requirements.txt", "flask==2.2.0\n")
            zf.writestr("git_log.txt", git_log_content.encode("utf-8"))
        return archive_path

    def _run_analyze(self, archive_path: Path, project_id: str) -> None:
        grant_consent()
        mode = resolve_mode("auto", load_config().consent)
        analyzer = ZipAnalyzer()
        analyzer.analyze(
            zip_path=archive_path,
            metadata_path=self.tmp_path / "out" / "meta.jsonl",
            summary_path=self.tmp_path / "out" / "summary.json",
            mode=mode,
            preferences=load_config().preferences,
            project_id=project_id,
            db_dir=self.tmp_path / "db",
        )

    def test_human_contributors_stored_in_users_table(self):
        git_log = (
            _reflog_line("Alice Example", "alice@example.com", 1700000000)
            + _reflog_line("Bob Smith", "bob@example.com", 1700000100)
        )
        self._run_analyze(self._make_archive(git_log), "proj1")

        conn = storage.open_db(self.tmp_path / "db")
        rows = conn.execute("SELECT github_username FROM contributors ORDER BY github_username").fetchall()
        names = [r[0] for r in rows]
        self.assertIn("Alice Example", names)
        self.assertIn("Bob Smith", names)

    def test_contributors_linked_in_user_projects_table(self):
        git_log = (
            _reflog_line("Alice Example", "alice@example.com", 1700000000)
            + _reflog_line("Bob Smith", "bob@example.com", 1700000100)
        )
        self._run_analyze(self._make_archive(git_log), "proj2")

        conn = storage.open_db(self.tmp_path / "db")
        rows = conn.execute(
            "SELECT contributor_name FROM user_projects WHERE project_id = ? ORDER BY contributor_name",
            ("proj2",),
        ).fetchall()
        names = [r[0] for r in rows]
        self.assertIn("Alice Example", names)
        self.assertIn("Bob Smith", names)

    def test_contributor_stats_written_with_zip_source(self):
        git_log = _reflog_line("Alice Example", "alice@example.com", 1700000000)
        self._run_analyze(self._make_archive(git_log), "proj3")

        conn = storage.open_db(self.tmp_path / "db")
        row = conn.execute(
            "SELECT source, commits, score FROM contributor_stats WHERE project_id = ? AND contributor = ?",
            ("proj3", "Alice Example"),
        ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], "zip")
        self.assertGreaterEqual(row[1], 1)   # at least 1 commit
        self.assertGreaterEqual(row[2], 0.0)  # score >= 0

    def test_bot_contributors_excluded_from_users_table(self):
        git_log = (
            _reflog_line("Alice Example", "alice@example.com", 1700000000)
            + _reflog_line("dependabot[bot]", "dependabot@github.com", 1700000100)
        )
        self._run_analyze(self._make_archive(git_log), "proj4")

        conn = storage.open_db(self.tmp_path / "db")
        rows = conn.execute("SELECT github_username FROM contributors").fetchall()
        names = [r[0] for r in rows]
        self.assertIn("Alice Example", names)
        self.assertNotIn("dependabot[bot]", names)

    def test_bot_contributors_excluded_from_user_projects_table(self):
        git_log = (
            _reflog_line("Alice Example", "alice@example.com", 1700000000)
            + _reflog_line("github-actions[bot]", "actions@github.com", 1700000100)
        )
        self._run_analyze(self._make_archive(git_log), "proj5")

        conn = storage.open_db(self.tmp_path / "db")
        rows = conn.execute(
            "SELECT contributor_name FROM user_projects WHERE project_id = ?", ("proj5",)
        ).fetchall()
        names = [r[0] for r in rows]
        self.assertNotIn("github-actions[bot]", names)

    def test_bot_contributors_excluded_from_contributor_stats(self):
        git_log = (
            _reflog_line("Alice Example", "alice@example.com", 1700000000)
            + _reflog_line("renovate[bot]", "renovate@whitesource.com", 1700000100)
        )
        self._run_analyze(self._make_archive(git_log), "proj6")

        conn = storage.open_db(self.tmp_path / "db")
        row = conn.execute(
            "SELECT id FROM contributor_stats WHERE project_id = ? AND contributor = ?",
            ("proj6", "renovate[bot]"),
        ).fetchone()
        self.assertIsNone(row)

    def test_email_stored_via_commit_format(self):
        """When git_log uses commit:HASH|name|email format, email is stored in contributors."""
        git_log = (
            "commit:abc123|Alice Example|alice@example.com|1700000000|Add feature\n"
            "commit:def456|Alice Example|alice@example.com|1700000100|Fix bug\n"
        )
        self._run_analyze(self._make_archive(git_log), "proj7")

        conn = storage.open_db(self.tmp_path / "db")
        row = conn.execute(
            "SELECT email FROM contributors WHERE github_username = ?", ("Alice Example",)
        ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], "alice@example.com")


# ---------------------------------------------------------------------------
# Unit tests for _extract_contributors_from_zip (projects.py)
# ---------------------------------------------------------------------------


class ExtractContributorsFromZipTestCase(unittest.TestCase):
    """Tests for the _extract_contributors_from_zip helper in api/routes/projects.py."""

    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmpdir.name)
        self.files_root = self.tmp_path / "files"
        self._original_base_dir = storage.BASE_DIR
        self._original_current_user = storage.CURRENT_USER
        self._original_files_root = file_store.DEFAULT_FILES_ROOT
        storage.close_db()
        storage.BASE_DIR = self.tmp_path
        storage.CURRENT_USER = None
        file_store.DEFAULT_FILES_ROOT = self.files_root
        self.conn = storage.open_db(self.tmp_path / "db")
        self.addCleanup(self._tmpdir.cleanup)
        self.addCleanup(storage.close_db)
        self.addCleanup(setattr, storage, "BASE_DIR", self._original_base_dir)
        self.addCleanup(setattr, storage, "CURRENT_USER", self._original_current_user)
        self.addCleanup(setattr, file_store, "DEFAULT_FILES_ROOT", self._original_files_root)

    def _store_zip_with_git_log(self, git_log_content: str) -> str:
        """Create a zip file with a git_log.txt and store it via file_store."""
        zip_path = self.tmp_path / "test.zip"
        with ZipFile(zip_path, "w") as zf:
            zf.writestr("git_log.txt", git_log_content.encode("utf-8"))
        meta = file_store.ensure_file(
            self.conn,
            zip_path,
            original_name="test.zip",
            files_root=self.files_root,
        )
        return meta["file_id"]

    def test_valid_contributors_returned(self):
        from capstone.api.routes.projects import _extract_contributors_from_zip

        git_log = (
            "commit:abc|Alice Example|alice@example.com|1700000000|Add feature\n"
            "commit:def|Bob Smith|bob@example.com|1700000001|Fix bug\n"
        )
        file_id = self._store_zip_with_git_log(git_log)
        result = _extract_contributors_from_zip(self.conn, file_id)
        names = [r[0] for r in result]
        self.assertIn("Alice Example", names)
        self.assertIn("Bob Smith", names)

    def test_bot_names_excluded(self):
        from capstone.api.routes.projects import _extract_contributors_from_zip

        git_log = (
            "commit:abc|Alice Example|alice@example.com|1700000000|Add feature\n"
            "commit:def|dependabot[bot]|dependabot@github.com|1700000001|Bump dep\n"
            "commit:ghi|github-actions[bot]|actions@github.com|1700000002|CI\n"
        )
        file_id = self._store_zip_with_git_log(git_log)
        result = _extract_contributors_from_zip(self.conn, file_id)
        names = [r[0] for r in result]
        self.assertIn("Alice Example", names)
        self.assertNotIn("dependabot[bot]", names)
        self.assertNotIn("github-actions[bot]", names)

    def test_noreply_email_stripped(self):
        from capstone.api.routes.projects import _extract_contributors_from_zip

        git_log = (
            "commit:abc|Alice|12345+alice@users.noreply.github.com|1700000000|msg\n"
            "commit:def|Bob|bob@example.com|1700000001|msg\n"
        )
        file_id = self._store_zip_with_git_log(git_log)
        result = _extract_contributors_from_zip(self.conn, file_id)
        alice = next((r for r in result if r[0] == "Alice"), None)
        bob = next((r for r in result if r[0] == "Bob"), None)
        self.assertIsNotNone(alice)
        self.assertIsNone(alice[1])  # noreply email stripped
        self.assertIsNotNone(bob)
        self.assertEqual(bob[1], "bob@example.com")

    def test_deduplication_by_name(self):
        from capstone.api.routes.projects import _extract_contributors_from_zip

        git_log = (
            "commit:aaa|Alice|alice@example.com|1700000000|First\n"
            "commit:bbb|Alice|alice@example.com|1700000001|Second\n"
        )
        file_id = self._store_zip_with_git_log(git_log)
        result = _extract_contributors_from_zip(self.conn, file_id)
        alice_entries = [r for r in result if r[0] == "Alice"]
        self.assertEqual(len(alice_entries), 1)

    def test_empty_zip_returns_empty_list(self):
        from capstone.api.routes.projects import _extract_contributors_from_zip

        zip_path = self.tmp_path / "empty.zip"
        with ZipFile(zip_path, "w") as zf:
            zf.writestr("README.md", "# empty\n")
        meta = file_store.ensure_file(
            self.conn, zip_path, original_name="empty.zip", files_root=self.files_root
        )
        result = _extract_contributors_from_zip(self.conn, meta["file_id"])
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
