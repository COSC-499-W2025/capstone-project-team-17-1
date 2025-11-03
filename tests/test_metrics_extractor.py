import sys
import unittest
from pathlib import Path
import tempfile
import os
import sqlite3
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
    
from capstone.metrics_extractor import analyze_metrics, metrics_api, init_db, save_metrics, handle_int


# helpers to make mock data -> files and db
def create_temp_dir():
    return tempfile.TemporaryDirectory()

def create_temp_db():
    temp_db = tempfile.NamedTemporaryFile(suffix = ".sqlite", delete = False)
    temp_db.close()
    conn = sqlite3.connect(temp_db.name)
    return conn, temp_db.name

# extracts 
def parse_mock_data(directory):
    files = os.listdir(directory)
    data = []
    
    for f in files:
        file_path = os.path.join(directory, f)
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read().splitlines()
        
        def get_value(index, key):
            if index < len(content) and key in content[index]:
                try:
                    return handle_int(content[index].split(":")[1].strip())
                except (ValueError, TypeError):
                    return 0
            return 0
        
        data.append({
            "name": "TestData",
            "files": [{
                "name": f,
                "extension": Path(f).suffix,
                "lastModified": datetime.now(),
                "duration": get_value(0, "duration"),
                "activity": get_value(1, "activity"),
                "contributions": get_value(2, "contributions"),
            }]
        })
        return data
    
class TestMetricsExtractor(unittest.TestCase):
    
    # tests if metrics were calculated correctly
    def test_analyze_metrics_summary(self):
        with create_temp_dir() as temp_dir:
            temp_path = Path(temp_dir)
            
            files = [
                {"name": "projectX.txt", "content": "duration: 24\nactivity: 32\ncontributions: 82"},
                {"name": "projectY.txt", "content": "duration: 3\nactivity: 5\ncontributions: 82"},
                {"name": "projectZ.txt", "content": "duration: 16\nactivity: 60\ncontributions: 82"}, 
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
            
    # tests if extracted metrics are saved to db
    def test_metrics_api_save_to_db(self):
        with create_temp_dir() as temp_dir:
            temp_path = Path(temp_dir)
            conn, db_path = create_temp_db()
            
            try:
                # mock files
                files = [
                    {"name": "data1.txt", "content": "duration: 5\nactivity: 30\ncontributions: 16"},
                    {"name": "data2.txt", "content": "duration: 28\nactivity: 256\ncontributions: 186"},
                ]
                
                # iterate through 
                for f in files:
                    with open(temp_path / f["name"], "w") as file:
                        file.write(f["content"])
                
                contributor_details = parse_mock_data(temp_path)
                result = metrics_api({"contributorDetails": contributor_details}, proj_name = "ProjectHEHE", db_path = db_path)
                
                self.assertIsNotNone(result)
                self.assertGreater(result["summary"]["durationDays"], 0)
                self.assertGreater(result["summary"]["volume"], 0)
                
                cursor = conn.cursor()
                row = cursor.execute("SELECT COUNT(*) FROM metrics_summary").fetchone()
                self.assertGreaterEqual(row[0], 1)
            
            finally:
                conn.close()
                os.remove(db_path)
        
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
        
if __name__ == "__main__":
    unittest.main()
    

