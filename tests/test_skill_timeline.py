import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from capstone.skills import build_skill_timeline  # noqa: E402
import capstone.timeline as tl  # noqa: E402


class SkillTimelineTests(unittest.TestCase):
    def test_build_skill_timeline(self):
        ts1 = datetime(2023, 1, 1)
        ts2 = datetime(2024, 4, 10)
        events = [
            ("python", "language", ts1, 1.0),
            ("python", "language", ts2, 2.0),
            ("docker", "tool", ts2, 1.0),
        ]
        timeline = build_skill_timeline(events)
        self.assertIn("python", timeline)
        py = timeline["python"]
        self.assertEqual(py["first_seen"], ts1.isoformat())
        self.assertEqual(py["last_seen"], ts2.isoformat())
        self.assertIn("2023", py["year_counts"])
        self.assertIn("2024-Q2", py["quarter_counts"])
        self.assertGreater(py["intensity"], 0)

    def test_exports_top_skills_by_year(self):
        # stub snapshots with skill_timeline
        sample_timeline = {
            "skills": [
                {
                    "skill": "python",
                    "category": "language",
                    "first_seen": "2023-01-01T00:00:00",
                    "last_seen": "2024-01-01T00:00:00",
                    "total_weight": 3.0,
                    "year_counts": {"2023": 1.0, "2024": 2.0},
                    "quarter_counts": {"2023-Q1": 1.0, "2024-Q1": 2.0},
                    "intensity": 1.0,
                }
            ]
        }

        def fake_iter(_conn):
            yield "demo", {"skill_timeline": sample_timeline, "skills": []}

        orig_iter = tl._iter_snapshots
        tl._iter_snapshots = fake_iter
        try:
            tmpdir = Path(tempfile.mkdtemp())
            out_csv = tmpdir / "skills.csv"
            out_json = tmpdir / "top_skills.json"
            rows = tl.write_skills_timeline(db_dir=None, out_csv=out_csv)
            years = tl.write_top_skills_by_year(db_dir=None, out_json=out_json, top_n=3)
            self.assertEqual(rows, 1)
            payload = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertIn("2024", payload)
            self.assertEqual(years, 2)  # two years in the payload
            self.assertTrue(out_csv.exists())
        finally:
            tl._iter_snapshots = orig_iter


if __name__ == "__main__":
    unittest.main()
