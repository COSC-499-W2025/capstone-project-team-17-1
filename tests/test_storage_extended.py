"""
Extended storage layer tests covering:
- GitHub token management (save / get / clear)
- Project overrides (upsert / fetch / partial update)
- Project evidence (store / fetch / limit)
- Database backup
- Snapshot JSON export
"""

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import capstone.storage as storage  # noqa: E402

_ORIGINAL_BASE_DIR = storage.BASE_DIR


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_db(tmp: Path) -> sqlite3.Connection:
    """
    Return an isolated database connection in *tmp*.

    We monkey-patch storage.BASE_DIR so that get_database_path() resolves to
    a temp path instead of the production AppData location.
    """
    storage.BASE_DIR = tmp
    return storage.open_db()


def _restore_base_dir():
    storage.BASE_DIR = _ORIGINAL_BASE_DIR


# ---------------------------------------------------------------------------
# GitHub token management
# ---------------------------------------------------------------------------

class GitHubTokenTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.tmp = Path(self._tmpdir.name)
        self.addCleanup(self._tmpdir.cleanup)
        self.addCleanup(storage.close_db)
        self.addCleanup(_restore_base_dir)

    # ------------------------------------------------------------------
    def test_get_token_returns_none_when_table_empty(self) -> None:
        _make_db(self.tmp)
        result = storage.get_github_token()
        self.assertIsNone(result)

    def test_save_and_get_token_roundtrip(self) -> None:
        _make_db(self.tmp)
        storage.save_github_token("ghp_test_token_abc123")
        result = storage.get_github_token()
        self.assertEqual(result, "ghp_test_token_abc123")

    def test_save_token_replaces_previous(self) -> None:
        _make_db(self.tmp)
        storage.save_github_token("first_token")
        storage.save_github_token("second_token")
        result = storage.get_github_token()
        # Only the latest token should be stored
        self.assertEqual(result, "second_token")

    def test_clear_token_removes_stored_value(self) -> None:
        _make_db(self.tmp)
        storage.save_github_token("ghp_will_be_cleared")
        storage.clear_github_token()
        result = storage.get_github_token()
        self.assertIsNone(result)

    def test_clear_token_is_idempotent_on_empty_table(self) -> None:
        _make_db(self.tmp)
        # Clearing when nothing is stored should not raise
        storage.clear_github_token()
        self.assertIsNone(storage.get_github_token())

    def test_save_then_clear_then_save_again(self) -> None:
        _make_db(self.tmp)
        storage.save_github_token("token_a")
        storage.clear_github_token()
        storage.save_github_token("token_b")
        self.assertEqual(storage.get_github_token(), "token_b")


# ---------------------------------------------------------------------------
# Schema reset
# ---------------------------------------------------------------------------

class SchemaResetTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.tmp = Path(self._tmpdir.name)
        self.addCleanup(self._tmpdir.cleanup)
        self.addCleanup(storage.close_db)
        self.addCleanup(_restore_base_dir)
        storage.BASE_DIR = self.tmp
        storage.CURRENT_USER = "ivy"
        storage._SCHEMA_READY.clear()
        self.addCleanup(setattr, storage, "CURRENT_USER", None)

    def test_open_db_resets_when_table_set_differs_from_expected(self) -> None:
        db_path = storage.get_database_path()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            CREATE TABLE legacy_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL
            )
            """
        )
        conn.commit()
        conn.close()

        live = storage.open_db()
        self.addCleanup(live.close)

        tables = {
            row[0]
            for row in live.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        self.assertIn("user", tables)
        self.assertIn("contributors", tables)
        self.assertNotIn("legacy_users", tables)


# ---------------------------------------------------------------------------
# Project overrides
# ---------------------------------------------------------------------------

class ProjectOverridesTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self._tmpdir.cleanup)
        self.addCleanup(storage.close_db)
        self.addCleanup(_restore_base_dir)
        self.conn = _make_db(Path(self._tmpdir.name))
        self.addCleanup(self.conn.close)

    def _make_project(self, project_id: str = "proj-1") -> str:
        """Insert a minimal project_analysis row so FK constraints pass."""
        storage.store_analysis_snapshot(
            self.conn,
            project_id=project_id,
            classification="individual",
            snapshot={},
        )
        return project_id

    # ------------------------------------------------------------------
    def test_fetch_overrides_returns_none_for_unknown_project(self) -> None:
        result = storage.fetch_project_overrides(self.conn, "nonexistent")
        self.assertIsNone(result)

    def test_upsert_and_fetch_basic_fields(self) -> None:
        pid = self._make_project("proj-basic")
        storage.upsert_project_overrides(
            self.conn,
            project_id=pid,
            key_role="Backend Developer",
            portfolio_blurb="Built the REST API.",
        )
        data = storage.fetch_project_overrides(self.conn, pid)
        self.assertIsNotNone(data)
        self.assertEqual(data["project_id"], pid)
        self.assertEqual(data["key_role"], "Backend Developer")
        self.assertEqual(data["portfolio_blurb"], "Built the REST API.")

    def test_upsert_resume_bullets_roundtrip(self) -> None:
        pid = self._make_project("proj-bullets")
        bullets = ["Designed the database schema", "Wrote unit tests", "Deployed to AWS"]
        storage.upsert_project_overrides(self.conn, project_id=pid, resume_bullets=bullets)
        data = storage.fetch_project_overrides(self.conn, pid)
        self.assertEqual(data["resume_bullets"], bullets)

    def test_upsert_selected_and_rank(self) -> None:
        pid = self._make_project("proj-rank")
        storage.upsert_project_overrides(self.conn, project_id=pid, selected=True, rank=2)
        data = storage.fetch_project_overrides(self.conn, pid)
        self.assertTrue(data["selected"])
        self.assertEqual(data["rank"], 2)

    def test_upsert_is_idempotent_and_merges_fields(self) -> None:
        pid = self._make_project("proj-merge")
        storage.upsert_project_overrides(self.conn, project_id=pid, key_role="Lead Dev")
        storage.upsert_project_overrides(self.conn, project_id=pid, portfolio_blurb="Updated blurb")
        data = storage.fetch_project_overrides(self.conn, pid)
        # Both fields should survive the second upsert
        self.assertEqual(data["key_role"], "Lead Dev")
        self.assertEqual(data["portfolio_blurb"], "Updated blurb")

    def test_upsert_raises_on_empty_project_id(self) -> None:
        with self.assertRaises((ValueError, Exception)):
            storage.upsert_project_overrides(self.conn, project_id="")

    def test_fetch_overrides_returns_none_on_empty_project_id(self) -> None:
        result = storage.fetch_project_overrides(self.conn, "")
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# Project evidence
# ---------------------------------------------------------------------------

class ProjectEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self._tmpdir.cleanup)
        self.addCleanup(storage.close_db)
        self.addCleanup(_restore_base_dir)
        self.conn = _make_db(Path(self._tmpdir.name))
        self.addCleanup(self.conn.close)

    def _make_project(self, project_id: str = "ev-proj") -> str:
        storage.store_analysis_snapshot(self.conn, project_id=project_id, snapshot={})
        return project_id

    # ------------------------------------------------------------------
    def test_fetch_evidence_empty_for_unknown_project(self) -> None:
        result = storage.fetch_project_evidence(self.conn, "ghost")
        self.assertEqual(result, [])

    def test_store_and_fetch_single_evidence(self) -> None:
        pid = self._make_project()
        storage.store_project_evidence(
            self.conn,
            pid,
            evidence_type="metric",
            label="Stars",
            value="42",
            source="GitHub",
        )
        rows = storage.fetch_project_evidence(self.conn, pid)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["evidence_type"], "metric")
        self.assertEqual(rows[0]["label"], "Stars")
        self.assertEqual(rows[0]["value"], "42")
        self.assertEqual(rows[0]["source"], "GitHub")
        self.assertEqual(rows[0]["project_id"], pid)

    def test_multiple_evidence_items_returned_newest_first(self) -> None:
        pid = self._make_project("ev-multi")
        for i in range(3):
            storage.store_project_evidence(
                self.conn, pid, evidence_type="feedback", label=f"Item {i}", value=str(i)
            )
        rows = storage.fetch_project_evidence(self.conn, pid)
        self.assertEqual(len(rows), 3)
        # Newest row should be last inserted (Item 2)
        self.assertEqual(rows[0]["label"], "Item 2")

    def test_fetch_evidence_with_limit(self) -> None:
        pid = self._make_project("ev-limit")
        for i in range(5):
            storage.store_project_evidence(self.conn, pid, evidence_type="other", value=str(i))
        rows = storage.fetch_project_evidence(self.conn, pid, limit=2)
        self.assertEqual(len(rows), 2)

    def test_fetch_evidence_limit_zero_returns_empty(self) -> None:
        pid = self._make_project("ev-limit-zero")
        storage.store_project_evidence(self.conn, pid, evidence_type="metric", value="1")
        rows = storage.fetch_project_evidence(self.conn, pid, limit=0)
        self.assertEqual(rows, [])

    def test_store_evidence_raises_on_empty_project_id(self) -> None:
        with self.assertRaises((ValueError, Exception)):
            storage.store_project_evidence(self.conn, "", evidence_type="metric")

    def test_store_evidence_raises_on_missing_evidence_type(self) -> None:
        pid = self._make_project("ev-no-type")
        with self.assertRaises((ValueError, Exception)):
            storage.store_project_evidence(self.conn, pid, evidence_type="")

    def test_evidence_optional_fields_can_be_none(self) -> None:
        pid = self._make_project("ev-nulls")
        storage.store_project_evidence(self.conn, pid, evidence_type="evaluation")
        rows = storage.fetch_project_evidence(self.conn, pid)
        self.assertEqual(len(rows), 1)
        self.assertIsNone(rows[0]["label"])
        self.assertIsNone(rows[0]["value"])
        self.assertIsNone(rows[0]["source"])

    def test_fetch_evidence_empty_string_project_id(self) -> None:
        result = storage.fetch_project_evidence(self.conn, "")
        self.assertEqual(result, [])


# ---------------------------------------------------------------------------
# Database backup
# ---------------------------------------------------------------------------

class DatabaseBackupTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.tmp = Path(self._tmpdir.name)
        self.addCleanup(self._tmpdir.cleanup)
        self.addCleanup(storage.close_db)
        self.addCleanup(_restore_base_dir)
        self.conn = _make_db(self.tmp)
        self.addCleanup(self.conn.close)

    def test_backup_creates_file_at_destination(self) -> None:
        dest = self.tmp / "backups" / "copy.db"
        result = storage.backup_database(self.conn, dest)
        self.assertTrue(dest.exists())
        self.assertGreater(dest.stat().st_size, 0)
        self.assertEqual(result, dest)

    def test_backup_creates_parent_directories(self) -> None:
        dest = self.tmp / "deep" / "nested" / "backup.db"
        storage.backup_database(self.conn, dest)
        self.assertTrue(dest.exists())

    def test_backup_is_a_valid_sqlite_database(self) -> None:
        dest = self.tmp / "valid.db"
        storage.backup_database(self.conn, dest)
        backup_conn = sqlite3.connect(dest)
        try:
            tables = {
                row[0]
                for row in backup_conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            self.assertIn("project_analysis", tables)
        finally:
            backup_conn.close()

    def test_backup_contains_stored_data(self) -> None:
        storage.store_analysis_snapshot(
            self.conn, project_id="snap-backup", snapshot={"x": 1}
        )
        dest = self.tmp / "data.db"
        storage.backup_database(self.conn, dest)
        backup_conn = sqlite3.connect(dest)
        try:
            row = backup_conn.execute(
                "SELECT project_id FROM project_analysis WHERE project_id = ?",
                ("snap-backup",),
            ).fetchone()
            self.assertIsNotNone(row)
        finally:
            backup_conn.close()


# ---------------------------------------------------------------------------
# Snapshot JSON export
# ---------------------------------------------------------------------------

class SnapshotExportTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.tmp = Path(self._tmpdir.name)
        self.addCleanup(self._tmpdir.cleanup)
        self.addCleanup(storage.close_db)
        self.addCleanup(_restore_base_dir)
        self.conn = _make_db(self.tmp)
        self.addCleanup(self.conn.close)

    def test_export_empty_db_returns_zero_and_writes_empty_list(self) -> None:
        out = self.tmp / "out.json"
        count = storage.export_snapshots_to_json(self.conn, out)
        self.assertEqual(count, 0)
        self.assertTrue(out.exists())
        data = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(data, [])

    def test_export_single_snapshot(self) -> None:
        storage.store_analysis_snapshot(
            self.conn,
            project_id="export-1",
            classification="team",
            primary_contributor="alice",
            snapshot={"lang": "Python"},
        )
        out = self.tmp / "single.json"
        count = storage.export_snapshots_to_json(self.conn, out)
        self.assertEqual(count, 1)
        records = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["project_id"], "export-1")
        self.assertEqual(records[0]["classification"], "team")
        self.assertEqual(records[0]["primary_contributor"], "alice")
        self.assertIn("snapshot", records[0])
        self.assertEqual(records[0]["snapshot"]["lang"], "Python")

    def test_export_multiple_snapshots(self) -> None:
        for i in range(3):
            storage.store_analysis_snapshot(
                self.conn, project_id=f"proj-{i}", snapshot={"index": i}
            )
        out = self.tmp / "multi.json"
        count = storage.export_snapshots_to_json(self.conn, out)
        self.assertEqual(count, 3)
        records = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(len(records), 3)

    def test_export_creates_parent_directories(self) -> None:
        out = self.tmp / "nested" / "deep" / "export.json"
        storage.export_snapshots_to_json(self.conn, out)
        self.assertTrue(out.exists())

    def test_export_output_is_valid_json(self) -> None:
        storage.store_analysis_snapshot(self.conn, project_id="json-valid", snapshot={})
        out = self.tmp / "valid.json"
        storage.export_snapshots_to_json(self.conn, out)
        # Should not raise
        result = json.loads(out.read_text(encoding="utf-8"))
        self.assertIsInstance(result, list)


if __name__ == "__main__":
    unittest.main()
