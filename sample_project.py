import json
import sqlite3
import sys
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from capstone.cli import main
from capstone.metrics_extractor import analyze_metrics, metrics_api, init_db, chronological_proj
from capstone.storage import close_db

def create_sample_zip(base_dir: Path) -> Path:
    project_dir = base_dir / "project"
    project_dir.mkdir()
    (project_dir / "src").mkdir()
    (project_dir / "docs").mkdir()
    (project_dir / "src" / "app.py").write_text("print('hello')\n", encoding="utf-8")
    (project_dir / "docs" / "README.md").write_text("# Sample\n", encoding="utf-8")
    (project_dir / "requirements.txt").write_text("flask==2.2.0\n", encoding="utf-8")

    # NEW: add a tiny fake git log so collaboration detection has data
    git_logs_dir = project_dir / ".git" / "logs"
    git_logs_dir.mkdir(parents=True, exist_ok=True)
    head_path = git_logs_dir / "HEAD"
    head_path.write_text(
        (
            "0000000000000000000000000000000000000000 "
            "1111111111111111111111111111111111111111 "
            "Demo User <demo@example.com> 1710000000 +0000\t"
            "clone: from https://example.com/demo.git\n"
            "1111111111111111111111111111111111111111 "
            "2222222222222222222222222222222222222222 "
            "Demo User <demo@example.com> 1710003600 +0000\t"
            "commit: Initial commit\n"
        ),
        encoding="utf-8",
    )

    zip_path = base_dir / "sample.zip"
    with ZipFile(zip_path, "w") as archive:
        for file in project_dir.rglob("*"):
            archive.write(file, file.relative_to(project_dir.parent))
    return zip_path


def run_demo() -> None:
    # keep db outside temp dir so windows doesn't delete an open .db file
    db_dir = ROOT / "demo_db"
    db_dir.mkdir(parents=True, exist_ok=True)

    # temp dir only for zip + json outputs
    with tempfile.TemporaryDirectory() as temp:
        temp_path = Path(temp)
        zip_path = create_sample_zip(temp_path)
        metadata_output = temp_path / "meta.jsonl"
        summary_output = temp_path / "summary.json"

        # grant consent
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
        cursor = conn.execute(
    "SELECT project_id, classification, primary_contributor, snapshot "
    "FROM project_analysis"
)

        rows = cursor.fetchall()

        print("\n--- project_analysis rows ---")
        for row in rows:
            project_id, classification, primary_contributor, snapshot = row
            print(project_id, classification, primary_contributor)
            snap = json.loads(snapshot)
            print(
                json.dumps(
                    {
                        "skills": snap.get("skills"),
                        "collaboration": snap.get("collaboration"),
                    },
                    indent=2,
                )
            )

    print("\n--- Metrics Extractor ---")
    # mock data
    contributor_details = [
        {
            "name": "jerrycan",
            "files": [
                {
                    "name": "speed.py",
                    "extension": ".py",
                    "lastModified": datetime.now() - timedelta(days=10),
                    "duration": 45,
                    "activity": 3,
                    "contributions": 12,
                },
                {
                    "name": "todo.md",
                    "extension": ".md",
                    "lastModified": datetime.now() - timedelta(days=5),
                    "duration": 15,
                    "activity": 2,
                    "contributions": 8,
                },
            ],
        }
    ]

    db_path = db_dir / "metrics.db"
    metrics = metrics_api(
        {"contributorDetails": contributor_details},
        proj_name="TestMetrics",
        db_path=db_path,
    )
    
    print(json.dumps(metrics, indent=2, default=str))
    
    print("\n--- Chronological Projects ---")
    projA = {"contributorDetails": contributor_details}
    projB = {"contributorDetails": [
            {
                "name": "bob",
                "files": [
                    {
                        "name": "hello.js",
                        "extension": ".js",                            
                        "lastModified": datetime.now() - timedelta(days=15),
                        "duration": 20,
                        "activity": 3,
                        "contributions": 8,
                    }
                ],
            }
        ]
    }
    projC = {
        "ongoing": True,
        "contributorDetails": [
            {
                "name": "bob",
                "files": [
                    {
                        "name": "welp.md",
                        "extension": ".md",                            
                        "lastModified": datetime.now() - timedelta(days=30),
                        "duration":8,
                        "activity": 2,
                        "contributions": 3,
                    }
                ],
            }
        ]
    }
        
    all_proj = {"ProjA": projA, "ProjB": projB, "ProjC": projC}
        
    for proj_name, proj_details in all_proj.items():
        metrics_api(proj_details, proj_name=proj_name, db_path=db_path)
            
    chron_list = chronological_proj(all_proj)
        
    for p in chron_list:
        start_str = p["start"].strftime("%Y-%m-%d") if p["start"] else "Undated"
        end_str = p["end"].strftime("%Y-%m-%d") if p["end"] else "Present"
        print(f"{start_str} - {end_str}: {p["name"]}")
    
    
    close_db()

if __name__ == "__main__":
    run_demo()
