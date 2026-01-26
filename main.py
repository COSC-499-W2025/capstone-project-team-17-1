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
from capstone.metrics_extractor import chronological_proj
from capstone.modes import resolve_mode
from capstone.project_ranking import rank_projects_from_snapshots
from capstone.resume_retrieval import (
    build_resume_preview,
    delete_resume_project_description,
    generate_resume_project_descriptions,
    get_resume_entry,
    get_resume_project_description,
    insert_resume_entry,
    list_resume_project_descriptions,
    query_resume_entries,
    update_resume_entry,
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
from capstone.top_project_summaries import (
    AutoWriter,
    EvidenceItem,
    create_summary_template,
    export_markdown,
    generate_top_project_summaries,
)
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

def _merge_year_counts(target, incoming):
    for year, weight in (incoming or {}).items():
        try:
            target[year] = target.get(year, 0.0) + float(weight or 0.0)
        except (TypeError, ValueError):
            continue


def _merge_quarter_counts(target, incoming):
    for quarter, weight in (incoming or {}).items():
        try:
            target[quarter] = target.get(quarter, 0.0) + float(weight or 0.0)
        except (TypeError, ValueError):
            continue


def _merge_seen(a: str, b: str, *, pick_min: bool) -> str:
    if not a:
        return b or ""
    if not b:
        return a
    return min(a, b) if pick_min else max(a, b)


def _build_skills_timeline_rows(snapshots: Iterable[dict]) -> List[dict]:
    agg = {}
    for row in snapshots:
        snap = row.get("snapshot") or {}
        skill_timeline = (snap.get("skill_timeline") or {}).get("skills") or []
        if skill_timeline:
            for s in skill_timeline:
                skill = s.get("skill")
                if not skill:
                    continue
                cat = s.get("category", "unspecified")
                key = (skill, cat)
                entry = agg.setdefault(
                    key,
                    {
                        "skill": skill,
                        "category": cat,
                        "first_seen": "",
                        "last_seen": "",
                        "total_weight": 0.0,
                        "count": 0,
                        "year_counts": {},
                        "quarter_counts": {},
                        "intensity": 0.0,
                    },
                )
                entry["first_seen"] = _merge_seen(entry["first_seen"], s.get("first_seen") or "", pick_min=True)
                entry["last_seen"] = _merge_seen(entry["last_seen"], s.get("last_seen") or "", pick_min=False)
                try:
                    entry["total_weight"] += float(s.get("total_weight") or 0.0)
                except (TypeError, ValueError):
                    pass
                try:
                    entry["count"] += int(s.get("count") or 0)
                except (TypeError, ValueError):
                    pass
                _merge_year_counts(entry["year_counts"], s.get("year_counts"))
                _merge_quarter_counts(entry["quarter_counts"], s.get("quarter_counts"))
            continue

        fs = snap.get("file_summary", {}) or {}
        first = fs.get("first_modified") or fs.get("earliest_modified") or ""
        last = fs.get("last_modified") or fs.get("latest_modified") or ""
        for s in snap.get("skills", []) or []:
            skill = s.get("skill")
            if not skill:
                continue
            cat = s.get("category", "unspecified")
            key = (skill, cat)
            entry = agg.setdefault(
                key,
                {
                    "skill": skill,
                    "category": cat,
                    "first_seen": "",
                    "last_seen": "",
                    "total_weight": 0.0,
                    "count": 0,
                    "year_counts": {},
                    "quarter_counts": {},
                    "intensity": 0.0,
                },
            )
            entry["first_seen"] = _merge_seen(entry["first_seen"], first, pick_min=True)
            entry["last_seen"] = _merge_seen(entry["last_seen"], last, pick_min=False)
            try:
                entry["total_weight"] += float(s.get("score", s.get("weight", 1.0)) or 0.0)
            except (TypeError, ValueError):
                pass
            entry["count"] += 1

    rows = list(agg.values())
    if rows:
        max_weight = max(r.get("total_weight", 0.0) for r in rows) or 1.0
        for r in rows:
            r["intensity"] = (r.get("total_weight", 0.0) / max_weight) if max_weight else 0.0
            r["year_counts"] = dict(sorted((r.get("year_counts") or {}).items()))
            r["quarter_counts"] = dict(sorted((r.get("quarter_counts") or {}).items()))
    rows.sort(key=lambda r: (r.get("first_seen") or "", r.get("skill") or ""))
    return rows


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


def _format_resume_preview(preview: dict) -> str:
    sections = preview.get("sections") or []
    if not sections:
        return "No resume sections to display."
    project_context = preview.get("projectContext") or {}
    # Render mixed-type lists safely 
    def _stringify_list(values: Iterable) -> str:
        parts: List[str] = []
        for value in values:
            if isinstance(value, str):
                parts.append(value)
                continue
            if isinstance(value, dict):
                name = value.get("name") or value.get("skill") or value.get("framework")
                parts.append(str(name) if name is not None else json.dumps(value, ensure_ascii=True))
                continue
            parts.append(str(value))
        return ", ".join(parts)
    # Keep the preview compact 
    def _body_snippet(text: str, max_lines: int = 2) -> str:
        if not text:
            return ""
        lines = [line for line in text.splitlines() if line.strip()]
        if not lines:
            return ""
        snippet = lines[:max_lines]
        suffix = " ..." if len(lines) > max_lines else ""
        return " / ".join(snippet) + suffix
    lines: List[str] = []
    for section in sections:
        name = (section.get("name") or "Section").title()
        lines.append(f"{name}")
        lines.append("-" * len(name))
        for item in section.get("items") or []:
            title = item.get("title") or item.get("id") or "Untitled"
            excerpt = (item.get("excerpt") or "").strip()
            entry_summary = (item.get("entrySummary") or "").strip()
            entry_body = (item.get("entryBody") or "").strip()
            source = item.get("source") or "-"
            project_ids = item.get("projectIds") or []
            skills = item.get("skills") or []
            updated_at = item.get("updated_at") or item.get("updatedAt") or "-"
            metadata = item.get("metadata") or {}
            status = item.get("status") or "-"
            section_name = item.get("section") or "-"
            start_date = metadata.get("start_date")
            end_date = metadata.get("end_date")
            period = "-"
            if start_date or end_date:
                period = f"{start_date or ''} – {end_date or 'Present'}".strip()
            lines.append(f"* {title}")
            if item.get("id"):
                lines.append(f"  Entry ID: {item.get('id')}")
            if section_name:
                lines.append(f"  Section: {section_name}")
            if status:
                lines.append(f"  Status: {status}")
            if period != "-":
                lines.append(f"  Period: {period}")
            if project_ids:
                lines.append(f"  Project IDs: {', '.join(project_ids)}")
            if entry_summary:
                lines.append(f"  Entry Summary: {entry_summary}")
            if entry_body:
                lines.append(f"  Entry Body (2 lines): {_body_snippet(entry_body)}")
            if excerpt:
                lines.append(f"  Effective Summary: {excerpt}")
            if skills:
                lines.append(f"  Skills: {', '.join(skills)}")
            if updated_at:
                lines.append(f"  Updated: {updated_at}")
            if source:
                lines.append(f"  Source: {source}")
            for pid in project_ids:
                context = project_context.get(pid)
                if not context:
                    continue
                lines.append(f"  Project Context ({pid}):")
                project_name = context.get("project_name") or context.get("project") or context.get("project_id")
                classification = context.get("classification") or context.get("project_type")
                if project_name:
                    lines.append(f"    Name: {project_name}")
                if classification:
                    lines.append(f"    Type: {classification}")
                file_summary = context.get("file_summary") if isinstance(context.get("file_summary"), dict) else {}
                if file_summary:
                    file_count = file_summary.get("file_count") or file_summary.get("files") or "-"
                    active_days = file_summary.get("active_days") or file_summary.get("duration_days") or "-"
                    lines.append(f"    Files: {file_count}")
                    lines.append(f"    Active Days: {active_days}")
                languages = context.get("languages") if isinstance(context.get("languages"), dict) else {}
                if languages:
                    lang_names = ", ".join(languages.keys())
                    lines.append(f"    Languages: {lang_names}")
                frameworks = context.get("frameworks") or []
                if frameworks:
                    if isinstance(frameworks, list):
                        lines.append(f"    Frameworks: {', '.join(frameworks)}")
                    else:
                        lines.append(f"    Frameworks: {frameworks}")
                ctx_skills = context.get("skills") or []
                if ctx_skills:
                    if isinstance(ctx_skills, list):
                        lines.append(f"    Snapshot Skills: {_stringify_list(ctx_skills)}")
                    else:
                        lines.append(f"    Snapshot Skills: {ctx_skills}")
        lines.append("")
    warnings = preview.get("warnings") or []
    if warnings:
        lines.append("Warnings")
        lines.append("--------")
        for warning in warnings:
            lines.append(f"* {warning}")
    return "\n".join(lines).strip()


def _build_project_target_map(preview: dict) -> dict[str, str]:
    targets: dict[str, set[str]] = {}
    for section in preview.get("sections") or []:
        for item in section.get("items") or []:
            title = item.get("title") or item.get("id") or "Untitled"
            for project_id in item.get("projectIds") or []:
                targets.setdefault(project_id, set()).add(title)
    return {pid: ", ".join(sorted(titles)) for pid, titles in targets.items()}


def _build_entry_target_map(preview: dict) -> dict[str, str]:
    targets: dict[str, str] = {}
    for section in preview.get("sections") or []:
        for item in section.get("items") or []:
            entry_id = item.get("id")
            title = item.get("title") or entry_id or "Untitled"
            metadata = item.get("metadata") or {}
            start_date = metadata.get("start_date")
            end_date = metadata.get("end_date")
            period = ""
            if start_date or end_date:
                period = f" ({start_date or ''} – {end_date or 'Present'})"
            if entry_id:
                targets[entry_id] = f"{title}{period}"
    return targets

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
    
    if consent_status == "granted_existing":
        print("\nWelcome Back! Consent saved from previous session. Proceeding with analysis...\n")
    elif consent_status == "granted_new":
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
                    snapshot_map = {
                        str(item.get("project_id")): (item.get("snapshot") or {})
                        for item in snapshots
                        if item.get("project_id")
                    }
                    summaries = generate_top_project_summaries(snapshot_map, limit=3)
                    if not summaries:
                        print("No project summaries available.")
                    else:
                        print("\nPortfolio Summary:\n")
                        for summary in summaries:
                            print(export_markdown(summary))
                            print()
            elif choice == "6":
                with _open_app_db() as conn:
                    result = query_resume_entries(conn)
                    project_ids = sorted({pid for entry in result.entries for pid in entry.project_ids})
                    if project_ids:
                        generate_resume_project_descriptions(conn, project_ids=project_ids, overwrite=False)
                    resume_preview = build_resume_preview(result, conn=conn)
                    print("\nResume Preview:\n")
                    print(_format_resume_preview(resume_preview))

                    if project_ids:
                        action = _prompt_menu("Preview Options", ["Customize", "Back to main menu"])
                        if action == "1":
                            while True:
                                entry_map = _build_entry_target_map(resume_preview)
                                if not entry_map:
                                    print("No resume entries available to edit.")
                                    break
                                print("Available entries:")
                                for entry_id, label in entry_map.items():
                                    print(f"- {entry_id}: {label}")
                                entry_id = input("Entry id to edit (blank to go back): ").strip()
                                if not entry_id:
                                    break
                                entry = get_resume_entry(conn, entry_id)
                                if not entry:
                                    print("Invalid entry id.")
                                    continue
                                print("\nNote: Title/name and start/end dates are locked.")
                                while True:
                                    # Field-level editor
                                    edit_action = _prompt_menu(
                                        "Edit Entry",
                                        [
                                            "Summary",
                                            "Body",
                                            "Skills",
                                            "Linked projects",
                                            "Section",
                                            "Status",
                                            "Metadata (non-date)",
                                            "Back",
                                        ],
                                    )
                                    if edit_action == "8":
                                        break
                                    if edit_action == "1":
                                        while True:
                                            sub = _prompt_menu(
                                                "Summary",
                                                ["Edit", "Delete", "Add", "Back"],
                                            )
                                            if sub == "4":
                                                break
                                            print(f"\nCurrent summary:\n{entry.summary or ''}")
                                            if sub == "2":
                                                # Offer full delete or targeted text removal.
                                                del_mode = _prompt_menu(
                                                    "Delete Summary",
                                                    ["Delete all", "Delete matching text", "Back"],
                                                )
                                                if del_mode == "3":
                                                    continue
                                                if del_mode == "1":
                                                    entry = update_resume_entry(
                                                        conn,
                                                        entry_id=entry_id,
                                                        summary=None,
                                                        _summary_provided=True,
                                                    ) or entry
                                                elif del_mode == "2":
                                                    target = input("Text to delete (blank cancels): ").strip()
                                                    if not target:
                                                        print("No changes made.")
                                                        continue
                                                    current = entry.summary or ""
                                                    if target not in current:
                                                        print("Text not found in summary.")
                                                        continue
                                                    summary = current.replace(target, "").strip()
                                                    entry = update_resume_entry(
                                                        conn,
                                                        entry_id=entry_id,
                                                        summary=summary,
                                                        _summary_provided=True,
                                                    ) or entry
                                            elif sub == "1":
                                                summary = input("New summary (blank keeps current): ").strip()
                                                if not summary:
                                                    print("No changes made.")
                                                    continue
                                                entry = update_resume_entry(
                                                    conn,
                                                    entry_id=entry_id,
                                                    summary=summary,
                                                    _summary_provided=True,
                                                ) or entry
                                            elif sub == "3":
                                                addition = input("Add text (blank cancels): ").strip()
                                                if not addition:
                                                    print("No changes made.")
                                                    continue
                                                base = (entry.summary or "").strip()
                                                summary = f"{base} {addition}".strip()
                                                entry = update_resume_entry(
                                                    conn,
                                                    entry_id=entry_id,
                                                    summary=summary,
                                                    _summary_provided=True,
                                                ) or entry
                                            else:
                                                print("Invalid choice.")
                                            refreshed = query_resume_entries(conn)
                                            refreshed_preview = build_resume_preview(refreshed, conn=conn)
                                            resume_preview = refreshed_preview
                                            print("\nUpdated Resume Preview:\n")
                                            print(_format_resume_preview(refreshed_preview))
                                        continue
                                    elif edit_action == "2":
                                        while True:
                                            sub = _prompt_menu(
                                                "Body",
                                                ["Edit", "Delete", "Add", "Back"],
                                            )
                                            if sub == "4":
                                                break
                                            print(f"\nCurrent body:\n{entry.body}")
                                            if sub == "2":
                                                # Offer full delete or removal.
                                                del_mode = _prompt_menu(
                                                    "Delete Body",
                                                    ["Delete all", "Delete matching text", "Back"],
                                                )
                                                if del_mode == "3":
                                                    continue
                                                if del_mode == "1":
                                                    entry = update_resume_entry(
                                                        conn,
                                                        entry_id=entry_id,
                                                        body="",
                                                    ) or entry
                                                elif del_mode == "2":
                                                    target = input("Text to delete (blank cancels): ").strip()
                                                    if not target:
                                                        print("No changes made.")
                                                        continue
                                                    current = entry.body or ""
                                                    if target not in current:
                                                        print("Text not found in body.")
                                                        continue
                                                    body = current.replace(target, "").strip()
                                                    entry = update_resume_entry(
                                                        conn,
                                                        entry_id=entry_id,
                                                        body=body,
                                                    ) or entry
                                            elif sub == "1":
                                                body = input("New body (blank keeps current): ").strip()
                                                if not body:
                                                    print("No changes made.")
                                                    continue
                                                entry = update_resume_entry(conn, entry_id=entry_id, body=body) or entry
                                            elif sub == "3":
                                                addition = input("Add text (blank cancels): ").strip()
                                                if not addition:
                                                    print("No changes made.")
                                                    continue
                                                base = (entry.body or "").strip()
                                                body = f"{base}\n{addition}".strip()
                                                entry = update_resume_entry(conn, entry_id=entry_id, body=body) or entry
                                            else:
                                                print("Invalid choice.")
                                            refreshed = query_resume_entries(conn)
                                            refreshed_preview = build_resume_preview(refreshed, conn=conn)
                                            resume_preview = refreshed_preview
                                            print("\nUpdated Resume Preview:\n")
                                            print(_format_resume_preview(refreshed_preview))
                                        continue
                                    elif edit_action == "3":
                                        while True:
                                            sub = _prompt_menu(
                                                "Skills",
                                                ["Edit", "Delete", "Add", "Back"],
                                            )
                                            if sub == "4":
                                                break
                                            current = list(entry.skills)
                                            print(f"\nCurrent skills: {', '.join(current)}")
                                            if sub == "2":
                                                raw = input(
                                                    "Comma-separated skills to remove ('clear' to remove all): "
                                                ).strip()
                                                if not raw:
                                                    print("No changes made.")
                                                    continue
                                                if raw.lower() == "clear":
                                                    skills = []
                                                else:
                                                    remove = {s.strip().lower() for s in raw.split(",") if s.strip()}
                                                    skills = [s for s in current if s.lower() not in remove]
                                                entry = update_resume_entry(
                                                    conn,
                                                    entry_id=entry_id,
                                                    skills=skills,
                                                    _skills_provided=True,
                                                ) or entry
                                            elif sub == "1":
                                                raw = input(
                                                    "Comma-separated skills (blank keeps current): "
                                                ).strip()
                                                if not raw:
                                                    print("No changes made.")
                                                    continue
                                                skills = [s.strip() for s in raw.split(",") if s.strip()]
                                                entry = update_resume_entry(
                                                    conn,
                                                    entry_id=entry_id,
                                                    skills=skills,
                                                    _skills_provided=True,
                                                ) or entry
                                            elif sub == "3":
                                                raw = input("Comma-separated skills to add: ").strip()
                                                if not raw:
                                                    print("No changes made.")
                                                    continue
                                                additions = [s.strip() for s in raw.split(",") if s.strip()]
                                                skills = list(dict.fromkeys(current + additions))
                                                entry = update_resume_entry(
                                                    conn,
                                                    entry_id=entry_id,
                                                    skills=skills,
                                                    _skills_provided=True,
                                                ) or entry
                                            else:
                                                print("Invalid choice.")
                                            refreshed = query_resume_entries(conn)
                                            refreshed_preview = build_resume_preview(refreshed, conn=conn)
                                            resume_preview = refreshed_preview
                                            print("\nUpdated Resume Preview:\n")
                                            print(_format_resume_preview(refreshed_preview))
                                        continue
                                    elif edit_action == "4":
                                        while True:
                                            sub = _prompt_menu(
                                                "Linked Projects",
                                                ["Edit", "Delete", "Add", "Back"],
                                            )
                                            if sub == "4":
                                                break
                                            current = list(entry.project_ids)
                                            print(f"\nCurrent linked projects: {', '.join(current)}")
                                            if sub == "2":
                                                raw = input(
                                                    "Comma-separated project ids to remove ('clear' to remove all): "
                                                ).strip()
                                                if not raw:
                                                    print("No changes made.")
                                                    continue
                                                if raw.lower() == "clear":
                                                    projects = []
                                                else:
                                                    remove = {s.strip() for s in raw.split(",") if s.strip()}
                                                    projects = [p for p in current if p not in remove]
                                                entry = update_resume_entry(
                                                    conn,
                                                    entry_id=entry_id,
                                                    projects=projects,
                                                    _projects_provided=True,
                                                ) or entry
                                            elif sub == "1":
                                                raw = input(
                                                    "Comma-separated project ids (blank keeps current): "
                                                ).strip()
                                                if not raw:
                                                    print("No changes made.")
                                                    continue
                                                projects = [s.strip() for s in raw.split(",") if s.strip()]
                                                entry = update_resume_entry(
                                                    conn,
                                                    entry_id=entry_id,
                                                    projects=projects,
                                                    _projects_provided=True,
                                                ) or entry
                                            elif sub == "3":
                                                raw = input("Comma-separated project ids to add: ").strip()
                                                if not raw:
                                                    print("No changes made.")
                                                    continue
                                                additions = [s.strip() for s in raw.split(",") if s.strip()]
                                                projects = list(dict.fromkeys(current + additions))
                                                entry = update_resume_entry(
                                                    conn,
                                                    entry_id=entry_id,
                                                    projects=projects,
                                                    _projects_provided=True,
                                                ) or entry
                                            else:
                                                print("Invalid choice.")
                                            refreshed = query_resume_entries(conn)
                                            refreshed_preview = build_resume_preview(refreshed, conn=conn)
                                            resume_preview = refreshed_preview
                                            print("\nUpdated Resume Preview:\n")
                                            print(_format_resume_preview(refreshed_preview))
                                        continue
                                    elif edit_action == "5":
                                        print(f"\nCurrent section: {entry.section}")
                                        section = input("New section (blank keeps current): ").strip()
                                        if not section:
                                            print("No changes made.")
                                            continue
                                        entry = update_resume_entry(
                                            conn,
                                            entry_id=entry_id,
                                            section=section,
                                        ) or entry
                                    elif edit_action == "6":
                                        print(f"\nCurrent status: {entry.status}")
                                        status = input("New status (blank keeps current): ").strip()
                                        if not status:
                                            print("No changes made.")
                                            continue
                                        entry = update_resume_entry(
                                            conn,
                                            entry_id=entry_id,
                                            status=status,
                                        ) or entry
                                    elif edit_action == "7":
                                        metadata = dict(entry.metadata or {})
                                        print(f"\nCurrent metadata:\n{json.dumps(metadata, indent=2)}")
                                        meta_action = _prompt_menu(
                                            "Metadata Options",
                                            ["Add/update key", "Remove key", "Back"],
                                        )
                                        if meta_action == "3":
                                            continue
                                        if meta_action == "1":
                                            key = input("Key (cannot be start_date/end_date): ").strip()
                                            if not key:
                                                print("No changes made.")
                                                continue
                                            if key in {"start_date", "end_date"}:
                                                print("start_date/end_date are locked.")
                                                continue
                                            value = input("Value (blank keeps current): ").strip()
                                            if not value:
                                                print("No changes made.")
                                                continue
                                            metadata[key] = value
                                        elif meta_action == "2":
                                            key = input("Key to remove: ").strip()
                                            if not key:
                                                print("No changes made.")
                                                continue
                                            if key in {"start_date", "end_date"}:
                                                print("start_date/end_date are locked.")
                                                continue
                                            if key in metadata:
                                                metadata.pop(key, None)
                                            else:
                                                print("Key not found.")
                                                continue
                                        entry = update_resume_entry(
                                            conn,
                                            entry_id=entry_id,
                                            metadata=metadata,
                                            _metadata_provided=True,
                                        ) or entry
                                    else:
                                        print("Invalid choice.")
                                    refreshed = query_resume_entries(conn)
                                    refreshed_preview = build_resume_preview(refreshed, conn=conn)
                                    resume_preview = refreshed_preview
                                    print("\nUpdated Resume Preview:\n")
                                    print(_format_resume_preview(refreshed_preview))
            elif choice == "7":
                with _open_app_db() as conn:
                    snapshots = fetch_latest_snapshots(conn)
                    snapshot_map = {
                        str(item.get("project_id")): (item.get("snapshot") or {})
                        for item in snapshots
                        if item.get("project_id")
                    }
                    timeline = chronological_proj(snapshot_map)
                    print("\nChronological Project Timeline:\n")
                    for entry in timeline:
                        start = entry.get("start")
                        end = entry.get("end")
                        start_text = start.isoformat() if start else "-"
                        end_text = end.isoformat() if end else "Present"
                        print(f"- {entry['name']}: {start_text} -> {end_text}")
            elif choice == "8":
                with _open_app_db() as conn:
                    snapshots = fetch_latest_snapshots(conn)
                    skills_timeline = _build_skills_timeline_rows(snapshots)
                    print("\nSkills Timeline:\n")
                    if not skills_timeline:
                        print("No skill timeline data found.")
                    else:
                        for entry in skills_timeline:
                            years = ", ".join(
                                f"{year}:{weight}"
                                for year, weight in (entry.get("year_counts") or {}).items()
                            )
                            print(
                                f"- {entry.get('skill')} ({entry.get('category')}) "
                                f"{entry.get('first_seen') or '-'} -> {entry.get('last_seen') or '-'} "
                                f"| years: {years or '-'} | total_weight: {entry.get('total_weight', 0.0)}"
                            )
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
    
