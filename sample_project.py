import json
import sqlite3
import sys
import tempfile
from pathlib import Path

from zipfile import ZipFile

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from capstone.cli import main


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

        conn = sqlite3.connect(db_dir / "capstone.db")
        cursor = conn.execute("SELECT project_id, classification, primary_contributor, snapshot FROM project_analysis")
        rows = cursor.fetchall()
        print("\n--- project_analysis rows ---")
        for row in rows:
            project_id, classification, primary_contributor, snapshot = row
            print(project_id, classification, primary_contributor)
            snap = json.loads(snapshot)
            print(json.dumps({"skills": snap.get("skills"), "collaboration": snap.get("collaboration")}, indent=2))


if __name__ == "__main__":
    run_demo()
