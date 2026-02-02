import io
import sqlite3
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from capstone import storage, file_store


class FileStoreUnitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)

        # isolate DB and files root
        storage.close_db()
        storage.DB_DIR = Path(self.tmpdir.name) / "data"
        file_store.DEFAULT_FILES_ROOT = Path(self.tmpdir.name) / "files"

        self.conn = storage.open_db(storage.DB_DIR)

    def tearDown(self) -> None:
        storage.close_db()

    def _make_zip_file(self) -> Path:
        tmp_zip = Path(self.tmpdir.name) / "demo.zip"
        with zipfile.ZipFile(tmp_zip, "w") as zf:
            zf.writestr("src/app.py", "print('hi')\n")
            zf.writestr("README.md", "# Demo\n")
        return tmp_zip

    def test_ensure_file_deduplicates_and_tracks_uploads(self) -> None:
        zip_path = self._make_zip_file()

        first = file_store.ensure_file(
            self.conn,
            zip_path,
            original_name="demo.zip",
            source="unit",
            mime="application/zip",
        )
        self.assertFalse(first["dedup"])
        self.assertTrue(Path(first["path"]).exists())

        second = file_store.ensure_file(
            self.conn,
            zip_path,
            original_name="demo.zip",
            source="unit",
            mime="application/zip",
        )
        self.assertTrue(second["dedup"])
        self.assertEqual(first["file_id"], second["file_id"])

        ref_count = self.conn.execute(
            "SELECT ref_count FROM files WHERE file_id = ?",
            (first["file_id"],),
        ).fetchone()[0]
        self.assertEqual(ref_count, 2)

        upload_count = self.conn.execute(
            "SELECT COUNT(*) FROM uploads WHERE file_id = ?",
            (first["file_id"],),
        ).fetchone()[0]
        self.assertEqual(upload_count, 2)

    def test_open_file_reads_back_zip(self) -> None:
        zip_path = self._make_zip_file()
        meta = file_store.ensure_file(self.conn, zip_path, original_name="demo.zip", source="unit")

        with file_store.open_file(self.conn, meta["file_id"]) as fh:
            with zipfile.ZipFile(fh) as zf:
                names = zf.namelist()
                self.assertIn("src/app.py", names)
                self.assertIn("README.md", names)

    def test_restores_missing_blob_when_db_entry_exists(self) -> None:
        zip_path = self._make_zip_file()
        meta = file_store.ensure_file(self.conn, zip_path, original_name="demo.zip", source="unit")
        stored_path = Path(meta["path"])
        self.assertTrue(stored_path.exists())

        # remove physical file to simulate manual cleanup
        stored_path.unlink()
        self.assertFalse(stored_path.exists())

        # ingest same content again should recreate file and still dedup
        second = file_store.ensure_file(self.conn, zip_path, original_name="demo.zip", source="unit")
        self.assertTrue(second["dedup"])
        self.assertTrue(Path(second["path"]).exists())


if __name__ == "__main__":
    unittest.main()
