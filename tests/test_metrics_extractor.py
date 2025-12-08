import sys
import unittest
from pathlib import Path
import tempfile
import os
import sqlite3
from datetime import datetime
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
    
from capstone.metrics_extractor import (analyze_metrics, metrics_api, init_db, save_metrics, handle_int, chronological_proj,)


# helpers to make mock data -> files and db
def create_temp_dir():
    return tempfile.TemporaryDirectory()

def create_temp_db():
    temp_db = tempfile.NamedTemporaryFile(suffix = ".sqlite", delete = False)
    temp_db.close()
    conn = sqlite3.connect(temp_db.name)
    return conn, temp_db.name

# extracts data
def parse_mock_data(directory):
    files = os.listdir(directory)
    data = []
    
    for f in files:
        file_path = os.path.join(directory, f)
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read().splitlines()
        
        duration = handle_int((content[0].split(":")[1]).strip()) if len(content) > 0 and ":" in content[0] else 0
        activity = handle_int((content[1].split(":")[1]).strip()) if len(content) > 1 and ":" in content[1] else 0
        contributions = handle_int((content[2].split(":")[1]).strip()) if len(content) > 2 and ":" in content[2] else 0
        
        data.append({
            "name": "TestData",
            "files": [{
                "name": f,
                "extension": Path(f).suffix,
                "lastModified": datetime.now(),
                "duration": duration,
                "activity": activity,
                "contributions": contributions
            }]
        })
        return [{"name": "TestData", "files": data}]
    
class TestMetricsExtractor(unittest.TestCase):
    
    # create mock db and data
    def setUp(self):
        self.temp_db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.temp_db_file.name
        self.temp_db_file.close()
        self.conn = init_db(self.db_path)
        
        # contributor data
        self.contributor_details = [
            {
                "name": "Obama",
                "files": [
                    {
                        "name": "mcchicken.cvs",
                        "extension": ".cvs",
                        "lastModified": datetime.now(),
                        "duration": 27,
                        "activity": 156,
                        "contributions": 238
                    },
                    {
                        "name": "mcnugget.png",
                        "extension": ".png",
                        "lastModified": datetime.now(),
                        "duration": 2,
                        "activity": 4,
                        "contributions": 1
                    },
                ],
            }
        ]
        
        self.metrics = analyze_metrics({"contributorDetails": self.contributor_details})
        self.proj_name = "MetricsTest"
        
    # clean up mock run
    def tearDown(self):
        self.conn.close()
        Path(self.db_path).unlink(missing_ok=True)
        
        
    # TESTS START HERE
    # tests if metrics were calculated correctly
    def test_analyze_metrics_summary(self):
        with create_temp_dir() as temp_dir:
            temp_path = Path(temp_dir)
            
            files = [
                {"name": "projectX.txt", "content": "duration: 24\nactivity: 32\ncontributions: 82"},
                {"name": "projectY.txt", "content": "duration: 3\nactivity: 5\ncontributions: 82"},
                {"name": "projectZ.txt", "content": "duration: 16\nactivity: 60\ncontributions: 82"}
            ]
            for f in files:
                with open(temp_path / f["name"], "w") as file:
                    file.write(f["content"])
            
            contributor_details = parse_mock_data(temp_path)
            metrics = analyze_metrics({"contributorDetails": contributor_details})
            
            self.assertIsNotNone(metrics)
            self.assertGreater(metrics["summary"]["durationDays"], 0)
            self.assertGreater(metrics["summary"]["frequency"], 0)
            self.assertGreater(metrics["summary"]["volume"], 0)
            self.assertEqual(len(metrics["primaryContributors"]), 1)
        
    # tests if it can handle empty contributors scenario
    def test_empty_contributors(self):
        metrics = analyze_metrics({"contributorDetails": []})
        self.assertEqual(metrics["summary"]["durationDays"], 1)
        self.assertEqual(metrics["summary"]["frequency"], 1)
        self.assertEqual(metrics["summary"]["volume"], 1)
        self.assertEqual(len(metrics["primaryContributors"]), 0)
        self.assertEqual(metrics["timeLine"]["activityTimeline"], [])
        
    # tests if it can handle invalid metrics entries scenario
    def test_invalid_numeric_entries(self):
        with create_temp_dir() as temp_dir:
            temp_path = Path(temp_dir)
            
            # invalid content
            with open(temp_path / "error.txt", "w") as f:
                f.write("duration: six\nactivity: seven?\ncontributions: !!@!\n")
                
            contributor_details = parse_mock_data(temp_dir)
            metrics = analyze_metrics({"contributorDetails": contributor_details})
            self.assertEqual(metrics["summary"]["durationDays"], 1)
            self.assertEqual(metrics["summary"]["volume"], 1)
        
    # tests if metrics saves to db
    def test_save_metrics(self):
        save_metrics(self.conn, self.proj_name, self.metrics)
        cursor = self.conn.cursor()
        
        # check all three tables
        for table in ["metrics_summary", "metrics_types", "metrics_timeline"]:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            self.assertGreaterEqual(count, 1)
    
    # tests if analyzed projects are returned in order for resume output        
    def test_chronological_proj(self):
        # mock dates and multiple project inputs
        date1 = datetime(2024, 1, 20)
        date2 = datetime(2025, 8, 21)
        
        all_proj = {
            "ProjA": {
                "contributorDetails": [
                    {
                        "name": "jericho",
                        "files": [
                            {
                                "name": "frog.py",
                                "extension": ".py",                            
                                "lastModified": date1,
                                "duration": 25,
                                "activity": 4,
                                "contributions": 3
                            }
                        ],
                    }
                ]
            },
            "ProjB": {
                "contributorDetails": [
                    {
                        "name": "steve",
                        "files": [
                            {
                                "name": "minecraft.md",
                                "extension": ".md",                            
                                "lastModified": date2,
                                "duration": 14,
                                "activity": 8,
                                "contributions": 5
                            }
                        ],
                    }
                ]
            }
        }
        
        # there should be 2 projects in output
        result = chronological_proj(all_proj)
        self.assertEqual(len(result), 2)
        
        # order should be earliest to latest
        ordered_names = [p["name"] for p in result]
        self.assertEqual(ordered_names, ['ProjB', "ProjA"])
        
        self.assertIsNotNone(result[0]["start"])
        self.assertIsNotNone(result[1]["start"])
        self.assertEqual(result[0]["start"].date(), date2.date())
        self.assertEqual(result[1]["start"].date(), date1.date())
        
        self.assertEqual(result[0]["end"].date(), date2.date())
        self.assertEqual(result[1]["end"].date(), date1.date())
        
    # tests that from extracted metrics, dates of ongoing projects are outputted as start-present
    def test_chronological_proj_ongoing(self):
        start = datetime(2025, 9, 23)
        
        mock_metrics = {
            "summary": {"durationDays": 1, "frequency": 1, "volume": 1},
            "contributionTypes": {},
            "primaryContributors": [],
            "timeLine": {"activityTimeline": [], "periods": {"active": [], "inactive": []}},
            "start": start,
            "end": None
        }
        
        # make metrics_api use mock data from above
        with patch("capstone.metrics_extractor.metrics_api", return_value=mock_metrics):
            all_proj = {"ProjC": {"contributorDetails": []}}
            result = chronological_proj(all_proj)
        
        # list should only contain 1 proj
        self.assertEqual(len(result), 1)
        p = result[0]
            
        self.assertEqual(p["name"], "ProjC")
        self.assertEqual(p["start"], start)
        self.assertIsNone(p["end"])
        
        start_str = p["start"].strftime("%Y-%m-%d") if p["start"] else "Undated"
        end_str = p["end"].strftime("%Y-%m-%d") if p["end"] else "Present"
        output = f"{start_str} - {end_str}: {p["name"]}"
        
        self.assertEqual(output, "2025-09-23 - Present: ProjC")
    
    # tests that api computes and stores metrics to database
    def test_metrics_api(self):
        result = metrics_api({"contributorDetails": self.contributor_details}, proj_name = self.proj_name, db_path = self.db_path)
        
        # check metric objects exist
        self.assertIsNotNone(result)
        self.assertIn("summary", result)
        self.assertIn("contributionTypes", result)
        self.assertIn("primaryContributors", result)
        self.assertIn("timeLine", result)
        
        # verify db entries
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # check table inserts
        for table in ["metrics_summary", "metrics_types", "metrics_timeline"]:
            cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE proj_name=?", (self.proj_name,))
            count = cursor.fetchone()[0]
            self.assertGreaterEqual(count, 1)
            
        conn.close()
        
if __name__ == "__main__":
    unittest.main()
    

