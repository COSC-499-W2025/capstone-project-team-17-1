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

from capstone import storage  # noqa: E402
from capstone.project_detection import detect_node_electron_project  # noqa: E402


class StorageTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)

    def test_open_db_creates_directory_and_reuses_connection(self) -> None:
        base_dir = Path(self._tmpdir.name) / "db"
        conn1 = storage.open_db(base_dir)
        self.assertTrue(base_dir.exists())
        self.assertIsInstance(conn1, sqlite3.Connection)
        conn2 = storage.open_db(base_dir)
        self.assertIs(conn1, conn2)

    def tearDown(self) -> None:
        storage.close_db()


class ProjectDetectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self._tmpdir.name)
        self.addCleanup(self._tmpdir.cleanup)

    def test_detects_electron_project_and_generates_markdown(self) -> None:
        package_json = {
            "name": "sample-app",
            "dependencies": {"react": "^18.0.0", "electron": "^25.0.0"},
            "devDependencies": {"eslint": "^8.0.0"},
            "scripts": {"start": "electron .", "test": "npm test"},
        }
        (self.root / "package.json").write_text(json.dumps(package_json), encoding="utf-8")

        is_project, markdown = detect_node_electron_project(self.root)
        self.assertTrue(is_project)
        self.assertIn("Electron desktop application", markdown)
        self.assertIn("`start`", markdown)

    def test_returns_false_when_no_package_json(self) -> None:
        is_project, markdown = detect_node_electron_project(self.root)
        self.assertFalse(is_project)
        self.assertEqual(markdown, "")


if __name__ == "__main__":
    unittest.main()
