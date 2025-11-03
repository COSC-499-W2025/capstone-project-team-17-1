import os
import sqlite3
import tempfile
from pathlib import Path
from datetime import datetime
from metrics_extractor import analyze_metrics, metrics_api, init_db, save_metrics

def create_temp_dir():
    return tempfile.TemporaryDirectory()

def create_temp_db():
    temp_db = tempfile.NameTemporaryFile(suffix=".sqlite", delete=false)
    temp_db.close()
    conn = sqlite3.connect(temp_db.name)
    return conn, temp_db.name

def parse_mock_files(directory):
    files = os.listdir(directory)
    return [{
        "name": "TestData",
        "files": [
            {
                "name": f,
                "extension": Path(f).suffix,
                "lastModified": datetime.now(),
                "duration": int(open(os.path.join(drectory, f)).read().splitlines()[0].split(":")[1]).strip()) if "duration" in open(os.path.join(directory, f)).read() else 0,
                "activity": int(open(os.path.join(drectory, f)).read().splitlines()[1].split(":")[1]).strip()) if "activity" in open(os.path.join(directory, f)).read() else 0,
                "contributions": int(open(os.path.join(directory, f)).read().splitlines()[2].split(":")[1]).strip()) if "contributions" in open(os.path.join(directory, f)).read() else 0,
            } for f in files
        ]
    }]
    
class TestMetricsExtractor(unittest.TestCase):
    def test_analyze_metrics_summary():
            
    def test_metrics_api_save_to_db():
            
    def test_empty_contributors():
        
    def test_invalid_numeric_entries():
            
if __name__ == "__main__":
    unittest.main()
    

