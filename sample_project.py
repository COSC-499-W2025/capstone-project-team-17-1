import json
import sqlite3
import sys
import tempfile
from pathlib import Path
from datetime import datetime
from zipfile import ZipFile
from dataclasses import dataclass
from typing import List

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from capstone.cli import main
from capstone.metrics_extractor import metrics_api
from capstone.company_profile import build_company_resume_lines
from capstone.company_qualities import extract_company_qualities

def create_sample_zip(base_dir: Path) -> Path:
    project_dir = base_dir / "project"
    project_dir.mkdir()
    (project_dir / "src").mkdir()
    (project_dir / "docs").mkdir()
    (project_dir / "src" / "app.py").write_text("print('hello')\n", encoding="utf-8")
    (project_dir / "docs" / "README.md").write_text("# Sample\n", encoding="utf-8")
    (project_dir / "requirements.txt").write_text("flask==2.2.0\n", encoding="utf-8")

    zip_path = base_dir / "sample.zip"
    with ZipFile(zip_path, "w") as archive:
        for file in project_dir.rglob("*"):
            archive.write(file, file.relative_to(project_dir.parent))
    return zip_path

@dataclass
class ProjectMatch:
    project_id: str
    score: float = 0.0
    required_coverage: float = 0.0
    preferred_coverage: float = 0.0
    keyword_overlap: float = 0.0
    recency_factor: float = 0.0
    matched_required: List[str] = None
    matched_preferred: List[str] = None
    matched_keywords: List[str] = None
    
    def post_init(self):
        if self.matched_required is None:
            self.matched_required = []
        if self.matched_preferred is None:
            self.matched_preferred = []
        if self.matched_keywords is None:
            self.matched_keywords = []

def run_demo() -> None:
    with tempfile.TemporaryDirectory() as temp:
        temp_path = Path(temp)
        zip_path = create_sample_zip(temp_path)
        metadata_output = temp_path / "meta.jsonl"
        summary_output = temp_path / "summary.json"
        db_dir = temp_path / "db"

        # Grant consent programmatically
        from capstone.consent import grant_consent

        grant_consent()

        args = [
            "analyze",
            str(zip_path),
            "--metadata-output",
            str(metadata_output),
            "--summary-output",
            str(summary_output),
            "--summary-to-stdout",
            "--project-id",
            "demo",
            "--db-dir",
            str(db_dir),
        ]
        main(args)

        print("\n--- metadata.jsonl ---")
        print(metadata_output.read_text("utf-8"))

        print("\n--- summary.json ---")
        print(summary_output.read_text("utf-8"))

        with sqlite3.connect(db_dir / "capstone.db") as conn:
            cursor = conn.execute("SELECT project_id, classification, primary_contributor, snapshot FROM project_analysis")
            rows = cursor.fetchall()
            
            print("\n--- project_analysis rows ---")
            for row in rows:
                project_id, classification, primary_contributor, snapshot = row
                print(project_id, classification, primary_contributor)
                snap = json.loads(snapshot)
                print(json.dumps({"skills": snap.get("skills"), "collaboration": snap.get("collaboration")}, indent=2))

        print("\n--- Metrics Extractor ---")
        # mock data
        contributor_details = [
            {
                "name": "jerrycan",
                "files": [
                    {
                        "name": "speed.py",
                        "extension": ".py",
                        "lastModified": datetime.now(),
                        "duration": 45,
                        "activity": 3,
                        "contributions": 12,
                    },
                    {
                        "name": "todo.md",
                        "extension": ".md",
                        "lastModified": datetime.now(),
                        "duration": 15,
                        "activity": 2,
                        "contributions": 8,
                    },
                ],
            }
        ]
        
        db_path = db_dir / "metrics.db"
        metrics = metrics_api({"contributorDetails": contributor_details}, proj_name = "TestMetrics", db_path=db_path)
        print(json.dumps(metrics, indent=2, default=str))

        print("\n--- Company Qualities ---")
        company_desc = """At McDonalds, we build scalable backend services in Python and Flask. 
                        We deploy to AWS and rely on SQL databases.
                        We are an innovative and customer-focused company that values diversity, collaboration, and a fast-paced, agile environment."""
        
        qualities = extract_company_qualities(company_desc, company_name="Mcdonalds")
        
        print(json.dumps(qualities.to_json(), indent=2))
        
        jd_profile = {
            "required_skills": qualities.preferred_skills,
            "preferred_skills": qualities.preferred_skills,
            "keywords": qualities.keywords
        }
        
        matches = [
            ProjectMatch(
                project_id = "behemoth",
                matched_required = ['python'],
                matched_preferred = ["python"],
                matched_keywords = ["python"]
            ),
            ProjectMatch(
                project_id = "demo-backend",
                matched_required = ['python', "flask", "sql"],
                matched_preferred = ["python", "flask", "sql"],
                matched_keywords = ["python", "flask", "sql", "aws"]
            )
        ]
        
        print("\n--- Resume Bullet Points ---")
        points = build_company_resume_lines(company_name="Mcdonalds", jd_profile=jd_profile, matches=matches, max_projects=2, max_skills_per_project=3)
        for line in points:
            print(line)

if __name__ == "__main__":
    run_demo()
