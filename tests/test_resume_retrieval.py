import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from capstone.resume_retrieval import (
    build_resume_preview,
    describe_resume_schema,
    export_resume,
    insert_resume_entry,
    query_resume_entries,
    resolve_resume_projects,
    resume_to_json,
    resume_to_markdown,
)


PROJECT_SCHEMA = """
CREATE TABLE IF NOT EXISTS project_analysis(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id TEXT NOT NULL,
  project_name TEXT,
  classification TEXT,
  primary_contributor TEXT,
  snapshot TEXT NOT NULL,
  created_at TEXT NOT NULL
);
"""


class ResumeRetrievalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "capstone.db"
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(PROJECT_SCHEMA)
        self._seed_project("proj-1", {"project": "proj-1", "skills": [{"skill": "Python"}]})

    def tearDown(self):
        self.conn.close()
        self.tmp.cleanup()

    def _seed_project(self, project_id: str, snapshot: dict):
        self.conn.execute(
            """
            INSERT INTO project_analysis(project_id, project_name, classification, primary_contributor, snapshot, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (project_id, project_id, "demo", "alice", json.dumps(snapshot), "2024-01-01T00:00:00"),
        )
        self.conn.commit()

    def _create_sample_entries(self):
        insert_resume_entry(
            self.conn,
            section="Projects",
            title="Telemetry Platform",
            summary="Designed and shipped a metrics ingestion tool.",
            body="Details about metrics ingestion and alerting pipeline.",
            metadata={"start_date": "2024-01", "end_date": "2024-05"},
            projects=["proj-1"],
            skills=["Python", "SQL"],
            created_at="2024-06-01T00:00:00",
        )
        insert_resume_entry(
            self.conn,
            section="Skills",
            title="Python Expert",
            body="Hands-on experience with async tooling.",
            metadata={"expires_at": "2020-01-01T00:00:00"},
            skills=["python"],
            created_at="2019-01-01T00:00:00",
        )

    def test_schema_description(self):
        describe = describe_resume_schema(self.conn)
        self.assertIn("resume_entries", describe["tables"])
        self.assertEqual(describe["counts"]["resume_entries"], 0)

    def test_query_filters_and_outdated_handling(self):
        self._create_sample_entries()
        result = query_resume_entries(self.conn, sections=["projects"], keywords=["metrics"])
        self.assertEqual(len(result.entries), 1)
        entry = result.entries[0]
        self.assertEqual(entry.section, "projects")
        self.assertTrue(any("resume entries" in warning for warning in result.warnings))
        # outdated entry excluded by default
        self.assertEqual(len(result.entries), 1)
        result_with_outdated = query_resume_entries(self.conn, include_outdated=True)
        self.assertEqual(len(result_with_outdated.entries), 2)

    def test_preview_and_project_mapping(self):
        self._create_sample_entries()
        result = query_resume_entries(self.conn, sections=["projects"])
        preview = build_resume_preview(result, conn=self.conn)
        self.assertIn("sections", preview)
        self.assertTrue(preview["sections"])
        context = resolve_resume_projects(self.conn, result.entries)
        self.assertIn("proj-1", context)
        self.assertIsInstance(context["proj-1"], dict)

    def test_export_formats(self):
        self._create_sample_entries()
        result = query_resume_entries(self.conn)
        markdown = resume_to_markdown(result.entries)
        self.assertIn("Telemetry Platform", markdown)
        payload = resume_to_json(result.entries)
        self.assertIn("sections", payload)
        export_path = Path(self.tmp.name) / "resume.pdf"
        pdf_bytes = export_resume(result.entries, fmt="pdf", destination=export_path)
        self.assertTrue(export_path.exists())
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()
