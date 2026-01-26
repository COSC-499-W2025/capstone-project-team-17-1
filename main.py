import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Iterable,List

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from capstone.cli import main
from capstone.config import load_config
from capstone.company_profile import build_company_resume_lines
from capstone.company_qualities import extract_company_qualities
from capstone.config import load_config, reset_config
from capstone.consent import ensure_consent, grant_consent, revoke_consent, ensure_or_prompt_consent
from capstone.github_contributors import get_contributor_rankings, parse_repo_url, sync_contributor_stats
from capstone.metrics_extractor import chronological_proj, metrics_api
from capstone.modes import resolve_mode
from capstone.project_ranking import rank_projects_from_snapshots
from capstone.resume_retrieval import (
    build_resume_preview,
    generate_resume_project_descriptions,
    get_resume_project_description,
    insert_resume_entry,
    query_resume_entries,
    upsert_resume_project_description,
)
from capstone.storage import (
    fetch_github_source,
    fetch_latest_snapshot,
    fetch_latest_snapshots,
    open_db,
    store_github_source,
)
from capstone.services import ArchiveAnalysisError, ArchiveAnalyzerService, SnapshotStore
from capstone.top_project_summaries import AutoWriter, EvidenceItem, create_summary_template, export_markdown
from capstone.top_project_summaries import export_readme_snippet
from capstone.zip_analyzer import ZipAnalyzer

def _row_to_dict(row):
    if row is None:
        return {}
    if isinstance(row, dict):
        return row
    if hasattr(row, "to_dict"):
        try:
            return row.to_dict()
        except Exception:
            pass
    if hasattr(row, "__dict__"):
        return dict(row.__dict__)
    return {"value": row}

def _prompt_github_token() -> str | None:
    token = input("Enter GitHub token (leave blank to use GITHUB_TOKEN): ").strip()
    if token:
        return token
    return os.environ.get("GITHUB_TOKEN")


def _exit_app() -> None:
    print("\nGood luck with everything! Exiting application.")
    raise SystemExit(0)


def _print_contributor_rankings(project_id: str, sort_by: str) -> None:
    with _open_app_db() as conn:
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


def _parse_contrib_counts(data) -> tuple[int, int, int]:
    if isinstance(data, str):
        try:
            parts = [int(x.strip()) for x in data.strip("[]").split(",") if x.strip()]
            commits = parts[0] if len(parts) > 0 else 0
            lines = parts[1] if len(parts) > 1 else 0
            reviews = parts[2] if len(parts) > 2 else 0
            return commits, lines, reviews
        except Exception:
            return 0, 0, 0
    if isinstance(data, (list, tuple)):
        commits = int(data[0]) if len(data) > 0 else 0
        lines = int(data[1]) if len(data) > 1 else 0
        reviews = int(data[2]) if len(data) > 2 else 0
        return commits, lines, reviews
    if isinstance(data, dict):
        return (
            int(data.get("commits", 0)),
            int(data.get("lines", 0)),
            int(data.get("reviews", 0)),
        )
    return 0, 0, 0


def _print_zip_contributor_rankings(project_id: str) -> None:
    with _open_app_db() as conn:
        snapshot = fetch_latest_snapshot(conn, project_id)
    if not snapshot:
        print("No contributor data found for this project.")
        return
    collaboration = snapshot.get("collaboration") or {}
    contributors = collaboration.get("contributors (commits, line changes, reviews)", {}) or {}
    if not contributors:
        print("No contributor data found for this project.")
        return
    rows = []
    for name, payload in contributors.items():
        commits, _lines, reviews = _parse_contrib_counts(payload)
        rows.append((name, commits, reviews))
    rows.sort(key=lambda item: (-item[1], -item[2], item[0]))
    for index, (name, commits, reviews) in enumerate(rows, start=1):
        print(
            f"{index}. {name} "
            f"(Total Score: {float(commits):.2f}, Commits: {commits}, "
            f"PRs: 0, Issues: 0, Reviews: {reviews})"
        )


def _show_contributor_rankings(project_id: str) -> None:
    with _open_app_db() as conn:
        source = fetch_github_source(conn, project_id)
    if source:
        _contributor_menu(project_id)
    else:
        _print_zip_contributor_rankings(project_id)


def _contributor_menu(project_id: str) -> None:
    try:
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
                repo_url = None
                token = None
                with _open_app_db() as conn:
                    source = fetch_github_source(conn, project_id)
                    if source:
                        repo_url = source.get("repo_url")
                        token = source.get("token")
                if not repo_url or not token:
                    repo_url = input("Enter GitHub repository URL: ").strip()
                    token = _prompt_github_token()
                    if not token:
                        print("GitHub token missing. Set GITHUB_TOKEN or enter one.")
                        continue
                    try:
                        with _open_app_db() as conn:
                            store_github_source(conn, project_id, repo_url, token)
                    except Exception as exc:
                        print(f"Failed to save GitHub source: {exc}")
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
    except KeyboardInterrupt:
        _exit_app()

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
    print("            Data and Artifact Mining Application")
    print("               Portfolio & Resume Generator")
    print("=" * 60)
    print()
    
    consent_status = ensure_or_prompt_consent()
    
    if consent_status == "denied":
        print("\nConsent is required to proceed! Please run again and grant consent to continue.")
        print("Exiting application...\n")
        return
    
    if consent_status == "saved_existing":
        print("\nWelcome Back! Consent saved from previous session. Proceeding with analysis...\n")
    elif consent_status == "saved_new":
        print("Saving consent for future sessions.")
        print("\n\nProceeding with analysis...\n")
    elif consent_status == "sessions_only":
        print("\nConsent granted for THIS SESSION ONLY. You will be prompted again next time.")
        print("\n\nProceeding with analysis...\n")
    
    # main menu loop
    try:
        while True:
            print("\n" + "=" * 40)
            print("Main Menu")
            print("=" * 40)
            print("1.  Analyze new project archive (ZIP)")
            print("2.  Import from GitHub URL")
            print("3.  View all projects")
            print("4.  View project details")
            print("5.  Generate portfolio summary")
            print("6.  Generate resume preview")
            print("7.  View chronological project timeline")
            print("8.  View skills timeline")
            print("9.  Delete project insights")
            print("10. Manage consent")
            print("11. Contributor rankings (Quick Access)")
            print("12. Exit")
            print()
            while True:
                choice = input("Please select an option (1-12): ").strip()
                if choice in {str(i) for i in range(1, 13)}:
                    break
                print("Invalid choice. Please enter a number between 1 and 12.")
                print()

            if choice == "1":
                zip_path = input("Enter the path to the project ZIP archive: ").strip()
                if not os.path.isfile(zip_path):
                    print("Invalid file path. Please try again.")
                    continue
                archive_service = ArchiveAnalyzerService(ZipAnalyzer())
                archive_path, payload, _code = archive_service.validate_archive(zip_path)
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
                repo_url = input("Enter GitHub repository URL: ").strip()
                token = _prompt_github_token()
                if not token:
                    print("GitHub token missing. Set GITHUB_TOKEN or enter one.")
                    continue
                try:
                    owner, repo = parse_repo_url(repo_url)
                    project_id = f"{owner}/{repo}"
                    with _open_app_db() as conn:
                        store_github_source(conn, project_id, repo_url, token)
                    sync_contributor_stats(repo_url, token=token)
                except Exception as exc:
                    print(f"Failed to import from GitHub: {exc}")
                else:
                    print("GitHub import completed.")
            elif choice == "3":
                with _open_app_db() as conn:
                    snapshots = fetch_latest_snapshots(conn)
                    if not snapshots:
                        print("No projects found.")
                        continue
                    for snap in snapshots:
                        snapshot_data = snap.get("snapshot") or {}
                        project_label = snapshot_data.get("project_name") or snap.get("project_id")
                        print(f"- {project_label} (ID: {snap.get('project_id')})")
                while True:
                    print()
                    print("1. View project details")
                    print("2. Back")
                    follow = input("Please select an option (1-2): ").strip()
                    if follow == "1":
                        project_id = input("Enter the project ID to view details (0 to cancel): ").strip()
                        if project_id == "0":
                            continue
                        project = None
                        with _open_app_db() as conn:
                            snapshots = fetch_latest_snapshots(conn)
                            project = next((s for s in snapshots if str(s.get("project_id")) == project_id), None)
                            if not project:
                                print("Project not found.")
                            else:
                                print(json.dumps(project, indent=4))
                        if project:
                            while True:
                                print()
                                print("1. View contributor rankings")
                                print("2. Back")
                                detail_choice = input("Please select an option (1-2): ").strip()
                                if detail_choice == "1":
                                    _show_contributor_rankings(project_id)
                                elif detail_choice == "2":
                                    break
                                else:
                                    print("Invalid choice. Please enter 1 or 2.")
                    elif follow == "2":
                        break
                    else:
                        print("Invalid choice. Please enter 1 or 2.")
            elif choice == "4":
                project_id = input("Enter the project ID to view details: ").strip()
                project = None
                with _open_app_db() as conn:
                    snapshots = fetch_latest_snapshots(conn)
                    project = next((s for s in snapshots if str(s.get("project_id")) == project_id), None)
                    if not project:
                        print("Project not found.")
                    else:
                        print(json.dumps(project, indent=4))
                if project:
                    while True:
                        print()
                        print("1. View contributor rankings")
                        print("2. Back")
                        detail_choice = input("Please select an option (1-2): ").strip()
                        if detail_choice == "1":
                            _show_contributor_rankings(project_id)
                        elif detail_choice == "2":
                            break
                        else:
                            print("Invalid choice. Please enter 1 or 2.")
            elif choice == "5":
                with _open_app_db() as conn:
                    snapshots = fetch_latest_snapshots(conn)
                    ranked_projects = rank_projects_from_snapshots(snapshots)
                    summary = create_summary_template(ranked_projects)
                    print("\nPortfolio Summary:\n")
                    print(summary)
            elif choice == "6":
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
            elif choice == "7":
                with _open_app_db() as conn:
                    snapshots = fetch_latest_snapshots(conn)
                    timeline = chronological_proj(snapshots)
                    print("\nChronological Project Timeline:\n")
                    for entry in timeline:
                        print(f"- {entry['date']}: {entry['project_name']}")
            elif choice == "8":
                with _open_app_db() as conn:
                    snapshots = fetch_latest_snapshots(conn)
                    skills_timeline = metrics_api(snapshots)
                    print("\nSkills Timeline:\n")
                    for skill in skills_timeline:
                        print(f"- {skill['date']}: {skill['skill_name']} ({skill['level']})")
            elif choice == "9":
                project_id = input("Enter the project ID to delete insights: ").strip()
                with _open_app_db() as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM analysis_snapshots WHERE id = ?", (project_id,))
                    conn.commit()
                    print("Project insights deleted.")
            elif choice == "10":
                consent = input("Do you wish to (g)rant or (r)evoke consent? (g/r): ").strip().lower()
                if consent == "g":
                    grant_consent()
                    print("Consent granted.")
                elif consent == "r":
                    revoke_consent("deny")
                    print("Consent revoked successfully. Exiting application...")
                    return
                else:
                    print("Invalid choice. Please try again.")
            elif choice == "11":
                with _open_app_db() as conn:
                    snapshots = fetch_latest_snapshots(conn)
                    if not snapshots:
                        print("No projects found.")
                        continue
                    for snap in snapshots:
                        snapshot_data = snap.get("snapshot") or {}
                        project_label = snapshot_data.get("project_name") or snap.get("project_id")
                        print(f"- {project_label} (ID: {snap.get('project_id')})")
                while True:
                    print()
                    print("1. View contributor rankings")
                    print("2. Back")
                    follow = input("Please select an option (1-2): ").strip()
                    if follow == "1":
                        project_id = input("Enter the project ID to view contributor rankings: ").strip()
                        _show_contributor_rankings(project_id)
                    elif follow == "2":
                        break
                    else:
                        print("Invalid choice. Please enter 1 or 2.")
            elif choice == "12":
                _exit_app()
    except KeyboardInterrupt:
        _exit_app()
    
if __name__ == "__main__":
    main()
    
