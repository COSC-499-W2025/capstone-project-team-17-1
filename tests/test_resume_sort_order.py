import sys
import types
import sqlite3
import unittest
from pathlib import Path
from capstone import consent as consent_module

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

if not hasattr(consent_module, "ensure_or_prompt_consent"):
    consent_module.ensure_or_prompt_consent = lambda *args, **kwargs: "granted_existing"
if not hasattr(consent_module, "clear_external_permission"):
    consent_module.clear_external_permission = lambda *args, **kwargs: None
if not hasattr(consent_module, "request_external_service_permission"):
    consent_module.request_external_service_permission = lambda *args, **kwargs: True

dummy_cli = types.ModuleType("capstone.cli")
dummy_cli.main = lambda argv=None: 0
dummy_cli.prompt_project_metadata = lambda *args, **kwargs: {}
dummy_cli.pick_zip_file = lambda *args, **kwargs: ""
sys.modules["capstone.cli"] = dummy_cli

import main as app  # noqa: E402

sys.modules.pop("capstone.cli", None)


def _make_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE resumes (id TEXT PRIMARY KEY, updated_at TEXT)")
    conn.execute(
        """
        CREATE TABLE resume_sections (
            id TEXT PRIMARY KEY,
            resume_id TEXT NOT NULL,
            key TEXT,
            label TEXT,
            sort_order INTEGER NOT NULL,
            is_enabled INTEGER NOT NULL DEFAULT 1,
            updated_at TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE resume_items (
            id TEXT PRIMARY KEY,
            section_id TEXT NOT NULL,
            title TEXT,
            subtitle TEXT,
            start_date TEXT,
            end_date TEXT,
            location TEXT,
            content TEXT,
            bullets_json TEXT,
            metadata_json TEXT,
            sort_order INTEGER NOT NULL,
            is_enabled INTEGER NOT NULL DEFAULT 1,
            updated_at TEXT
        )
        """
    )
    return conn


class ResumeSortOrderTests(unittest.TestCase):
    def test_update_section_sort_order_rebalances_and_deduplicates(self):
        conn = _make_conn()
        conn.execute("INSERT INTO resumes (id, updated_at) VALUES ('r1', CURRENT_TIMESTAMP)")
        conn.executemany(
            """
            INSERT INTO resume_sections (id, resume_id, key, label, sort_order, is_enabled, updated_at)
            VALUES (?, 'r1', ?, ?, ?, 1, CURRENT_TIMESTAMP)
            """,
            [
                ("s1", "summary", "Summary", 1),
                ("s2", "education", "Education", 1),  # duplicate on purpose
                ("s3", "experience", "Experience", 3),
            ],
        )
        conn.commit()

        app._update_resume_section_fields(conn, section_id="s3", sort_order=1)

        rows = conn.execute(
            "SELECT id, sort_order FROM resume_sections WHERE resume_id = 'r1' ORDER BY sort_order, id"
        ).fetchall()
        self.assertEqual(rows, [("s3", 1), ("s1", 2), ("s2", 3)])

    def test_update_item_sort_order_rebalances_and_deduplicates(self):
        conn = _make_conn()
        conn.execute("INSERT INTO resumes (id, updated_at) VALUES ('r1', CURRENT_TIMESTAMP)")
        conn.execute(
            """
            INSERT INTO resume_sections (id, resume_id, key, label, sort_order, is_enabled, updated_at)
            VALUES ('s1', 'r1', 'experience', 'Experience', 1, 1, CURRENT_TIMESTAMP)
            """
        )
        conn.executemany(
            """
            INSERT INTO resume_items (
                id, section_id, title, subtitle, start_date, end_date, location, content,
                bullets_json, metadata_json, sort_order, is_enabled, updated_at
            ) VALUES (?, 's1', ?, '', '', '', '', '', '[]', '{}', ?, 1, CURRENT_TIMESTAMP)
            """,
            [
                ("i1", "A", 1),
                ("i2", "B", 1),  # duplicate on purpose
                ("i3", "C", 3),
            ],
        )
        conn.commit()

        app._update_resume_item_fields(conn, item_id="i3", sort_order=1)

        rows = conn.execute(
            "SELECT id, sort_order FROM resume_items WHERE section_id = 's1' ORDER BY sort_order, id"
        ).fetchall()
        self.assertEqual(rows, [("i3", 1), ("i1", 2), ("i2", 3)])


if __name__ == "__main__":
    unittest.main()
