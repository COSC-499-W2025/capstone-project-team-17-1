
import unittest, tempfile, json, os
from pathlib import Path
from capstone.storage import open_db, store_analysis_snapshot
from capstone.timeline import write_projects_timeline, write_skills_timeline

class TimelineSmokeTest(unittest.TestCase):
    def test_exports(self):
        tmp = Path(tempfile.mkdtemp())
        conn = open_db(tmp)
        snap = {
            "file_summary": {"first_modified": "2024-01-01T00:00:00","last_modified":"2024-01-02T00:00:00","total_files": 2,"total_bytes": 10},
            "languages": {"python": 3},
            "frameworks": ["fastapi"],
            "collaboration": {"classification": "individual", "primary_contributor": "you"},
            "skills": [{"skill":"python","category":"language","score":1.0}],
        }
        store_analysis_snapshot(conn, project_id="demo", classification="individual", primary_contributor="you", snapshot=snap)
        out = tmp / "out"
        n1 = write_projects_timeline(tmp, out / "projects_timeline.csv")
        n2 = write_skills_timeline(tmp, out / "skills_timeline.csv")
        self.assertGreaterEqual(n1, 1)
        self.assertGreaterEqual(n2, 1)
        self.assertTrue((out / "projects_timeline.csv").exists())
        self.assertTrue((out / "skills_timeline.csv").exists())

if __name__ == "__main__":
    unittest.main()
