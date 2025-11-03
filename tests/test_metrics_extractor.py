import os
import sqlite3
import tempfile
from pathlib import Path
from datetime import datetime
from metrics_extractor import analyze_metrics, metrics_api, init_db, save_metrics

# helpers to make mock data -> files and db
def create_temp_dir():
    return tempfile.TemporaryDirectory()

def create_temp_db():
    temp_db = tempfile.NameTemporaryFile(suffix = ".sqlite", delete = false)
    temp_db.close()
    conn = sqlite3.connect(temp_db.name)
    return conn, temp_db.name

# extracts 
def parse_mock_data(directory):
    files = os.listdir(directory)
    return [{
        "name": "TestData",
        "files": [
            {
                "name": f,
                "extension": Path(f).suffix,
                "lastModified": datetime.now(),
                "duration": int(open(os.path.join(directory, f)).read().splitlines()[0].split(":")[1].strip()) if "duration" in open(os.path.join(directory, f)).read() else 0,
                "activity": int(open(os.path.join(directory, f)).read().splitlines()[1].split(":")[1].strip()) if "activity" in open(os.path.join(directory, f)).read() else 0,
                "contributions": int(open(os.path.join(directory, f)).read().splitlines()[2].split(":")[1].strip()) if "contributions" in open(os.path.join(directory, f)).read() else 0,
            } for f in files
        ]
    }]
    
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
            
            self.assertIsNotNon(metrics)
            self.assertGreater(metrics["summary"]["durationDays"], 0)
            self.assertGreater(metrics["summary"]["frequency"], 0)
            self.assertGreater(metrics["summary"]["volume"], 0)
            self.assertEqual(len(metrics["primaryContributors"]), 1)
            
    # tests if extracted metrics are saved to db
    def test_metrics_api_save_to_db(self):
        with create_temp_dir as temp_dir:
            temp_path = Path(temp_dir)
            conn, db_path = create_temp_db()
            
            try:
                # mock files
                files = [
                    {"name": "data1.txt", "content": "duration: 5\nactivity: 30\ncontributions: 16"},
                    {"name": "data2.txt", "content": "durationL 28\nactivity: 256\ncontributions: 186"},
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
    

