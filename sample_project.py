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

    zip_path = base_dir / "sample.zip"
    with ZipFile(zip_path, "w") as archive:
        for file in project_dir.rglob("*"):
            archive.write(file, file.relative_to(project_dir.parent))
    return zip_path


# using all the pretty printing helpers


def _banner(title: str) -> None:
    line = "=" * 60
    print(line)
    print(title)
    print(line)


def _section(title: str) -> None:
    print("\n" + "-" * 60)
    print(title)
    print("-" * 60)


def print_project_summary(summary: dict) -> None:
    """
    Demo-friendly CLI summary for the project analysis (summary.json content).
    """
    _banner("📦 Project Analysis — Local Analysis Mode")

    archive = summary.get("archive", "-")
    mode_label = summary.get("local_mode_label", summary.get("resolved_mode", "-"))

    fs = summary.get("file_summary", {}) or {}
    file_count = fs.get("file_count", 0)
    total_bytes = fs.get("total_bytes", 0)
    earliest = fs.get("earliest_modification", "-")
    latest = fs.get("latest_modification", "-")
    active_days = fs.get("active_days", 0)
    activity_breakdown = fs.get("activity_breakdown", {}) or {}

    languages = summary.get("languages", {}) or {}
    frameworks = summary.get("frameworks", []) or []

    lang_str = ", ".join(f"{lang} ({count})" for lang, count in languages.items()) or "-"
    fw_str = ", ".join(frameworks) if frameworks else "-"

    print(f"Archive        : {archive}")
    print(f"Mode           : {mode_label}")
    print(f"Files          : {file_count} ({total_bytes} bytes total)")
    print(f"Languages      : {lang_str}")
    print(f"Frameworks     : {fw_str}")
    print(f"Activity Span  : {earliest} → {latest}")
    print(f"Active Days    : {active_days}")
    if activity_breakdown:
        act_str = ", ".join(f"{k}({v})" for k, v in activity_breakdown.items())
        print(f"Activity Types : {act_str}")

    # Skills
    skills = summary.get("skills", []) or []
    if skills:
        _section("🧠 Detected Skills")
        for s in skills:
            name = s.get("skill", "-")
            cat = s.get("category", "-")
            conf = s.get("confidence", 0)
            print(f"- {name:<10} ({cat:<9})  confidence: {conf:.2f}")

    # Top skills by year
    top_by_year = summary.get("top_skills_by_year", {}) or {}
    if top_by_year:
        _section("📈 Top Skills by Year")
        for year, year_skills in sorted(top_by_year.items()):
            print(f"{year}:")
            for item in year_skills:
                print(f"  - {item.get('skill', '-')}"
                      f" ({item.get('weight', 0)})")

    # Collaboration
    collab = summary.get("collaboration", {}) or {}
    if collab:
        _section("👥 Collaboration")
        print(f"- Classification : {collab.get('classification', '-')}")
        primary = collab.get("primary_contributor") or "(not detected)"
        print(f"- Primary author : {primary}")


def print_metrics(metrics: dict) -> None:
    """
    Demo-friendly CLI summary for the metrics_api output.
    """
    if not metrics:
        return

    summary = metrics.get("summary", {}) or {}
    start = metrics.get("start", "-")
    end = metrics.get("end", "-")

    _section("📊 Metrics Summary")
    print(f"Duration        : {summary.get('durationDays', 0)} days")
    print(f"Start → End     : {start} → {end}")
    print(f"Frequency       : {summary.get('frequency', 0)} changes/day")
    print(f"Volume          : {summary.get('volume', 0)} changes")

    contrib_types = metrics.get("contributionTypes", {}) or {}
    if contrib_types:
        print("\nContribution types:")
        for k, v in contrib_types.items():
            print(f"  - {k:<5}: {v}")

    timeline = (metrics.get("timeLine") or {}).get("activityTimeline", []) or []
    if timeline:
        print("\nTimeline:")
        for row in timeline:
            print(f"  • {row.get('date', '-')}"
                  f" : {row.get('count', 0)} change(s)")


# main demo script


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
           # "--summary-to-stdout",
            "--project-id",
            "demo",
            "--db-dir",
            str(db_dir),
        ]
        main(args)

        # Show metadata raw (it's small and useful to see)
        print("\n--- metadata.jsonl ---")
        print(metadata_output.read_text("utf-8"))

        # Load summary JSON, but print it in a friendly way
        summary_text = summary_output.read_text("utf-8")
        summary_data = json.loads(summary_text)

        print()  # spacing
        print_project_summary(summary_data)
        print(f"\n(ℹ️ Raw summary JSON written to: {summary_output})")

    # Open the capstone DB and inspect project_analysis rows
    with sqlite3.connect(db_dir / "capstone.db") as conn:
     cursor = conn.execute(
        """
        SELECT id AS project_id, classification, primary_contributor, snapshot
        FROM project_analysis
        ORDER BY rowid DESC
        LIMIT 1
        """
    )
    row = cursor.fetchone()

    print("\n--- project_analysis (latest snapshot) ---")
    if row:
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

    # Pretty-print metrics instead of raw JSON
    print_metrics(metrics)
    print(f"\n(ℹ️ Metrics stored in: {db_path})")

    print("\n--- Chronological Projects ---")
    projA = {"contributorDetails": contributor_details}
    projB = {
        "contributorDetails": [
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
                        "duration": 8,
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
        print(f"{start_str} - {end_str}: {p['name']}")

    print("\n--- Chronological Skills ---")
    print("skill | category | first_seen -> last_seen | years(year:weight)")
    skill_timeline = (summary_data.get("skill_timeline") or {}).get("skills") or []
    for entry in skill_timeline:
        years = ", ".join(
            f"{y}:{w}" for y, w in (entry.get("year_counts") or {}).items()
        )
        print(
            f"{entry.get('skill')} | {entry.get('category')} | "
            f"{entry.get('first_seen')} -> {entry.get('last_seen')} | {years}"
        )

    top_by_year = summary_data.get("top_skills_by_year") or {}
    if top_by_year:
        print("Top skills by year:")
        for year, rows in sorted(top_by_year.items()):
            names = ", ".join(f"{r['skill']}({r['weight']})" for r in rows)
            print(f"  {year}: {names}")

    close_db()


if __name__ == "__main__":
    run_demo()
