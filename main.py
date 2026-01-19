import json
import os
import sqlite3
import sys
import tempfile
import threading
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Iterable, List
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from capstone.cli import main
from capstone.company_profile import build_company_resume_lines
from capstone.company_qualities import extract_company_qualities
from capstone.config import load_config, reset_config
from capstone.consent import ensure_consent, grant_consent
from capstone.insight_store import InsightStore
from capstone.metrics_extractor import chronological_proj, metrics_api
from capstone.modes import resolve_mode
from capstone.project_ranking import rank_projects_from_snapshots
from capstone.resume_retrieval import (
    build_resume_preview,
    ensure_resume_schema,
    generate_resume_project_descriptions,
    get_resume_project_description,
    insert_resume_entry,
    query_resume_entries,
    upsert_resume_project_description,
)
from capstone.storage import close_db, export_snapshots_to_json, fetch_latest_snapshots, open_db, store_analysis_snapshot
from capstone.services import ArchiveAnalyzerService, SnapshotStore
from capstone.top_project_summaries import AutoWriter, EvidenceItem, create_summary_template, export_markdown
from capstone.top_project_summaries import export_readme_snippet
from capstone.zip_analyzer import ZipAnalyzer

# set NO_COLOR=1 to disable the colorized titles.
USE_COLOR = sys.stdout.isatty() and os.environ.get("NO_COLOR") not in {"1", "true", "yes"}

def _open_app_db():
    # Pin to repo-local data directory to avoid cwd-dependent DBs.
    return open_db(ROOT / "data")

def _prompt_choice(prompt: str, choices: Iterable[str]) -> str:
    options = {c.lower() for c in choices}
    while True:
        value = input(prompt).strip().lower()
        if value in options:
            return value
        print(f"Please choose one of: {', '.join(sorted(options))}")

def _prompt_menu(title: str, options: List[str]) -> str:
    line = "=" * 40
    print(f"\n{line}")
    print(title)
    print(line)
    for idx, label in enumerate(options, start=1):
        print(f"{idx}. {label}")
    return _prompt_choice("Select an option: ", [str(i) for i in range(1, len(options) + 1)])

def main():
    # main entry point for user
    print("=" * 60)
    print("     Data and Artifact Mining Application")
    print("     Portfolio & Resume Generator")
    print("=" * 60)
    print()
    
    if not grant_consent():
        print("Consent is required to proceed. Exiting application.")
        print("Please run program again and provide consent to continue.")
        return
    print("\n Consent granted. Proceeding with analysis...\n")
    
    # main menu loop
    while True:
        print("\n" + "=" * 40)
        print("Main Menu")
        print("=" * 40)
        print("1. Analyze new project archive (ZIP)")
        print("2. View all projects")
        print("3. Vew project details")
        print("4. Generate portfolio summary")
        print("5. Generate resume preview")
        print("6. View chronological project timeline")
        print("7. View skills timeline")
        print("8. Delete project insights")
        print("9. Manage consent")
        print("10. Exit")
        print()
        
        choice = input("Please select an option (1-10): ").strip()
        
        if choice == "1":
            zip_path = input("Enter the path to the project ZIP archive: ").strip()
            if not os.path.isfile(zip_path):
                print("Invalid file path. Please try again.")
                continue
            archive_service = ArchiveAnalyzerService(ZipAnalyzer())
            archive_path, payload, code = archive_service.validate_archive(zip_path)
            if payload:
                print(json.dumps(payload))
                continue
            consent = ensure_consent()
            config = load_config()
            mode = resolve_mode("local", consent)
            try:
                summary = archive_service.analyze(
                    zip_path=archive_path,
                    metadata_path=Path("analysis_output/metadata.jsonl"),
                    summary_path=Path("analysis_output/summary.json"),
                    mode=mode,
                    preferences=config.preferences,
                    project_id=Path(zip_path).stem,
                    db_dir=ROOT / "data",
                )
            except ArchiveAnalysisError as exc:
                print(json.dumps(exc.payload))
                continue
            store = SnapshotStore(ROOT / "data")
            try:
                store.store_snapshot(
                    project_id=summary.get("project_id") or Path(zip_path).stem,
                    classification=summary.get("collaboration", {}).get("classification", "unknown"),
                    primary_contributor=summary.get("collaboration", {}).get("primary_contributor"),
                    snapshot=summary,
                )
            finally:
                store.close()
            with _open_app_db() as conn:
                make_entry = _prompt_choice("Create a resume entry for this project? (y/n): ", ["y", "n"])
                if make_entry == "y":
                    project_id = summary.get("project_id") or Path(zip_path).stem
                    insert_resume_entry(
                        conn,
                        section="projects",
                        title=project_id,
                        body=f"Auto-generated resume entry for {project_id}.",
                        projects=[project_id],
                    )
            print("Project analysis completed and stored.")
        elif choice == "2":
            with _open_app_db() as conn:
                snapshots = fetch_latest_snapshots(conn)
                if not snapshots:
                    print("No projects found.")
                else:
                    for snap in snapshots:
                        print(f"- {snap['project_name']} (ID: {snap['id']})")
        elif choice == "3":
            project_id = input("Enter the project ID to view details: ").strip()
            with _open_app_db() as conn:
                snapshots = fetch_latest_snapshots(conn)
                project = next((s for s in snapshots if str(s['id']) == project_id), None)
                if not project:
                    print("Project not found.")
                else:
                    print(json.dumps(project, indent=4))
        elif choice == "4":
            with _open_app_db() as conn:
                snapshots = fetch_latest_snapshots(conn)
                ranked_projects = rank_projects_from_snapshots(snapshots)
                summary = create_summary_template(ranked_projects)
                print("\nPortfolio Summary:\n")
                print(summary)
        elif choice == "5":
            with _open_app_db() as conn:
                result = query_resume_entries(conn)
                project_ids = sorted({pid for entry in result.entries for pid in entry.project_ids})
                if project_ids:
                    generate_resume_project_descriptions(conn, project_ids=project_ids, overwrite=False)
                resume_preview = build_resume_preview(result, conn=conn)
                print("\nResume Preview:\n")
                print(resume_preview)

                if project_ids:
                    action = _prompt_menu("Preview Options", ["Customize", "Back to main menu"])
                    if action == "1":
                        print(f"Available projects: {', '.join(project_ids)}")
                        target = input("Project id to customize: ").strip()
                        if target in project_ids:
                            summary = input("Custom resume wording: ").strip()
                            if summary:
                                variant_name = input("Variant name (optional): ").strip() or None
                                audience = input("Audience (optional): ").strip() or None
                                upsert_resume_project_description(
                                    conn,
                                    project_id=target,
                                    summary=summary,
                                    variant_name=variant_name,
                                    audience=audience,
                                    is_active=True,
                                    metadata={"source": "custom"},
                                )
                                updated = get_resume_project_description(conn, target)
                                print("\nUpdated Resume Preview:\n")
                                refreshed = query_resume_entries(conn)
                                print(build_resume_preview(refreshed, conn=conn))
                                if updated:
                                    print("\nActive wording:\n")
                                    print(updated.to_dict())
                            else:
                                print("No summary provided; keeping existing wording.")
        elif choice == "6":
            with _open_app_db() as conn:
                snapshots = fetch_latest_snapshots(conn)
                timeline = chronological_proj(snapshots)
                print("\nChronological Project Timeline:\n")
                for entry in timeline:
                    print(f"- {entry['date']}: {entry['project_name']}")
        elif choice == "7":
            with _open_app_db() as conn:
                snapshots = fetch_latest_snapshots(conn)
                skills_timeline = metrics_api(snapshots)
                print("\nSkills Timeline:\n")
                for skill in skills_timeline:
                    print(f"- {skill['date']}: {skill['skill_name']} ({skill['level']})")
        elif choice == "8":
            project_id = input("Enter the project ID to delete insights: ").strip()
            with _open_app_db() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM analysis_snapshots WHERE id = ?", (project_id,))
                conn.commit()
                print("Project insights deleted.")
        elif choice == "9":
            consent = input("Do you want to (g)rant or (r)evoke consent? (g/r): ").strip().lower()
            if consent == "g":
                grant_consent()
                print("Consent granted.")
            elif consent == "r":
                print("Consent revoked. Exiting application.")
                return
            else:
                print("Invalid choice. Please try again.")
        elif choice == "10":
            print("Good luck with everything! Exiting application.")
            break
        else:
            print("Invalid choice. Please enter a number between 1 and 10.")
    
if __name__ == "__main__":
    main()
    
