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
from capstone.config import reset_config
from capstone.consent import grant_consent
from capstone.github_contributors import get_contributor_rankings, sync_contributor_stats
from capstone.insight_store import InsightStore
from capstone.metrics_extractor import chronological_proj, metrics_api
from capstone.project_ranking import rank_projects_from_snapshots
from capstone.resume_retrieval import build_resume_preview, ensure_resume_schema, insert_resume_entry, query_resume_entries
from capstone.storage import (
    close_db,
    export_snapshots_to_json,
    fetch_latest_snapshots,
    open_db,
    store_analysis_snapshot,
)
from capstone.top_project_summaries import AutoWriter, EvidenceItem, create_summary_template, export_markdown
from capstone.top_project_summaries import export_readme_snippet

# set NO_COLOR=1 to disable the colorized titles.
USE_COLOR = sys.stdout.isatty() and os.environ.get("NO_COLOR") not in {"1", "true", "yes"}

def _prompt_github_token() -> str | None:
    token = input("Enter GitHub token (leave blank to use GITHUB_TOKEN): ").strip()
    if token:
        return token
    return os.environ.get("GITHUB_TOKEN")


def _print_contributor_rankings(project_id: str, sort_by: str) -> None:
    with open_db() as conn:
        rows = get_contributor_rankings(conn, project_id, sort_by=sort_by)
    if not rows:
        print("No contributor stats found. Please sync from GitHub first.")
        return
    for index, row in enumerate(rows, start=1):
        print(
            f"{index}. {row['contributor']} "
            f"(Total Score: {row['score']:.2f}, Commits: {row['commits']}, "
            f"PRs: {row['pull_requests']}, Issues: {row['issues']}, Reviews: {row['reviews']})"
        )


def _contributor_menu(project_id: str) -> None:
    while True:
        print("\n" + "=" * 40)
        print("Contributor Menu")
        print("=" * 40)
        print("1. Sync from GitHub")
        print("2. View total score ranking")
        print("3. View commits ranking")
        print("4. View PR ranking")
        print("5. View issue ranking")
        print("6. View review ranking")
        print("7. Back")
        print()
        choice = input("Please select an option (1-7): ").strip()
        if choice == "1":
            repo_url = input("Enter GitHub repository URL: ").strip()
            token = _prompt_github_token()
            if not token:
                print("GitHub token missing. Set GITHUB_TOKEN or enter one.")
                continue
            try:
                sync_contributor_stats(repo_url, token=token, project_id=project_id)
            except Exception as exc:
                print(f"Failed to sync contributor stats: {exc}")
            else:
                print("Contributor stats synced.")
        elif choice == "2":
            _print_contributor_rankings(project_id, "score")
        elif choice == "3":
            _print_contributor_rankings(project_id, "commits")
        elif choice == "4":
            _print_contributor_rankings(project_id, "pull_requests")
        elif choice == "5":
            _print_contributor_rankings(project_id, "issues")
        elif choice == "6":
            _print_contributor_rankings(project_id, "reviews")
        elif choice == "7":
            return
        else:
            print("Invalid choice. Please enter a number between 1 and 7.")


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
        print("10. Contributor rankings")
        print("11. Exit")
        print()
        
        choice = input("Please select an option (1-11): ").strip()
        
        if choice == "1":
            zip_path = input("Enter the path to the project ZIP archive: ").strip()
            if not os.path.isfile(zip_path):
                print("Invalid file path. Please try again.")
                continue
            with open_db() as conn:
                store_analysis_snapshot(conn, zip_path)
            print("Project analysis completed and stored.")
        elif choice == "2":
            with open_db() as conn:
                snapshots = fetch_latest_snapshots(conn)
                if not snapshots:
                    print("No projects found.")
                else:
                    for snap in snapshots:
                        snapshot_data = snap.get("snapshot") or {}
                        project_label = snapshot_data.get("project_name") or snap.get("project_id")
                        print(f"- {project_label} (ID: {snap.get('project_id')})")
        elif choice == "3":
            project_id = input("Enter the project ID to view details: ").strip()
            with open_db() as conn:
                snapshots = fetch_latest_snapshots(conn)
                project = next((s for s in snapshots if str(s.get("project_id")) == project_id), None)
                if not project:
                    print("Project not found.")
                else:
                    print(json.dumps(project, indent=4))
            follow = input("View contributor rankings for this project? (y/n): ").strip().lower()
            if follow == "y":
                _contributor_menu(project_id)
        elif choice == "4":
            with open_db() as conn:
                snapshots = fetch_latest_snapshots(conn)
                ranked_projects = rank_projects_from_snapshots(snapshots)
                summary = create_summary_template(ranked_projects)
                print("\nPortfolio Summary:\n")
                print(summary)
        elif choice == "5":
            with open_db() as conn:
                resume_preview = build_resume_preview(conn)
                print("\nResume Preview:\n")
                print(resume_preview)
        elif choice == "6":
            with open_db() as conn:
                snapshots = fetch_latest_snapshots(conn)
                timeline = chronological_proj(snapshots)
                print("\nChronological Project Timeline:\n")
                for entry in timeline:
                    print(f"- {entry['date']}: {entry['project_name']}")
        elif choice == "7":
            with open_db() as conn:
                snapshots = fetch_latest_snapshots(conn)
                skills_timeline = metrics_api(snapshots)
                print("\nSkills Timeline:\n")
                for skill in skills_timeline:
                    print(f"- {skill['date']}: {skill['skill_name']} ({skill['level']})")
        elif choice == "8":
            project_id = input("Enter the project ID to delete insights: ").strip()
            with open_db() as conn:
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
            project_id = input("Enter the project ID to view contributor rankings: ").strip()
            _contributor_menu(project_id)
        elif choice == "11":
            print("Good luck with everything! Exiting application.")
            break
        else:
            print("Invalid choice. Please enter a number between 1 and 11.")
    
if __name__ == "__main__":
    main()
    
