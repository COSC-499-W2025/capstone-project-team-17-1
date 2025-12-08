# tests/test_timeline_smoke.py
import unittest
import tempfile
from pathlib import Path

import capstone.timeline as tl
from capstone.timeline import write_projects_timeline, write_skills_timeline


class TimelineSmokeTest(unittest.TestCase):
    def test_exports(self):
        # --- stub timeline._iter_snapshots so we don't depend on DB schema ---
        sample_snap = {
            "file_summary": {
                "first_modified": "2024-01-01T00:00:00",
                "last_modified":  "2024-01-02T00:00:00",
                "total_files": 2,
                "total_bytes": 10,
            },
            "languages": {"python": 3, "javascript": 1},
            "frameworks": ["fastapi", "react"],
            "collaboration": {"classification": "individual", "primary_contributor": "you"},
            "skills": [
                {"skill": "python", "category": "language", "score": 1.0},
                {"skill": "fastapi", "category": "framework", "score": 0.7},
            ],
        }

        def fake_iter(_conn):
            yield "demo", sample_snap

        # Patch the private iterator
        orig_iter = tl._iter_snapshots
        tl._iter_snapshots = fake_iter
        try:
            out_dir = Path(tempfile.mkdtemp()) / "out"
            proj_csv = out_dir / "projects_timeline.csv"
            skills_csv = out_dir / "skills_timeline.csv"

            n_projects = write_projects_timeline(db_dir=None, out_csv=proj_csv)
            n_skills   = write_skills_timeline(db_dir=None, out_csv=skills_csv)

            # Files created
            self.assertTrue(proj_csv.exists(), "projects CSV not created")
            self.assertTrue(skills_csv.exists(), "skills CSV not created")

            # Return values sensible
            self.assertIsInstance(n_projects, int)
            self.assertIsInstance(n_skills, int)
            self.assertGreaterEqual(n_projects, 1)
            self.assertGreaterEqual(n_skills, 1)

            # Headers present
            proj_head = proj_csv.read_text(encoding="utf-8").splitlines()[0]
            skills_head = skills_csv.read_text(encoding="utf-8").splitlines()[0]
            self.assertIn("project_id", proj_head)
            self.assertIn("skill", skills_head)
        finally:
            # restore original
            tl._iter_snapshots = orig_iter


if __name__ == "__main__":
    unittest.main()
