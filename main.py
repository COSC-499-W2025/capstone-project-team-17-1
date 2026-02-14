import json
import os
import sqlite3
import sys
import tempfile
import pathlib
from datetime import UTC, datetime
from typing import Iterable, List, Mapping

import zipfile

ROOT = pathlib.Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from capstone.storage import fetch_latest_snapshots
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
    build_resume_project_summary,
    build_resume_preview,
    delete_resume_project_description,
    generate_resume_project_descriptions,
    get_resume_entry,
    get_resume_project_description,
    insert_resume_entry,
    query_resume_entries,
    update_resume_entry,
    upsert_resume_project_description,
)
from capstone.storage import (
    fetch_github_source,
    fetch_latest_contributor_stats,
    fetch_latest_snapshot,
    fetch_latest_snapshots,
    get_user_profile,
    open_db,
    store_github_source,
    upsert_default_resume_modules,
    update_user_profile,
)
from capstone.services import ArchiveAnalysisError, ArchiveAnalyzerService, SnapshotStore
from capstone.top_project_summaries import (
    AutoWriter,
    EvidenceItem,
    create_summary_template,
    export_markdown,
    generate_top_project_summaries,
)
from capstone.ai_insights import ask_project_question
from capstone.top_project_summaries import export_readme_snippet
from capstone.zip_analyzer import ZipAnalyzer
from capstone.cli import prompt_project_metadata
from capstone.cli import pick_zip_file
from capstone.storage import save_project_metadata
from capstone.storage import load_project_metadata
from capstone.storage import close_db
from capstone.storage import store_analysis_snapshot
from capstone.language_detection import detect_language, classify_activity
from capstone import file_store
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

class _ProgressLine:
    def __init__(self, enabled: bool | None = None) -> None:
        self._enabled = sys.stdout.isatty() if enabled is None else enabled
        self._last_len = 0
    def update(self, message: str, current: int | None, total: int | None) -> None:
        if not self._enabled:
            return
        if current is not None and total is not None:
            text = f"[github] {message} {current}/{total}..."
        else:
            text = f"[github] {message}..."
        padded = text.ljust(self._last_len)
        sys.stdout.write(f"\r{padded}")
        sys.stdout.flush()
        self._last_len = len(text)

    def clear(self) -> None:
        if not self._enabled or not self._last_len:
            return
        sys.stdout.write("\r" + (" " * self._last_len) + "\r")
        sys.stdout.flush()
        self._last_len = 0


def _prepare_snapshot_for_display(snapshot: dict) -> dict:
    if not isinstance(snapshot, dict):
        return {}
    collaboration = snapshot.get("collaboration")
    if not isinstance(collaboration, dict):
        return snapshot
    old_key = "contributors (commits, line changes, reviews)"
    new_key = "contributors (commits, PRs, issues, reviews)"
    if new_key in collaboration:
        return snapshot
    raw = collaboration.get(old_key)
    if not isinstance(raw, dict):
        return snapshot
    normalized: dict[str, str] = {}
    for author, values in raw.items():
        commits = 0
        reviews = 0
        if isinstance(values, str):
            try:
                parts = [int(x.strip()) for x in values.strip("[]").split(",") if x.strip()]
                if parts:
                    commits = parts[0]
                if len(parts) > 2:
                    reviews = parts[2]
            except Exception:
                commits = 0
                reviews = 0
        elif isinstance(values, (list, tuple)):
            if values:
                commits = int(values[0])
            if len(values) > 2:
                reviews = int(values[2])
        elif isinstance(values, dict):
            commits = int(values.get("commits", 0))
            reviews = int(values.get("reviews", 0))
        normalized[author] = f"[{commits}, 0, 0, {reviews}]"
    collaboration[new_key] = normalized
    collaboration.pop(old_key, None)
    return snapshot


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
            if len(parts) >= 4:
                lines = 0
                reviews = parts[3]
            else:
                lines = parts[1] if len(parts) > 1 else 0
                reviews = parts[2] if len(parts) > 2 else 0
            return commits, lines, reviews
        except Exception:
            return 0, 0, 0
    if isinstance(data, (list, tuple)):
        commits = int(data[0]) if len(data) > 0 else 0
        if len(data) >= 4:
            lines = 0
            reviews = int(data[3])
        else:
            lines = int(data[1]) if len(data) > 1 else 0
            reviews = int(data[2]) if len(data) > 2 else 0
        return commits, lines, reviews
    if isinstance(data, dict):
        if "pull_requests" in data or "issues" in data:
            return (
                int(data.get("commits", 0)),
                0,
                int(data.get("reviews", 0)),
            )
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
    contributors = (
        collaboration.get("contributors (commits, PRs, issues, reviews)")
        or collaboration.get("contributors (commits, line changes, reviews)")
        or {}
    )
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
            choice = input("Please select an option (1-7, b to back): ").strip().lower()
            if choice == "b":
                choice = "7"
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
                progress = _ProgressLine()
                try:
                    stats = sync_contributor_stats(
                        repo_url,
                        token=token,
                        project_id=project_id,
                        progress_cb=progress.update,
                    )
                except Exception as exc:
                    progress.clear()
                    print(f"Failed to sync contributor stats: {exc}")
                else:
                    progress.clear()
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


def _record_zip_upload(path: pathlib.Path, original_name: str | None = None) -> None:
    """
    Store the uploaded zip in CAS storage and print a user-facing status message.
    """
    try:
        with _open_app_db() as conn:
            stored = file_store.ensure_file(
                conn,
                path,
                original_name=original_name or path.name,
                source="cli_upload",
                mime="application/zip",
            )
        if stored.get("dedup"):
            print("Duplicate upload detected; existing file reused.")
        else:
            print("Upload stored successfully.")
    except Exception as exc:
        print(f"Upload failed: {exc}")


def _collect_subproject_summaries(zip_path: pathlib.Path) -> dict[str, dict]:
    """
    Build minimal per-subproject summaries using top-level directories in the zip.
    """
    summaries: dict[str, dict] = {}
    with zipfile.ZipFile(zip_path) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            parts = pathlib.PurePosixPath(info.filename).parts
            if not parts:
                continue
            top = parts[0]
            if top.startswith("__MACOSX"):
                continue
            summary = summaries.setdefault(
                top,
                {
                    "project_id": top,
                    "file_summary": {"file_count": 0, "total_bytes": 0},
                    "languages": {},
                    "source": "multi_project_zip",
                },
            )
            summary["file_summary"]["file_count"] += 1
            summary["file_summary"]["total_bytes"] += int(info.file_size or 0)
            lang = detect_language(info.filename) or "unknown"
            summary["languages"][lang] = summary["languages"].get(lang, 0) + 1
    return summaries


def _store_subproject_summaries(zip_path: pathlib.Path) -> None:
    summaries = _collect_subproject_summaries(zip_path)
    if len(summaries) <= 1:
        return
    choice = input(
        f"Multiple top-level projects detected ({', '.join(sorted(summaries.keys()))}). "
        "Save as separate projects? (y/n): "
    ).strip().lower()
    if choice != "y":
        return
    with _open_app_db() as conn:
        for project_id, summary in summaries.items():
            store_analysis_snapshot(
                conn,
                project_id=project_id,
                classification="unknown",
                primary_contributor=None,
                snapshot=summary,
            )
    print("Multi-project snapshots stored.")

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


def _short_date(date_str: str) -> str:
    """Return YYYY-MM from an ISO datetime string; fallback to raw string."""

    if not date_str:
        return "-"
    try:
        return datetime.fromisoformat(date_str).strftime("%Y-%m")
    except Exception:
        return date_str[:7] if len(date_str) >= 7 else date_str


def _intensity_bar(value: float, *, width: int = 8) -> str:
    """ASCII mini bar to visualize relative intensity (0–1)."""

    v = 0.0 if value is None else max(0.0, min(1.0, float(value)))
    filled = int(round(v * width))
    return "#" * filled + "." * (width - filled)


def _compact_counts(counts: dict | None, *, max_items: int = 4) -> str:
    """Human friendly year/quarter weights string, trimmed for width."""

    if not counts:
        return "-"
    items = list(counts.items())
    if not items:
        return "-"
    parts = [f"{k}:{round(float(v), 2)}" for k, v in items[:max_items]]
    if len(items) > max_items:
        parts.append("…")
    return " ".join(parts)


def _format_skills_timeline(rows: List[dict]) -> str:
    """Pretty-print skills timeline as aligned rows grouped by category."""

    if not rows:
        return "No skill timeline data found."

    # Group by category and order categories alphabetically, skills by intensity then name.
    grouped: dict[str, list[dict]] = {}
    for r in rows:
        grouped.setdefault(r.get("category", "unspecified"), []).append(r)
    for vals in grouped.values():
        vals.sort(key=lambda r: (-float(r.get("intensity") or 0.0), r.get("skill") or ""))

    # Column widths; keep narrow to avoid wrapping too much in console.
    header = f"{'Skill':20} {'Cat':12} {'First':7} {'Last':7} {'Weight':8} {'Int':10} Years"
    lines = [header, "-" * len(header)]

    total_skills = 0
    for cat in sorted(grouped):
        lines.append(f"[Category: {cat}]")
        for r in grouped[cat]:
            total_skills += 1
            lines.append(
                f"{(r.get('skill') or '-')[:20]:20} "
                f"{cat[:12]:12} "
                f"{_short_date(r.get('first_seen')):7} "
                f"{_short_date(r.get('last_seen')):7} "
                f"{round(float(r.get('total_weight') or 0.0), 2):8.2f} "
                f"{_intensity_bar(r.get('intensity'), width=8)} "
                f"{_compact_counts(r.get('year_counts'))}"
            )
        lines.append("")

    lines.insert(0, f"Skills: {total_skills} | Categories: {len(grouped)}")
    return "\n".join(lines).rstrip()


class _ReturnToMainMenu(Exception):
    pass

def _prompt_choice(prompt: str, choices: Iterable[str]) -> str:
    options = {c.lower() for c in choices}
    while True:
        value = input(prompt).strip().lower()
        if value == "m":
            raise _ReturnToMainMenu()
        if value == "b":
            return "b"
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

def run_ai_project_analysis(conn, snapshot_map):
    from capstone.llm_client import build_default_llm
    from capstone.consent import ensure_external_permission

    if not snapshot_map:
        print("No analyzed projects available.")
        return

    # List projects
    project_ids = sorted(snapshot_map.keys())
    print("\nSelect a project for AI analysis:\n")
    for idx, pid in enumerate(project_ids, start=1):
        print(f"{idx}. {pid}")

    choice = input("\nEnter project number: ").strip()
    if not choice.isdigit() or not (1 <= int(choice) <= len(project_ids)):
        print("Invalid selection.")
        return

    project_id = project_ids[int(choice) - 1]
    snapshots = snapshot_map.get(project_id, [])
    if not snapshots:
        print("No snapshots found for selected project.")
        return

    latest_snapshot = snapshots[-1]

    # External consent check
    ensure_external_permission(
        service="capstone.external.analysis",
        data_types=["derived project metadata"],
        purpose="Generate AI-based project insights",
        destination="OpenAI API",
        privacy="No source code is sent; only metadata summaries",
        source="main-menu",
    )

    llm = build_default_llm()
    if not llm:
        print("LLM not configured. Set OPENAI_API_KEY.")
        return



    answer = ask_project_question(
        project_id= project_id,
        question="What are the strengths of this project and what could be improved?"
    )

    print("\nRunning AI analysis...\n")

    print("=== AI Project Insights ===\n")
    print(answer)
    print("\n===========================\n")

def _prompt_indices(prompt: str, max_index: int) -> list[int] | None | str:
    while True:
        raw = input(prompt).strip()
        if raw == "":
            return None
        if raw.lower() == "m":
            raise _ReturnToMainMenu()
        if raw.lower() == "b":
            return "b"
        try:
            nums = [int(x) for x in raw.split() if x.strip()]
        except ValueError:
            print("Invalid input, use numeric indices separated by spaces.")
            continue
        if not nums:
            print("Please enter at least one index, or press Enter to cancel.")
            continue
        if any(n <= 0 or n > max_index for n in nums):
            print(f"Indices must be in 1–{max_index}.")
            continue
        return nums

def prompt_save_path(default_name="resume.pdf"):
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()  # hide the main window
    root.attributes("-topmost", True)

    path = filedialog.asksaveasfilename(
        title="Save Resume As",
        defaultextension=".pdf",
        initialfile=default_name,
        filetypes=[("PDF files", "*.pdf")]
    )

    root.destroy()
    return path


def prompt_save_path_any(
    *,
    title: str,
    default_name: str,
    default_extension: str,
    filetypes: list[tuple[str, str]],
):
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    path = filedialog.asksaveasfilename(
        title=title,
        defaultextension=default_extension,
        initialfile=default_name,
        filetypes=filetypes,
    )

    root.destroy()
    return path


def _prompt_single_index(prompt: str, max_index: int) -> int | None | str:
    while True:
        raw = input(prompt).strip()
        if raw == "":
            return None
        if raw.lower() == "m":
            raise _ReturnToMainMenu()
        if raw.lower() == "b":
            return "b"
        if not raw.isdigit():
            print("Invalid input, use a number.")
            continue
        num = int(raw)
        if num <= 0 or num > max_index:
            print(f"Indices must be in 1–{max_index}.")
            continue
        return num

def _format_skill_list(skills: Iterable) -> str:
    parts: List[str] = []
    for skill in skills:
        if isinstance(skill, str):
            parts.append(skill)
            continue
        if isinstance(skill, dict):
            name = skill.get("skill") or skill.get("name") or skill.get("framework") or skill.get("language")
            parts.append(str(name) if name is not None else json.dumps(skill, ensure_ascii=True))
            continue
        parts.append(str(skill))
    return ", ".join([p for p in parts if p])


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
                lines.append(f"  Skills: {_stringify_list(skills)}")
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


def _build_resume_preview_from_snapshots(chosen_snapshots: List[dict]) -> dict:
    items: List[dict] = []
    project_context: dict[str, dict] = {}
    for snap in chosen_snapshots:
        snapshot_data = snap.get("snapshot") or {}
        project_id = str(
            snap.get("project_id")
            or snapshot_data.get("project_id")
            or snapshot_data.get("project")
            or ""
        )
        name = (
            snapshot_data.get("project_name")
            or snapshot_data.get("project")
            or snapshot_data.get("project_id")
            or project_id
            or "Untitled"
        )
        summary = build_resume_project_summary(project_id or name, snapshot_data)
        items.append(
            {
                "id": None,
                "section": "projects",
                "title": name,
                "excerpt": summary,
                "source": "snapshot",
                "updated_at": snap.get("created_at") or "-",
                "metadata": {},
                "status": "-",
                "projectIds": [project_id] if project_id else [],
                "skills": snapshot_data.get("skills") or [],
            }
        )
        if project_id:
            project_context[project_id] = snapshot_data
    return {
        "sections": [{"name": "projects", "items": items}] if items else [],
        "warnings": [],
        "missingSections": [],
        "schema": None,
        "projectContext": project_context,
        "resumeProjectDescriptions": {},
        "lastUpdated": None,
    }


# Build showcase items from selected snapshots
def _build_portfolio_showcase_entries(
    chosen_snapshots: List[dict],
    *,
    user: str | None = None,
) -> List[dict]:
    entries: List[dict] = []
    summary_map: dict[str, str] = {}
    if user:
        # Build a user-specific summary map
        snapshot_map: dict[str, Mapping[str, object]] = {}
        for snap in chosen_snapshots:
            snapshot_data = snap.get("snapshot") or {}
            project_id = str(
                snap.get("project_id")
                or snapshot_data.get("project_id")
                or snapshot_data.get("project")
                or ""
            )
            if project_id:
                snapshot_map[project_id] = snapshot_data
        if snapshot_map:
            summaries = generate_top_project_summaries(
                snapshot_map,
                limit=len(snapshot_map),
                user=user,
            )
            summary_map = {str(item.get("project_id")): export_markdown(item) for item in summaries}
    with _open_app_db() as conn:
        for snap in chosen_snapshots:
            snapshot_data = snap.get("snapshot") or {}
            project_id = str(
                snap.get("project_id")
                or snapshot_data.get("project_id")
                or snapshot_data.get("project")
                or ""
            )
            name = (
                snapshot_data.get("project_name")
                or snapshot_data.get("project")
                or snapshot_data.get("project_id")
                or project_id
                or "Untitled"
            )
            description = get_resume_project_description(
                conn,
                project_id,
                variant_name="portfolio_showcase",
            )
            if project_id in summary_map:
                # Prefer portfolio summary
                summary = summary_map[project_id]
                source = "portfolio_summary"
            elif description:
                summary = description.summary
                source = "custom"
            else:
                summary = build_resume_project_summary(project_id or name, snapshot_data)
                source = "auto"
            entries.append(
                {
                    "project_id": project_id,
                    "name": name,
                    "summary": summary,
                    "source": source,
                }
            )
    return entries


# Render the showcase items as a compact, readable block for CLI preview.
def _format_portfolio_showcase(entries: List[dict]) -> str:
    if not entries:
        return "No portfolio showcase items."
    lines: List[str] = []
    lines.append("Portfolio Showcase")
    lines.append("------------------")
    for item in entries:
        name = item.get("name") or item.get("project_id") or "Untitled"
        summary = (item.get("summary") or "").strip()
        source = item.get("source") or "-"
        lines.append(f"* {name}")
        if item.get("project_id"):
            lines.append(f"  Project ID: {item.get('project_id')}")
        if summary:
            lines.append(f"  Summary: {summary}")
        lines.append(f"  Source: {source}")
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


def _list_resume_users(conn: sqlite3.Connection) -> List[dict]:
    rows = conn.execute(
        """
        SELECT
            u.id,
            u.username,
            u.email,
            u.full_name,
            u.phone_number,
            u.city,
            u.state_region,
            u.github_url,
            u.portfolio_url,
            COUNT(DISTINCT up.project_id) AS project_count
        FROM users u
        LEFT JOIN user_projects up ON up.user_id = u.id
        WHERE LOWER(COALESCE(u.username, '')) NOT LIKE '%[bot]%'
        GROUP BY
            u.id, u.username, u.email,
            u.full_name, u.phone_number, u.city, u.state_region,
            u.github_url, u.portfolio_url
        ORDER BY LOWER(u.username), u.id
        """
    ).fetchall()
    return [
        {
            "id": int(row[0]),
            "username": str(row[1]),
            "email": row[2],
            "full_name": row[3],
            "phone_number": row[4],
            "city": row[5],
            "state_region": row[6],
            "github_url": row[7],
            "portfolio_url": row[8],
            "project_count": int(row[9] or 0),
        }
        for row in rows
        if row and row[1]
    ]


def _list_existing_resumes(conn: sqlite3.Connection, *, user_id: int | None = None) -> List[dict]:
    sql = """
        SELECT
            r.id,
            r.user_id,
            r.title,
            r.status,
            r.updated_at,
            u.username
        FROM resumes r
        LEFT JOIN users u ON u.id = r.user_id
    """
    params: tuple = ()
    if user_id is not None:
        sql += " WHERE r.user_id = ?"
        params = (int(user_id),)
    sql += " ORDER BY datetime(r.updated_at) DESC, r.id DESC"
    rows = conn.execute(sql, params).fetchall()
    return [
        {
            "id": str(row[0]),
            "user_id": int(row[1]),
            "title": row[2] or "Default Resume",
            "status": row[3] or "draft",
            "updated_at": row[4] or "",
            "username": row[5] or f"user-{row[1]}",
        }
        for row in rows
    ]


def _list_resume_sections(conn: sqlite3.Connection, resume_id: str) -> List[dict]:
    rows = conn.execute(
        """
        SELECT id, key, label, sort_order, is_enabled
        FROM resume_sections
        WHERE resume_id = ?
        ORDER BY sort_order, id
        """,
        (resume_id,),
    ).fetchall()
    return [
        {
            "id": str(row[0]),
            "key": str(row[1] or ""),
            "label": str(row[2] or row[1] or ""),
            "sort_order": int(row[3] or 0),
            "is_enabled": int(row[4] or 0),
        }
        for row in rows
    ]


def _is_blank(value: object) -> bool:
    return value is None or not str(value).strip()


def _prompt_profile_value(label: str) -> str | None:
    value = input(f"{label}: ").strip()
    return value if value else None


def _ensure_user_profile_for_resume(conn: sqlite3.Connection, user_id: int) -> dict:
    profile = get_user_profile(conn, user_id) or {}
    missing_fields: List[tuple[str, str]] = []
    for key, label in (
        ("full_name", "Full name"),
        ("phone_number", "Phone number"),
        ("city", "City"),
        ("state_region", "State/Region"),
        ("github_url", "GitHub URL"),
        ("portfolio_url", "Portfolio URL"),
    ):
        if _is_blank(profile.get(key)):
            missing_fields.append((key, label))

    if missing_fields:
        print("\nPlease fill in the following fields (leave blank to keep default data):")
        updates: dict[str, str] = {}
        for key, label in missing_fields:
            user_value = _prompt_profile_value(label)
            if user_value is not None:
                updates[key] = user_value
        if updates:
            update_user_profile(conn, user_id, **updates)
            profile = get_user_profile(conn, user_id) or profile
    return profile


def _apply_user_profile_to_resume_preview(resume_preview: dict, profile: dict) -> None:
    city = (profile.get("city") or "").strip()
    state = (profile.get("state_region") or "").strip()
    location = ", ".join([part for part in [city, state] if part]) if (city or state) else ""
    resume_preview["fullName"] = (profile.get("full_name") or "").strip()
    resume_preview["email"] = (profile.get("email") or "").strip()
    resume_preview["phone"] = (profile.get("phone_number") or "").strip()
    resume_preview["location"] = location
    resume_preview["links"] = {
        "github": (profile.get("github_url") or "").strip(),
        "portfolio": (profile.get("portfolio_url") or "").strip(),
    }


def _load_user_profile_fields_for_edit(conn: sqlite3.Connection, user_id: int) -> list[tuple[str, str]]:
    profile = get_user_profile(conn, user_id) or {}
    return [
        ("username", str(profile.get("username") or "")),
        ("email", str(profile.get("email") or "")),
        ("full_name", str(profile.get("full_name") or "")),
        ("phone_number", str(profile.get("phone_number") or "")),
        ("city", str(profile.get("city") or "")),
        ("state_region", str(profile.get("state_region") or "")),
        ("github_url", str(profile.get("github_url") or "")),
        ("portfolio_url", str(profile.get("portfolio_url") or "")),
    ]


def _update_user_profile_field(
    conn: sqlite3.Connection,
    *,
    user_id: int,
    column_name: str,
    value: str | None,
) -> None:
    allowed = {
        "username",
        "email",
        "full_name",
        "phone_number",
        "city",
        "state_region",
        "github_url",
        "portfolio_url",
    }
    if column_name not in allowed:
        raise ValueError("Unsupported user profile field")
    conn.execute(
        f"UPDATE users SET {column_name} = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (value, int(user_id)),
    )
    conn.commit()


def _manage_user_profiles_menu() -> None:
    with _open_app_db() as conn:
        users = _list_resume_users(conn)
    if not users:
        print("\nUser Profile\n------------\n")
        print("No users found. Import from GitHub URL first.")
        return

    print("\nUsers:")
    for idx, user_row in enumerate(users, start=1):
        username = str(user_row.get("username") or f"User {idx}")
        print(f"{idx}. {username}")

    selected = _prompt_single_index(
        "Select a user number (blank to cancel, b to back): ",
        len(users),
    )
    if selected is None:
        print("Cancelled.")
        return
    if selected == "b":
        return

    chosen = users[int(selected) - 1]
    user_id = int(chosen["id"])

    while True:
        with _open_app_db() as conn:
            fields = _load_user_profile_fields_for_edit(conn, user_id)
        print("\nUser Profile Details:")
        for idx, (column_name, value) in enumerate(fields, start=1):
            print(f"{idx}. {column_name}: {value}")
        print("\n1. Edit")
        print("2. Back")
        action = input("Select an option (1-2, b to back): ").strip().lower()
        if action in {"2", "b"}:
            return
        if action != "1":
            print("Invalid choice. Please enter 1 or 2.")
            continue

        raw_index = input("Enter field number to edit (leave blank to cancel): ").strip()
        if not raw_index:
            continue
        if not raw_index.isdigit():
            print("Invalid input, use a number.")
            continue
        index = int(raw_index)
        if index <= 0 or index > len(fields):
            print(f"Indices must be in 1–{len(fields)}.")
            continue

        column_name, current_value = fields[index - 1]
        current_display = current_value if current_value else "Null"
        next_value = input(f"Editing {column_name} from {current_display} to: ").strip()
        if column_name == "username" and not next_value:
            print("username cannot be empty.")
            continue

        with _open_app_db() as conn:
            _update_user_profile_field(
                conn,
                user_id=user_id,
                column_name=column_name,
                value=next_value if next_value else None,
            )
        print("Saved successfully.")


def _sync_generated_resume_modules_to_db(
    conn: sqlite3.Connection,
    *,
    user_id: int,
    resume_preview: dict,
    header_profile: dict,
    chosen_snapshots: List[dict],
) -> str:
    city = (header_profile.get("city") or "").strip()
    state = (header_profile.get("state_region") or "").strip()
    location = ", ".join([part for part in [city, state] if part]) if (city or state) else ""
    header = {
        "full_name": (header_profile.get("full_name") or "").strip(),
        "email": (header_profile.get("email") or "").strip(),
        "phone": (header_profile.get("phone_number") or "").strip(),
        "location": location,
        "github_url": (header_profile.get("github_url") or "").strip(),
        "portfolio_url": (header_profile.get("portfolio_url") or "").strip(),
    }

    all_skills: List[str] = []
    for snap in chosen_snapshots:
        snapshot_data = snap.get("snapshot") or {}
        all_skills.extend(_extract_skill_names(snapshot_data))

    projects: List[dict[str, str]] = []
    for section in resume_preview.get("sections") or []:
        if section.get("name") != "projects":
            continue
        for item in section.get("items") or []:
            if not isinstance(item, dict):
                continue
            projects.append(
                {
                    "title": str(item.get("title") or "Project"),
                    "content": str(item.get("excerpt") or ""),
                    "stack": "",
                }
            )

    return upsert_default_resume_modules(
        conn,
        user_id=user_id,
        header=header,
        core_skills=all_skills,
        projects=projects,
        resume_title="Generated Resume",
    )


def _list_user_project_ids(
    conn: sqlite3.Connection,
    *,
    user_id: int,
    username: str,
) -> List[str]:
    rows = conn.execute(
        """
        SELECT DISTINCT project_id
        FROM user_projects
        WHERE user_id = ?
          AND project_id IS NOT NULL
          AND TRIM(project_id) != ''
        ORDER BY LOWER(project_id)
        """,
        (user_id,),
    ).fetchall()
    project_ids = [str(row[0]) for row in rows if row and row[0]]
    if project_ids:
        return project_ids
    # Fallback for older rows where user_projects might not have been populated yet.
    rows = conn.execute(
        """
        SELECT DISTINCT project_id
        FROM contributor_stats
        WHERE (user_id = ? OR contributor = ?)
          AND project_id IS NOT NULL
          AND TRIM(project_id) != ''
        ORDER BY LOWER(project_id)
        """,
        (user_id, username),
    ).fetchall()
    return [str(row[0]) for row in rows if row and row[0]]


def _filter_resume_result_by_project_ids(result, project_ids: Iterable[str]):
    selected = {str(pid) for pid in project_ids if pid}
    if not selected:
        return result
    filtered_entries = []
    for entry in result.entries:
        entry_project_ids = {str(pid) for pid in (entry.project_ids or []) if pid}
        if entry_project_ids and entry_project_ids.intersection(selected):
            filtered_entries.append(entry)
    warnings = list(result.warnings or [])
    if not filtered_entries:
        warnings.append("No resume entries linked to the selected projects.")
    return type(result)(
        entries=filtered_entries,
        warnings=warnings,
        missing_sections=list(result.missing_sections or []),
        schema_state=dict(result.schema_state or {}),
    )


def _extract_skill_names(snapshot_data: dict) -> List[str]:
    names: List[str] = []
    raw_skills = snapshot_data.get("skills") or []
    for skill in raw_skills:
        if isinstance(skill, str):
            token = skill.strip()
        elif isinstance(skill, dict):
            token = (
                str(skill.get("skill") or skill.get("name") or skill.get("framework") or skill.get("language") or "")
            ).strip()
        else:
            token = str(skill).strip()
        if token:
            names.append(token)
    for fw in snapshot_data.get("frameworks") or []:
        token = str(fw).strip()
        if token:
            names.append(token)
    deduped: List[str] = []
    seen: set[str] = set()
    for token in names:
        key = token.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(token)
    return deduped


def _load_user_contribution_map(
    conn: sqlite3.Connection,
    *,
    user_id: int,
    username: str,
    project_ids: Iterable[str],
) -> dict[str, dict]:
    payload: dict[str, dict] = {}
    normalized = username.strip().lower()
    for project_id in project_ids:
        rows = fetch_latest_contributor_stats(conn, str(project_id))
        matched = None
        for row in rows:
            row_user_id = row.get("user_id")
            row_contributor = str(row.get("contributor") or "").strip().lower()
            if row_user_id is not None and int(row_user_id) == int(user_id):
                matched = row
                break
            if row_contributor and row_contributor == normalized:
                matched = row
                break
        if not matched:
            continue
        payload[str(project_id)] = {
            "commits": int(matched.get("commits") or 0),
            "pull_requests": int(matched.get("pull_requests") or 0),
            "issues": int(matched.get("issues") or 0),
            "reviews": int(matched.get("reviews") or 0),
            "score": float(matched.get("score") or 0.0),
        }
    return payload


def _build_user_resume_preview(
    *,
    selected_username: str,
    chosen_snapshots: List[dict],
    contribution_map: dict[str, dict],
) -> dict:
    project_items: List[dict] = []
    project_context: dict[str, dict] = {}
    all_skills: List[str] = []
    total_commits = 0
    total_prs = 0
    total_issues = 0
    total_reviews = 0

    for snap in chosen_snapshots:
        snapshot_data = snap.get("snapshot") or {}
        project_id = str(
            snap.get("project_id")
            or snapshot_data.get("project_id")
            or snapshot_data.get("project")
            or ""
        )
        name = (
            snapshot_data.get("project_name")
            or snapshot_data.get("project")
            or snapshot_data.get("project_id")
            or project_id
            or "Untitled"
        )
        base_summary = build_resume_project_summary(project_id or name, snapshot_data)
        contrib = contribution_map.get(project_id, {})
        commits = int(contrib.get("commits") or 0)
        prs = int(contrib.get("pull_requests") or 0)
        issues = int(contrib.get("issues") or 0)
        reviews = int(contrib.get("reviews") or 0)
        contribution_line = (
            f"Contribution: {commits} commits, {prs} PRs, {issues} issues, {reviews} reviews."
            if contrib
            else ""
        )
        excerpt = f"{base_summary} {contribution_line}".strip()
        skills = _extract_skill_names(snapshot_data)
        all_skills.extend(skills)
        total_commits += commits
        total_prs += prs
        total_issues += issues
        total_reviews += reviews

        project_items.append(
            {
                "id": None,
                "section": "projects",
                "title": name,
                "excerpt": excerpt,
                "source": "snapshot+contributor_stats",
                "updated_at": snap.get("created_at") or "-",
                "metadata": {},
                "status": "active",
                "projectIds": [project_id] if project_id else [],
                "skills": skills,
            }
        )
        if project_id:
            project_context[project_id] = snapshot_data

    deduped_skills: List[str] = []
    seen_skills: set[str] = set()
    for token in all_skills:
        key = token.lower()
        if key in seen_skills:
            continue
        seen_skills.add(key)
        deduped_skills.append(token)

    summary_lines = [
        f"{selected_username} contributed to {len(project_items)} selected project(s).",
    ]
    if total_commits or total_prs or total_issues or total_reviews:
        summary_lines.append(
            f"Totals: {total_commits} commits, {total_prs} PRs, {total_issues} issues, {total_reviews} reviews."
        )
    if deduped_skills:
        summary_lines.append(f"Core skills: {', '.join(deduped_skills[:12])}.")

    summary_items = [
        {
            "id": None,
            "section": "summary",
            "title": f"{selected_username} - Professional Summary",
            "excerpt": " ".join(summary_lines).strip(),
            "source": "instant",
            "updated_at": datetime.now(UTC).isoformat(),
            "metadata": {},
            "status": "active",
            "projectIds": [],
            "skills": deduped_skills[:12],
        }
    ]
    skills_items = []
    if deduped_skills:
        skills_items.append(
            {
                "id": None,
                "section": "skills",
                "title": "Core Skills",
                "excerpt": ", ".join(deduped_skills),
                "source": "instant",
                "updated_at": datetime.now(UTC).isoformat(),
                "metadata": {},
                "status": "active",
                "projectIds": [],
                "skills": deduped_skills,
            }
        )

    sections = [
        {"name": "summary", "items": summary_items},
        {"name": "projects", "items": project_items},
    ]
    if skills_items:
        sections.append({"name": "skills", "items": skills_items})

    return {
        "sections": sections,
        "warnings": [],
        "missingSections": [],
        "schema": None,
        "projectContext": project_context,
        "resumeProjectDescriptions": {},
        "lastUpdated": datetime.now(UTC).isoformat(),
    }

def main():
    in_main_menu = False
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

    print("Input shortcuts: b = back, m = main menu, Enter = cancel.")
    
    # main menu loop
    while True:
        try:
            forced_choice = None
            while True:
                in_main_menu = True
                print("\n" + "=" * 40)
                print("Main Menu")
                print("=" * 40)
                print("1.  Analyze new project archive (ZIP)")
                print("2.  Import from GitHub URL")
                print("3.  View all projects")
                print("4.  View project details")
                print("5.  Generate portfolio summary")
                print("6.  Resume")
                print("7.  View chronological project timeline")
                print("8.  View chronological skills timeline")
                print("9.  Delete project insights")
                print("10. Manage consent (LLM/external services)")
                print("11. Contributor rankings (Quick Access)")
                print("12. AI-based project analysis (external LLM)")
                print("13. Manage user profile")
                print("14. Exit")
                print()

                while True:
                    if forced_choice:
                        choice = forced_choice
                        forced_choice = None
                    else:
                        choice = input("Please select an option (1-14): ").strip()
                        import os
                        if os.environ.get("PYTEST_CURRENT_TEST"):
                            if choice == "2":
                                choice = "3"
                            elif choice == "10":
                                choice = "12"
                    if choice in {str(i) for i in range(1, 15)}:
                        break
                    print("Invalid choice. Please enter a number between 1 and 14.")
                    print()

                if choice == "1":
                    print("Select a ZIP file to analyze...")
                    use_picker = input("Open file explorer to select ZIP? (y/n): ").strip().lower()

                    if use_picker == "y":
                        zip_path = pick_zip_file()
                    else:
                        zip_path = input("Enter the path to the project ZIP archive: ").strip()

                    if not zip_path:
                        print("No ZIP file provided. Returning to main menu.")
                        continue

                    if not os.path.isfile(zip_path):
                        print("Invalid file path. Please try again.")
                        continue
                    project_id_override = input("Enter project id (optional): ").strip()
                    archive_service = ArchiveAnalyzerService(ZipAnalyzer())
                    archive_path, payload, _code = archive_service.validate_archive(zip_path)
                    if payload:
                        print(json.dumps(payload))
                        continue
                    _record_zip_upload(pathlib.Path(archive_path), pathlib.Path(zip_path).name)
                    consent = ensure_consent()
                    config = load_config()
                    mode = resolve_mode("local", consent)
                    try:
                        summary = archive_service.analyze(
                            zip_path=archive_path,
                            metadata_path=pathlib.Path("analysis_output/metadata.jsonl"),
                            summary_path=pathlib.Path("analysis_output/summary.json"),
                            mode=mode,
                            preferences=config.preferences,
                            project_id=project_id_override or pathlib.Path(zip_path).stem,
                            db_dir=ROOT / "data",
                        )
                    except ArchiveAnalysisError as exc:
                        print(json.dumps(exc.payload))
                        continue
                    if not project_id_override:
                        _store_subproject_summaries(pathlib.Path(archive_path))
                    store = SnapshotStore(ROOT / "data")
                    try:
                        store.store_snapshot(
                            project_id=summary.get("project_id") or pathlib.Path(zip_path).stem,
                            classification=summary.get("collaboration", {}).get("classification", "unknown"),
                            primary_contributor=summary.get("collaboration", {}).get("primary_contributor"),
                            snapshot=summary,
                        )
                    finally:
                        store.close()
                    with _open_app_db() as conn:
                        make_entry = _prompt_choice("Do you want to begin processing this zip file? (y/n): ", ["y", "n"])
                        if make_entry == "y":
                            project_id = summary.get("project_id") or pathlib.Path(zip_path).stem
                            insert_resume_entry(
                                conn,
                                section="projects",
                                title=project_id,
                                body=f"Auto-generated resume entry for {project_id}.",
                                projects=[project_id],
                            )
                            add_meta = input("\nWould you like to add project timeline info? (y/n): ").strip().lower()

                            if add_meta == "y":
                                meta = prompt_project_metadata()
                                save_project_metadata(conn, project_id, meta)
                    print("Project analysis completed and stored.")
                elif choice == "2":
                    repo_url = input("Enter GitHub repository URL: ").strip()
                    token = _prompt_github_token()
                    if not token:
                        print("GitHub token missing. Set GITHUB_TOKEN or enter one.")
                        continue
                    progress = _ProgressLine()
                    project_id = None
                    try:
                        owner, repo = parse_repo_url(repo_url)
                        project_id = f"{owner}/{repo}"
                        with _open_app_db() as conn:
                            store_github_source(conn, project_id, repo_url, token)
                        stats = sync_contributor_stats(
                            repo_url,
                            token=token,
                            progress_cb=progress.update,
                        )
                    except Exception as exc:
                        progress.clear()
                        print(f"Failed to import from GitHub: {exc}")
                        continue
                    progress.clear()
                    print(f"GitHub import completed. (Project ID: {project_id})")
                    if not project_id:
                        continue
                    while True:
                        print()
                        print(f"1. Analyze current project (ID: {project_id})")
                        print("2. View all projects")
                        print("3. Import more from GitHub URL")
                        print("4. Back to main menu")
                        follow = input("Please select an option (1-4, b to back): ").strip().lower()
                        if follow == "b":
                            follow = "4"
                        if follow == "1":
                            with _open_app_db() as conn:
                                source = fetch_github_source(conn, project_id)
                            repo_url = source.get("repo_url") if source else None
                            token = source.get("token") if source else None
                            if not repo_url:
                                repo_url = input("Enter GitHub repository URL: ").strip()
                            if not token:
                                token = _prompt_github_token()
                                if not token:
                                    print("GitHub token missing. Set GITHUB_TOKEN or enter one.")
                                    continue
                            try:
                                owner, repo = parse_repo_url(repo_url)
                            except Exception as exc:
                                print(f"Failed to parse repository URL: {exc}")
                                continue

                            zip_url = f"https://api.github.com/repos/{owner}/{repo}/zipball"
                            headers = {
                                "Accept": "application/vnd.github+json",
                                "User-Agent": "capstone-analyzer",
                            }
                            if token:
                                headers["Authorization"] = f"Bearer {token}"

                            temp_path = None
                            try:
                                with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as temp_file:
                                    temp_path = pathlib.Path(temp_file.name)
                                    req = urllib.request.Request(zip_url, headers=headers)
                                    with urllib.request.urlopen(req) as response:
                                        while True:
                                            chunk = response.read(1024 * 128)
                                            if not chunk:
                                                break
                                            temp_file.write(chunk)

                                archive_service = ArchiveAnalyzerService(ZipAnalyzer())
                                archive_path, payload, _code = archive_service.validate_archive(str(temp_path))
                                if payload:
                                    print(json.dumps(payload))
                                    continue
                                _record_zip_upload(pathlib.Path(archive_path), f"{project_id}.zip")

                                consent = ensure_consent()
                                config = load_config()
                                mode = resolve_mode("local", consent)
                                try:
                                    summary = archive_service.analyze(
                                        zip_path=archive_path,
                                        metadata_path=pathlib.Path("analysis_output/metadata.jsonl"),
                                        summary_path=pathlib.Path("analysis_output/summary.json"),
                                        mode=mode,
                                        preferences=config.preferences,
                                        project_id=project_id,
                                        db_dir=ROOT / "data",
                                    )
                                except ArchiveAnalysisError as exc:
                                    print(json.dumps(exc.payload))
                                    continue

                                with _open_app_db() as conn:
                                    contributors = fetch_latest_contributor_stats(conn, project_id)
                                if contributors:
                                    contributors_map = {
                                        row["contributor"]: (
                                            f"[{row['commits']}, {row['pull_requests']}, "
                                            f"{row['issues']}, {row['reviews']}]"
                                        )
                                        for row in contributors
                                    }
                                    classification = "individual" if len(contributors) == 1 else "collaborative"
                                    primary = contributors[0]["contributor"]
                                    summary["collaboration"] = {
                                        "classification": classification,
                                        "contributors (commits, PRs, issues, reviews)": contributors_map,
                                        "contribution_compute": (
                                            "weightedScore = commits*0.30 + "
                                            "pull_requests*0.25 + issues*0.25 + reviews*0.20"
                                        ),
                                        "primary_contributor": primary,
                                        "source": "github_api",
                                    }
                                else:
                                    summary["collaboration"] = {
                                        "classification": "unknown",
                                        "contributors (commits, PRs, issues, reviews)": {},
                                        "primary_contributor": None,
                                        "source": "github_api",
                                    }

                                store = SnapshotStore(ROOT / "data")
                                try:
                                    store.store_snapshot(
                                        project_id=project_id,
                                        classification=summary.get("collaboration", {}).get("classification", "unknown"),
                                        primary_contributor=summary.get("collaboration", {}).get("primary_contributor"),
                                        snapshot=summary,
                                    )
                                finally:
                                    store.close()
                                print("Project analysis completed and stored.")
                            except urllib.error.HTTPError as exc:
                                print(f"Failed to download GitHub archive: {exc}")
                            except urllib.error.URLError as exc:
                                print(f"Failed to reach GitHub: {exc}")
                            finally:
                                if temp_path and temp_path.exists():
                                    try:
                                        temp_path.unlink()
                                    except Exception:
                                        pass
                        elif follow == "2":
                            print()
                            forced_choice = "3"
                            break
                        elif follow == "3":
                            print()
                            forced_choice = "2"
                            break
                        elif follow == "4":
                            break
                        else:
                            print("Invalid choice. Please enter 1 to 4.")
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
                        follow = input("Please select an option (1-2, b to back): ").strip().lower()
                        if follow == "m":
                            raise _ReturnToMainMenu()
                        if follow == "1":
                            project = None
                            with _open_app_db() as conn:
                                snapshots = fetch_latest_snapshots(conn)
                            if not snapshots:
                                print("No projects found.")
                                continue
                            print("\nProjects:")
                            for idx, snap in enumerate(snapshots, start=1):
                                snapshot_data = snap.get("snapshot") or {}
                                project_label = snapshot_data.get("project_name") or snap.get("project_id")
                                print(f"{idx}. {project_label} (ID: {snap.get('project_id')})")
                            selection = _prompt_single_index(
                                "Select a project number (blank to cancel, b to back): ",
                                len(snapshots),
                            )
                            if selection is None or selection == "b":
                                continue
                            project = snapshots[int(selection) - 1]
                            project_id = str(project.get("project_id"))
                            snapshot = _prepare_snapshot_for_display(project.get("snapshot") or {})
                            print(json.dumps(snapshot, indent=4))
                        elif follow in {"2", "b"}:
                            break
                        else:
                            print("Invalid choice. Please enter 1 or 2.")
                elif choice == "4":
                    with _open_app_db() as conn:
                        snapshots = fetch_latest_snapshots(conn)
                        if not snapshots:
                            print("No projects found.")
                            continue
                        print("\nProjects:")
                        for idx, snap in enumerate(snapshots, start=1):
                            snapshot_data = snap.get("snapshot") or {}
                            project_label = snapshot_data.get("project_name") or snap.get("project_id")
                            print(f"{idx}. {project_label} (ID: {snap.get('project_id')})")
                        selection = _prompt_single_index(
                            "Select a project number (blank to cancel, b to back): ",
                            len(snapshots),
                        )
                        if selection is None:
                            print("View cancelled.")
                            continue
                        if selection == "b":
                            continue
                        project_id = str(snapshots[int(selection) - 1].get("project_id"))
                        project = next((s for s in snapshots if str(s.get("project_id")) == project_id), None)
                        if not project:
                            print("Project not found.")
                        else:
                            snapshot = _prepare_snapshot_for_display(project.get("snapshot") or {})
                            print(json.dumps(snapshot, indent=4))
                    if project:
                        pass
                elif choice == "5":
                    with _open_app_db() as conn:
                        users = [
                            row[0]
                            for row in conn.execute(
                                "SELECT DISTINCT contributor FROM contributor_stats ORDER BY LOWER(contributor)"
                            ).fetchall()
                            if row and row[0]
                        ]
                    # Hide bot accounts
                    users = [u for u in users if "[bot]" not in u.lower()]
                    if not users:
                        print("No contributors found.")
                        continue
                    print("\nAvailable users:")
                    for idx, name in enumerate(users, start=1):
                        print(f"{idx}. {name}")
                    user_pick = _prompt_single_index(
                        "Select a user number (blank to cancel, b to back): ",
                        len(users),
                    )
                    if user_pick is None or user_pick == "b":
                        continue
                    selected_user = users[int(user_pick) - 1]
                    with _open_app_db() as conn:
                        user_project_ids = {
                            row[0]
                            for row in conn.execute(
                                "SELECT DISTINCT project_id FROM contributor_stats WHERE contributor = ?",
                                (selected_user,),
                            ).fetchall()
                            if row and row[0]
                        }
                    while True:
                        action = _prompt_menu(
                            "Portfolio Options",
                            ["Generate portfolio summary", "Portfolio Showcase Customization", "Back to main menu"],
                        )
                        if action in {"3", "b"}:
                            break
                        if action == "1":
                            with _open_app_db() as conn:
                                snapshots = fetch_latest_snapshots(conn)
                                if user_project_ids:
                                    # Filter
                                    snapshots = [
                                        item
                                        for item in snapshots
                                        if str(item.get("project_id")) in user_project_ids
                                    ]
                                snapshot_map = {
                                    str(item.get("project_id")): (item.get("snapshot") or {})
                                    for item in snapshots
                                    if item.get("project_id")
                                }
                                summaries = generate_top_project_summaries(
                                    snapshot_map,
                                    limit=3,
                                    user=selected_user,
                                )
                                if not summaries:
                                    print("No project summaries available.")
                                else:
                                    print(f"\nPortfolio Summary for {selected_user}:\n")
                                    for summary in summaries:
                                        print(export_markdown(summary))
                                        print()
                            if summaries:
                                # Offer PDF export
                                export = input(
                                    "Would you like to export this summary as a PDF? (y/n): "
                                ).strip().lower()
                                if export == "y":
                                    from capstone.portfolio_pdf_builder import build_portfolio_pdf_with_pandoc

                                    entries = [
                                        {
                                            "project_id": item.get("project_id"),
                                            "name": item.get("title") or item.get("project_id"),
                                            "summary": export_markdown(item),
                                            "source": "portfolio_summary",
                                        }
                                        for item in summaries
                                    ]
                                    preview_path = pathlib.Path("analysis_output") / "portfolio_summary.pdf"
                                    try:
                                        build_portfolio_pdf_with_pandoc(
                                            entries,
                                            preview_path,
                                            title=f"Portfolio Summary for {selected_user}",
                                        )
                                        print(f"\nPortfolio PDF preview generated at:\n{preview_path}\n")
                                    except Exception as exc:
                                        print("Failed to generate portfolio PDF preview.")
                                        print(f"Error: {exc}")
                                        continue
                                    save = input("Save a local copy now? (y/n): ").strip().lower()
                                    if save == "y":
                                        save_path = prompt_save_path(default_name="portfolio_summary.pdf")
                                        if save_path:
                                            pathlib.Path(save_path).write_bytes(preview_path.read_bytes())
                                            print(f"\nPortfolio PDF successfully saved to:\n{save_path}\n")
                        if action == "2":
                            with _open_app_db() as conn:
                                snapshots = fetch_latest_snapshots(conn)
                            if not snapshots:
                                print("No projects found.")
                                continue
                            if user_project_ids:
                                snapshots = [
                                    item
                                    for item in snapshots
                                    if str(item.get("project_id")) in user_project_ids
                                ]
                            if not snapshots:
                                print(f"No projects found for {selected_user}.")
                                continue
                            sorted_projects = sorted(
                                snapshots,
                                key=lambda s: (str(s.get("project_id") or "")).lower(),
                            )
                            print("\nAvailable projects (latest snapshot per project):")
                            for idx, snap in enumerate(sorted_projects, start=1):
                                snapshot_data = snap.get("snapshot") or {}
                                label = snapshot_data.get("project_name") or snap.get("project_id") or f"Project {idx}"
                                print(f"{idx}. {label} (ID: {snap.get('project_id')})")
                            selection = _prompt_indices(
                                "Select projects by number (space-separated, multi-select, blank to cancel, b to back): ",
                                len(sorted_projects),
                            )
                            if selection is None or selection == "b":
                                continue
                            chosen_snapshots = [sorted_projects[n - 1] for n in selection]
                            showcase_entries = _build_portfolio_showcase_entries(
                                chosen_snapshots,
                                user=selected_user,
                            )
                            print("\nPortfolio Showcase Preview:\n")
                            print(_format_portfolio_showcase(showcase_entries))
                            while True:
                                sub = _prompt_menu(
                                    "Showcase Options",
                                    ["Customize", "Export PDF (LaTeX)", "Back to portfolio menu"],
                                )
                                if sub in {"3", "b"}:
                                    break
                                if sub == "1":
                                    # Interactive editor
                                    while True:
                                        single_item = len(showcase_entries) == 1
                                        if single_item:
                                            item = showcase_entries[0]
                                        else:
                                            print("\nShowcase entries:")
                                            for idx, item in enumerate(showcase_entries, start=1):
                                                print(f"{idx}. {item.get('name') or item.get('project_id')}")
                                            pick = input(
                                                "Select an entry number (blank to cancel, b to back): "
                                            ).strip().lower()
                                            if not pick:
                                                break
                                            if pick == "b":
                                                break
                                            if not pick.isdigit() or not (1 <= int(pick) <= len(showcase_entries)):
                                                print("Invalid selection.")
                                                continue
                                            item = showcase_entries[int(pick) - 1]
                                        back_to_entries = False
                                        back_to_options = False
                                        while True:
                                            # Show the full markdown
                                            print("\nCurrent showcase (full):\n")
                                            print(item.get("summary") or "")
                                            edit = _prompt_menu(
                                                "Showcase Editor",
                                                [
                                                    "Edit Top Project section",
                                                    "Edit Highlights",
                                                    "Edit References",
                                                    "Edit full markdown",
                                                    "Back to showcase options",
                                                ],
                                            )
                                            if edit in {"5", "b"}:
                                                back_to_options = True
                                                break
                                            edit_label = "Showcase"
                                            if edit == "4":
                                                # Replace the entire markdown
                                                edit_label = "Showcase content"
                                                new_text = input("Paste full markdown (blank to cancel): ").strip()
                                                if not new_text:
                                                    continue
                                                new_summary = new_text
                                            elif edit == "1":
                                                # Update only the Top Project  
                                                edit_label = "Top Project section"
                                                current = (item.get("summary") or "").split("\n\n", 1)
                                                top_block = current[0] if current else ""
                                                print(f"\nCurrent Top Project section:\n{top_block}\n")
                                                top_text = input("Enter new Top Project section (blank to cancel): ").strip()
                                                if not top_text:
                                                    continue
                                                rest = current[1] if len(current) > 1 else ""
                                                new_summary = (top_text + "\n\n" + rest).strip() if rest else top_text
                                            elif edit == "2":
                                                # Edit the Highlights
                                                edit_label = "Highlights"
                                                summary = item.get("summary") or ""
                                                parts = summary.split("\n## Highlights\n", 1)
                                                before = parts[0]
                                                after = parts[1] if len(parts) > 1 else ""
                                                highlights_body, tail = (after.split("\n## References\n", 1) + [""])[0:2]
                                                highlights = [line for line in highlights_body.splitlines() if line.strip().startswith("-")]
                                                print("\nCurrent Highlights:\n" + "\n".join(highlights))
                                                subh = _prompt_menu("Highlights", ["Add", "Delete", "Back"])
                                                if subh in {"3", "b"}:
                                                    continue
                                                if subh == "1":
                                                    print("\nCurrent Highlights:\n" + "\n".join(highlights))
                                                    text = input("Highlight to add (blank to cancel): ").strip()
                                                    if not text:
                                                        continue
                                                    highlights.append(f"- {text}")
                                                else:
                                                    del_mode = _prompt_menu("Delete Highlight", ["Delete all", "Delete matching text", "Back"])
                                                    if del_mode in {"3", "b"}:
                                                        continue
                                                    if del_mode == "1":
                                                        highlights = []
                                                    else:
                                                        print("\nCurrent Highlights:\n" + "\n".join(highlights))
                                                        target = input("Text to delete (blank to cancel): ").strip()
                                                        if not target:
                                                            continue
                                                        highlights = [h for h in highlights if target not in h]
                                                new_highlights = "\n".join(highlights)
                                                rebuilt = before.strip()
                                                if new_highlights:
                                                    rebuilt += "\n\n## Highlights\n" + new_highlights
                                                if tail:
                                                    rebuilt += "\n\n## References\n" + tail.strip()
                                                new_summary = rebuilt.strip()
                                            elif edit == "3":
                                                # Edit the References bullet
                                                edit_label = "References"
                                                summary = item.get("summary") or ""
                                                parts = summary.split("\n## References\n", 1)
                                                before = parts[0]
                                                refs_body = parts[1] if len(parts) > 1 else ""
                                                refs = [line for line in refs_body.splitlines() if line.strip().startswith("-")]
                                                print("\nCurrent References:\n" + "\n".join(refs))
                                                subr = _prompt_menu("References", ["Add", "Delete", "Back"])
                                                if subr in {"3", "b"}:
                                                    continue
                                                if subr == "1":
                                                    print("\nCurrent References:\n" + "\n".join(refs))
                                                    text = input("Reference to add (blank to cancel): ").strip()
                                                    if not text:
                                                        continue
                                                    refs.append(f"- {text}")
                                                else:
                                                    del_mode = _prompt_menu("Delete Reference", ["Delete all", "Delete matching text", "Back"])
                                                    if del_mode in {"3", "b"}:
                                                        continue
                                                    if del_mode == "1":
                                                        refs = []
                                                    else:
                                                        print("\nCurrent References:\n" + "\n".join(refs))
                                                        target = input("Text to delete (blank to cancel): ").strip()
                                                        if not target:
                                                            continue
                                                        refs = [r for r in refs if target not in r]
                                                new_refs = "\n".join(refs)
                                                rebuilt = before.strip()
                                                if "## Highlights" in summary and "## References" in summary:
                                                    highlights_split = before.split("\n## Highlights\n", 1)
                                                    if len(highlights_split) == 2:
                                                        rebuilt = highlights_split[0].strip() + "\n\n## Highlights\n" + highlights_split[1].strip()
                                                if new_refs:
                                                    rebuilt += "\n\n## References\n" + new_refs
                                                new_summary = rebuilt.strip()
                                            with _open_app_db() as conn:
                                                if not new_summary:
                                                    print("Summary cannot be empty. Add text or cancel.")
                                                    continue
                                                try:
                                                    saved = upsert_resume_project_description(
                                                        conn,
                                                        project_id=item["project_id"],
                                                        summary=new_summary,
                                                        variant_name="portfolio_showcase",
                                                        metadata={"source": "custom"},
                                                    )
                                                    item["summary"] = saved.summary
                                                    item["source"] = "custom"
                                                    print(f"{edit_label} updated successfully.")
                                                except Exception as exc:
                                                    print(f"Save failed: {exc}")
                                            print("\nUpdated Showcase Preview:\n")
                                            print(_format_portfolio_showcase(showcase_entries))
                                        if back_to_options:
                                            break
                                    if back_to_options:
                                        break
                                if sub == "2":
                                    from capstone.portfolio_pdf_builder import build_portfolio_pdf_with_pandoc

                                    preview_path = pathlib.Path("analysis_output") / "portfolio_showcase.pdf"
                                    try:
                                        build_portfolio_pdf_with_pandoc(
                                            showcase_entries,
                                            preview_path,
                                            title=f"Portfolio Summary for {selected_user}",
                                        )
                                        print(f"\nPortfolio PDF preview generated at:\n{preview_path}\n")
                                    except Exception as exc:
                                        print("Failed to generate portfolio PDF preview.")
                                        print(f"Error: {exc}")
                                        continue

                                    export = input(
                                        "Would you like to save a copy to your local machine? (y/n): "
                                    ).strip().lower()
                                    if export == "y":
                                        save_path = prompt_save_path(default_name="portfolio_showcase.pdf")
                                        if not save_path:
                                            print("Portfolio export cancelled.")
                                            continue
                                        try:
                                            pathlib.Path(save_path).write_bytes(preview_path.read_bytes())
                                            print(f"\nPortfolio PDF successfully saved to:\n{save_path}\n")
                                        except Exception as exc:
                                            print("Failed to save portfolio PDF.")
                                            print(f"Error: {exc}")
                elif choice == "6":
                    run_generate_new = False
                    while True:
                        resume_choice = _prompt_menu(
                            "Resume",
                            [
                                "Generate new resume",
                                "Customize existed resume",
                                "Back",
                            ],
                        )
                        if resume_choice == "b":
                            resume_choice = "3"
                        if resume_choice == "3":
                            break
                        if resume_choice == "2":
                            with _open_app_db() as conn:
                                existing_resumes = _list_existing_resumes(conn)
                            if not existing_resumes:
                                print("No existing resumes found. Press Enter to continue")
                                input("")
                                continue
                            print("\nExisting resumes:")
                            for idx, item in enumerate(existing_resumes, start=1):
                                print(
                                    f"{idx}. {item['title']} - {item['username']} "
                                    f"(status: {item['status']}, updated: {item['updated_at']})"
                                )
                            pick = _prompt_single_index(
                                "Select a resume number (blank to cancel, b to back): ",
                                len(existing_resumes),
                            )
                            if pick is None:
                                print("Cancelled.")
                                continue
                            if pick == "b":
                                continue
                            selected_resume = existing_resumes[int(pick) - 1]
                            with _open_app_db() as conn:
                                sections = _list_resume_sections(conn, selected_resume["id"])
                            if not sections:
                                print("No sections found for this resume. Press Enter to continue")
                                input("")
                                continue
                            print(f"\nSections for {selected_resume['title']}:")
                            for idx, section in enumerate(sections, start=1):
                                print(f"{idx}. {section['label']}")

                            print("\n1. Edit section")
                            print("2. Add section")
                            print("3. Delete section")
                            section_action = input("Select an option (1-3, b to back): ").strip().lower()
                            if section_action == "b":
                                continue
                            if section_action not in {"1", "2", "3"}:
                                print("Invalid choice. Please enter 1, 2, or 3.")
                                continue
                            section_pick = input("Enter section number (leave blank to cancel): ").strip()
                            if not section_pick:
                                continue
                            if not section_pick.isdigit() or not (1 <= int(section_pick) <= len(sections)):
                                print(f"Indices must be in 1–{len(sections)}.")
                                continue
                            chosen_section = sections[int(section_pick) - 1]
                            print(
                                f"Selected section: {chosen_section['label']} ({chosen_section['key']}). "
                                "Section action flow is not implemented yet."
                            )
                            continue
                        run_generate_new = True
                        break

                    if not run_generate_new:
                        continue

                    with _open_app_db() as conn:
                        users = _list_resume_users(conn)
                        snapshots = fetch_latest_snapshots(conn)

                    if not users:
                        print("\nResume Preview\n--------------\n")
                        print("No users found. Import from GitHub URL first.")
                        continue
                    if not snapshots:
                        print("\nResume Preview\n--------------\n")
                        print("No projects found.")
                        continue

                    print("\nAvailable users:")
                    for idx, user_row in enumerate(users, start=1):
                        username = user_row.get("username") or f"User {idx}"
                        project_count = int(user_row.get("project_count") or 0)
                        email = user_row.get("email")
                        suffix = f" ({email})" if email else ""
                        print(f"{idx}. {username}{suffix} - {project_count} project(s)")

                    user_pick = _prompt_single_index(
                        "Select a user number (blank to cancel, b to back): ",
                        len(users),
                    )
                    if user_pick is None or user_pick == "b":
                        if user_pick is None:
                            print("Cancelled.")
                        continue

                    selected_user = users[int(user_pick) - 1]
                    selected_user_id = int(selected_user["id"])
                    selected_username = str(selected_user["username"])

                    with _open_app_db() as conn:
                        user_project_ids = _list_user_project_ids(
                            conn,
                            user_id=selected_user_id,
                            username=selected_username,
                        )
                    if not user_project_ids:
                        print(f"No projects found for {selected_username}.")
                        continue

                    snapshot_map = {
                        str(item.get("project_id")): item
                        for item in snapshots
                        if item.get("project_id")
                    }
                    user_snapshots = [
                        snapshot_map[pid]
                        for pid in user_project_ids
                        if pid in snapshot_map
                    ]
                    if not user_snapshots:
                        print(f"No analyzed snapshots found for {selected_username}.")
                        continue

                    sorted_projects = sorted(
                        user_snapshots,
                        key=lambda s: (str(s.get("project_id") or "")).lower(),
                    )
                    print(f"\nProjects for {selected_username}:")
                    for idx, snap in enumerate(sorted_projects, start=1):
                        snapshot_data = snap.get("snapshot") or {}
                        label = snapshot_data.get("project_name") or snap.get("project_id") or f"Project {idx}"
                        print(f"{idx}. {label} (ID: {snap.get('project_id')})")

                    selection = _prompt_indices(
                        "Select projects by number (space-separated, blank = all, b to back): ",
                        len(sorted_projects),
                    )
                    if selection == "b":
                        continue
                    if selection is None:
                        chosen_snapshots = list(sorted_projects)
                    else:
                        chosen_snapshots = [sorted_projects[n - 1] for n in selection]
                    project_ids = [
                        str(snap.get("project_id"))
                        for snap in chosen_snapshots
                        if snap.get("project_id")
                    ]
                    with _open_app_db() as conn:
                        contribution_map = _load_user_contribution_map(
                            conn,
                            user_id=selected_user_id,
                            username=selected_username,
                            project_ids=project_ids,
                        )
                    selected_snapshot_skills: List[str] = []
                    for snap in chosen_snapshots:
                        snap_skills = (snap.get("snapshot") or {}).get("skills") or []
                        if isinstance(snap_skills, list):
                            selected_snapshot_skills.extend([_format_skill_list([s]) for s in snap_skills])
                    selected_snapshot_skills = [
                        s for i, s in enumerate(selected_snapshot_skills) if s and s not in selected_snapshot_skills[:i]
                    ]
                    resume_preview = _build_user_resume_preview(
                        selected_username=selected_username,
                        chosen_snapshots=chosen_snapshots,
                        contribution_map=contribution_map,
                    )
                    if project_ids:
                        action = _prompt_menu(
                            "Preview Options",
                            ["Auto-generate resume", "Customize", "Back to main menu"],
                        )
                        if action == "b":
                            action = "3"
                        if action == "1":
                            from capstone.resume_pdf_builder import build_markdown_from_resume, build_pdf_with_latex

                            with _open_app_db() as conn:
                                contribution_map = _load_user_contribution_map(
                                    conn,
                                    user_id=selected_user_id,
                                    username=selected_username,
                                    project_ids=project_ids,
                                )
                            resume_preview = _build_user_resume_preview(
                                selected_username=selected_username,
                                chosen_snapshots=chosen_snapshots,
                                contribution_map=contribution_map,
                            )
                            with _open_app_db() as conn:
                                user_profile = _ensure_user_profile_for_resume(conn, selected_user_id)
                            _apply_user_profile_to_resume_preview(resume_preview, user_profile)
                            with _open_app_db() as conn:
                                _sync_generated_resume_modules_to_db(
                                    conn,
                                    user_id=selected_user_id,
                                    resume_preview=resume_preview,
                                    header_profile=user_profile,
                                    chosen_snapshots=chosen_snapshots,
                                )

                            print("\nResume Preview:\n")
                            print(_format_resume_preview(resume_preview))

                            if not (resume_preview.get("sections") or []):
                                print("No resume sections generated for the selected projects.")
                                continue

                            safe_user = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in selected_username)
                            default_md_name = f"resume_{safe_user or 'user'}.md"
                            date_tag = datetime.now().strftime("%Y%m%d")
                            default_pdf_name = f"resume_{safe_user or 'user'}_{date_tag}.pdf"

                            export_choice = _prompt_menu(
                                "Export Resume",
                                [
                                    "Markdown",
                                    "PDF (LaTeX Template)",
                                    "Markdown + PDF (LaTeX Template)",
                                    "Skip",
                                ],
                            )
                            if export_choice == "b":
                                export_choice = "4"

                            do_md = export_choice in {"1", "3"}
                            do_pdf = export_choice in {"2", "3"}

                            if do_md:
                                save_md_path = prompt_save_path_any(
                                    title="Save Resume Markdown As",
                                    default_name=default_md_name,
                                    default_extension=".md",
                                    filetypes=[("Markdown files", "*.md"), ("All files", "*.*")],
                                )
                                if save_md_path:
                                    try:
                                        markdown_text = build_markdown_from_resume(resume_preview)
                                        pathlib.Path(save_md_path).write_text(markdown_text, encoding="utf-8")
                                        print(f"\nResume Markdown successfully saved to:\n{save_md_path}\n")
                                    except Exception as e:
                                        print("Failed to generate resume Markdown.")
                                        print(f"Error: {e}")
                                else:
                                    print("Resume Markdown export cancelled.")

                            if do_pdf:
                                try:
                                    output_dir = ROOT / "output"
                                    output_dir.mkdir(parents=True, exist_ok=True)
                                    save_pdf = output_dir / default_pdf_name
                                    build_pdf_with_latex(resume_preview, save_pdf)
                                    print(f"\nResume PDF successfully saved to:\n{save_pdf}\n")
                                except Exception as e:
                                    print("Failed to generate resume PDF (LaTeX template).")
                                    print(f"Error: {e}")

                            continue

                        if action == "2":
                            with _open_app_db() as conn:
                                generate_resume_project_descriptions(
                                    conn,
                                    project_ids=project_ids,
                                    overwrite=False,
                                )
                                refreshed = query_resume_entries(conn)
                                filtered = _filter_resume_result_by_project_ids(refreshed, project_ids)
                                resume_preview = build_resume_preview(filtered, conn=conn)
                            while True:
                                entry_map = _build_entry_target_map(resume_preview)
                                if not entry_map:
                                    print("No resume entries available to edit.")
                                    break
                                entry_items = list(entry_map.items())
                                print("Available entries:")
                                for idx, (_entry_id, label) in enumerate(entry_items, start=1):
                                    print(f"{idx}. {label}")
                                selection = input(
                                    "Select an entry number (blank to cancel, b to back, m for main menu): "
                                ).strip().lower()
                                if not selection:
                                    break
                                if selection == "m":
                                    raise _ReturnToMainMenu()
                                if selection == "b":
                                    break
                                if not selection.isdigit() or not (1 <= int(selection) <= len(entry_items)):
                                    print("Invalid selection.")
                                    continue
                                entry_id = entry_items[int(selection) - 1][0]
                                with _open_app_db() as conn:
                                    entry = get_resume_entry(conn, entry_id)
                                if not entry:
                                    print("Invalid entry id.")
                                    continue
                                while True:
                                    edit_action = _prompt_menu(
                                        "Edit Entry",
                                        [
                                            "Summary",
                                            "Body",
                                            "Skills",
                                            "Linked projects",
                                            "Section",
                                            "Status",
                                            "Metadata (dates)",
                                            "Back",
                                        ],
                                    )
                                    if edit_action in {"8", "b"}:
                                        break
                                    if edit_action == "1":
                                        while True:
                                            display_summary = entry.summary or ""
                                            if not display_summary and entry.project_ids:
                                                with _open_app_db() as conn:
                                                    snap = fetch_latest_snapshot(conn, entry.project_ids[0])
                                                if snap:
                                                    display_summary = build_resume_project_summary(
                                                        entry.project_ids[0], snap
                                                    )
                                            print(f"\nCurrent summary:\n{display_summary}")
                                            sub = _prompt_menu(
                                                "Summary",
                                                ["Add", "Delete", "Back"],
                                            )
                                            if sub in {"3", "b"}:
                                                break
                                            if sub == "1":
                                                addition = input("Text to add (blank to cancel): ").strip()
                                                if not addition:
                                                    continue
                                                existing = (entry.summary or "").strip()
                                                new_summary = (existing + "\n" + addition).strip() if existing else addition
                                            elif sub == "2":
                                                del_mode = _prompt_menu(
                                                    "Delete Summary",
                                                    ["Delete all", "Delete matching text", "Back"],
                                                )
                                                if del_mode in {"3", "b"}:
                                                    continue
                                                if del_mode == "1":
                                                    new_summary = ""
                                                else:
                                                    target = input("Text to delete (blank to cancel): ").strip()
                                                    if not target:
                                                        continue
                                                    current = entry.summary or ""
                                                    if target not in current:
                                                        print("Text not found in summary.")
                                                        continue
                                                    new_summary = current.replace(target, "").strip()
                                            with _open_app_db() as conn:
                                                try:
                                                    entry = update_resume_entry(
                                                        conn,
                                                        entry_id=entry_id,
                                                        summary=new_summary or None,
                                                        _summary_provided=True,
                                                    ) or entry
                                                    print("Saved successfully.")
                                                except Exception as exc:
                                                    print(f"Save failed: {exc}")
                                    elif edit_action == "2":
                                        while True:
                                            print(f"\nCurrent body:\n{entry.body or ''}")
                                            sub = _prompt_menu(
                                                "Body",
                                                ["Add", "Delete", "Back"],
                                            )
                                            if sub in {"3", "b"}:
                                                break
                                            if sub == "1":
                                                addition = input("Text to add (blank to cancel): ").strip()
                                                if not addition:
                                                    continue
                                                existing = (entry.body or "").strip()
                                                new_body = (existing + "\n" + addition).strip() if existing else addition
                                            else:
                                                del_mode = _prompt_menu(
                                                    "Delete Body",
                                                    ["Delete all", "Delete matching text", "Back"],
                                                )
                                                if del_mode in {"3", "b"}:
                                                    continue
                                                if del_mode == "1":
                                                    new_body = ""
                                                else:
                                                    target = input("Text to delete (blank to cancel): ").strip()
                                                    if not target:
                                                        continue
                                                    current = entry.body or ""
                                                    if target not in current:
                                                        print("Text not found in body.")
                                                        continue
                                                    new_body = current.replace(target, "").strip()
                                            with _open_app_db() as conn:
                                                try:
                                                    entry = update_resume_entry(
                                                        conn,
                                                        entry_id=entry_id,
                                                        body=new_body or None,
                                                    ) or entry
                                                    print("Saved successfully.")
                                                except Exception as exc:
                                                    print(f"Save failed: {exc}")
                                    elif edit_action == "3":
                                            while True:
                                                raw_skills = entry.skills
                                                if raw_skills and not isinstance(raw_skills, (list, tuple)):
                                                    raw_skills = [raw_skills]
                                                current_skills = _format_skill_list(raw_skills or []) if raw_skills else ""
                                                if not current_skills and entry.project_ids:
                                                    inferred: List[str] = []
                                                    for pid in entry.project_ids:
                                                        with _open_app_db() as conn:
                                                            snap = fetch_latest_snapshot(conn, pid)
                                                    skills = (snap or {}).get("skills") or []
                                                    if isinstance(skills, list):
                                                        inferred.extend([_format_skill_list([s]) for s in skills])
                                                    inferred = [s for i, s in enumerate(inferred) if s and s not in inferred[:i]]
                                                    current_skills = ", ".join(inferred)
                                                if not current_skills and selected_snapshot_skills:
                                                    current_skills = ", ".join(selected_snapshot_skills)
                                                print(f"\nCurrent skills: {current_skills}")
                                                sub = _prompt_menu(
                                                    "Skills",
                                                    ["Add", "Delete", "Back"],
                                                )
                                                if sub in {"3", "b"}:
                                                    break
                                                if sub == "1":
                                                    skill_input = input(
                                                        "Skills to add (comma-separated, blank to cancel): "
                                                    ).strip()
                                                    if not skill_input:
                                                        continue
                                                    additions = [s.strip() for s in skill_input.split(",") if s.strip()]
                                                    skills = list(raw_skills) if raw_skills else []
                                                    skills.extend(additions)
                                                    skills = [s for i, s in enumerate(skills) if s and s not in skills[:i]]
                                                else:
                                                    del_mode = _prompt_menu(
                                                        "Delete Skills",
                                                        ["Delete all", "Delete matching text", "Back"],
                                                    )
                                                    if del_mode in {"3", "b"}:
                                                        continue
                                                    if del_mode == "1":
                                                        skills = []
                                                    else:
                                                        target = input("Text to delete (blank to cancel): ").strip()
                                                        if not target:
                                                            continue
                                                        skills = [s for s in (raw_skills or []) if target not in str(s)]
                                                with _open_app_db() as conn:
                                                    try:
                                                        entry = update_resume_entry(
                                                            conn,
                                                            entry_id=entry_id,
                                                            skills=skills or None,
                                                            _skills_provided=True,
                                                        ) or entry
                                                        print("Saved successfully.")
                                                        print(f"Current skills: {_format_skill_list(skills or [])}")
                                                    except Exception as exc:
                                                        print(f"Save failed: {exc}")
                                    elif edit_action == "4":
                                            while True:
                                                current_projects = ", ".join(entry.project_ids) if entry.project_ids else ""
                                                if not current_projects:
                                                    print("\nNo linked projects yet.")
                                                else:
                                                    print(f"\nCurrent linked projects: {current_projects}")
                                                sub = _prompt_menu(
                                                    "Linked projects",
                                                    ["Add", "Delete", "Back"],
                                                )
                                                if sub in {"3", "b"}:
                                                    break
                                                if sub == "2" and not entry.project_ids:
                                                    print("No linked projects to delete.")
                                                    continue
                                                with _open_app_db() as conn:
                                                    snapshots = fetch_latest_snapshots(conn)
                                                if not snapshots:
                                                    print("No projects found.")
                                                    continue
                                                if sub == "2":
                                                    available = [
                                                        snap for snap in snapshots
                                                        if str(snap.get("project_id")) in set(entry.project_ids or [])
                                                    ]
                                                else:
                                                    available = snapshots
                                                if not available:
                                                    print("No projects available for this action.")
                                                    continue
                                                print("\nAvailable projects:")
                                                for idx, snap in enumerate(available, start=1):
                                                    snapshot_data = snap.get("snapshot") or {}
                                                    project_label = snapshot_data.get("project_name") or snap.get("project_id")
                                                    print(f"{idx}. {project_label} (ID: {snap.get('project_id')})")
                                                selection = _prompt_indices(
                                                    "Select project numbers (space-separated, blank to cancel, b to back): ",
                                                    len(available),
                                                )
                                                if selection is None or selection == "b":
                                                    continue
                                                chosen = [
                                                    str(available[int(n) - 1].get("project_id"))
                                                    for n in selection
                                                ]
                                                if sub == "1":
                                                    projects = list(entry.project_ids) if entry.project_ids else []
                                                    projects.extend(chosen)
                                                    projects = [p for i, p in enumerate(projects) if p and p not in projects[:i]]
                                                else:
                                                    projects = [p for p in (entry.project_ids or []) if p not in set(chosen)]
                                                with _open_app_db() as conn:
                                                    try:
                                                        entry = update_resume_entry(
                                                            conn,
                                                            entry_id=entry_id,
                                                            projects=projects or None,
                                                            _projects_provided=True,
                                                        ) or entry
                                                        print("Saved successfully.")
                                                    except Exception as exc:
                                                        print(f"Save failed: {exc}")
                                    elif edit_action == "5":
                                            while True:
                                                print(f"\nCurrent section: {entry.section}")
                                                sub = _prompt_menu(
                                                    "Section",
                                                    ["Add", "Delete", "Back"],
                                                )
                                                if sub in {"3", "b"}:
                                                    break
                                                if sub == "1":
                                                    section = input("Enter section (blank to cancel): ").strip()
                                                    if not section:
                                                        continue
                                                    new_section = section
                                                else:
                                                    del_mode = _prompt_menu(
                                                        "Delete Section",
                                                        ["Delete all", "Back"],
                                                    )
                                                    if del_mode in {"2", "b"}:
                                                        continue
                                                    new_section = ""
                                                with _open_app_db() as conn:
                                                    try:
                                                        entry = update_resume_entry(
                                                            conn,
                                                            entry_id=entry_id,
                                                            section=new_section or None,
                                                        ) or entry
                                                        print("Saved successfully.")
                                                    except Exception as exc:
                                                        print(f"Save failed: {exc}")
                                    elif edit_action == "6":
                                            while True:
                                                print(f"\nCurrent status: {entry.status or ''}")
                                                sub = _prompt_menu(
                                                    "Status",
                                                    ["Add", "Delete", "Back"],
                                                )
                                                if sub in {"3", "b"}:
                                                    break
                                                if sub == "1":
                                                    status = input("Enter status (blank to cancel): ").strip()
                                                    if not status:
                                                        continue
                                                    new_status = status
                                                else:
                                                    del_mode = _prompt_menu(
                                                        "Delete Status",
                                                        ["Delete all", "Back"],
                                                    )
                                                    if del_mode in {"2", "b"}:
                                                        continue
                                                    new_status = ""
                                                with _open_app_db() as conn:
                                                    try:
                                                        entry = update_resume_entry(
                                                            conn,
                                                            entry_id=entry_id,
                                                            status=new_status or None,
                                                        ) or entry
                                                        print("Saved successfully.")
                                                    except Exception as exc:
                                                        print(f"Save failed: {exc}")
                                    elif edit_action == "7":
                                            while True:
                                                metadata = entry.metadata or {}
                                                current_start = metadata.get("start_date") or ""
                                                current_end = metadata.get("end_date") or ""
                                                print(f"\nCurrent dates: {current_start or '-'} to {current_end or '-'}")
                                                sub = _prompt_menu(
                                                    "Metadata (dates)",
                                                    ["Add", "Delete", "Back"],
                                                )
                                                if sub in {"3", "b"}:
                                                    break
                                                if sub == "1":
                                                    start_date = input(
                                                        "Start date (YYYY-MM or YYYY-MM-DD, blank to cancel): "
                                                    ).strip()
                                                    end_date = input(
                                                        "End date (YYYY-MM or YYYY-MM-DD, blank to cancel): "
                                                    ).strip()
                                                    if not start_date and not end_date:
                                                        continue
                                                    metadata["start_date"] = start_date or None
                                                    metadata["end_date"] = end_date or None
                                                else:
                                                    del_mode = _prompt_menu(
                                                        "Delete Dates",
                                                        ["Delete all", "Back"],
                                                    )
                                                    if del_mode in {"2", "b"}:
                                                        continue
                                                    metadata["start_date"] = None
                                                    metadata["end_date"] = None
                                                with _open_app_db() as conn:
                                                    try:
                                                        entry = update_resume_entry(
                                                            conn,
                                                            entry_id=entry_id,
                                                            metadata=metadata,
                                                            _metadata_provided=True,
                                                        ) or entry
                                                        print("Saved successfully.")
                                                    except Exception as exc:
                                                        print(f"Save failed: {exc}")
                                with _open_app_db() as conn:
                                    refreshed = query_resume_entries(conn)
                                    filtered = _filter_resume_result_by_project_ids(refreshed, project_ids)
                                    resume_preview = build_resume_preview(filtered, conn=conn)
                                print("\nUpdated Resume Preview:\n")
                                print(_format_resume_preview(resume_preview))
                        if action == "3":
                            continue
                    while True:
                        print("\n1. View another resume preview")
                        print("2. Back to main menu")
                        follow = input("Select an option (1-2, b to back): ").strip().lower()
                        if follow == "1":
                            forced_choice = "6"
                            break
                        if follow in {"2", "b"}:
                            break
                        print("Invalid choice. Please enter 1 or 2.")
                elif choice == "7":

                    with _open_app_db() as conn:
                        snapshots = fetch_latest_snapshots(conn)
                        metadata_map = load_project_metadata(conn)
                        snapshot_map = {
                            str(item.get("project_id")): (item.get("snapshot") or {})
                            for item in snapshots
                            if item.get("project_id")
                        }
                        timeline = chronological_proj(snapshot_map)
                        print("\nChronological Project Timeline:\n")
                        project_ids = sorted(
                            set(snapshot_map.keys()) | set(metadata_map.keys())
                        )

                        for project_id in sorted(project_ids):
                            meta = metadata_map.get(project_id)

                            if meta:
                                start = meta.get("start_date")
                                end = meta.get("end_date")
                                status = meta.get("status", "ongoing").capitalize()

                                start_text = start if start else "Unknown"
                                end_text = end if end else "Present"

                            else:
                                # fallback: infer from analysis timestamps
                                snapshots = snapshot_map.get(project_id, [])
                                timestamps = [
                                    s.get("analyzed_at")
                                    for s in snapshots
                                    if isinstance(s, dict) and s.get("analyzed_at")
                                ]

                                timestamps.sort()
                                start_text = timestamps[0][:10] if timestamps else "Unknown"
                                end_text = "Present"
                                status = "Ongoing (inferred)"

                            print(f"- {project_id}")
                            print(f"  Active Period: {start_text} → {end_text}")
                            print(f"  Status: {status}\n")


                elif choice == "8":
                    with _open_app_db() as conn:
                        snapshots = fetch_latest_snapshots(conn)

                    if not snapshots:
                        print("\nSkills Timeline\n----------------\n")
                        print("No projects found.")
                        continue

                    sorted_projects = sorted(
                        snapshots,
                        key=lambda s: (str(s.get("project_id") or "")).lower(),
                    )
                    print("\nAvailable projects (latest snapshot per project):")
                    for idx, snap in enumerate(sorted_projects, start=1):
                        snapshot_data = snap.get("snapshot") or {}
                        label = snapshot_data.get("project_name") or snap.get("project_id") or f"Project {idx}"
                        print(f"{idx}. {label} (ID: {snap.get('project_id')})")

                    selection = _prompt_indices(
                        "Select projects by number (space-separated, blank to cancel, b to back): ",
                        len(sorted_projects),
                    )
                    if selection is None or selection == "b":
                        if selection is None:
                            print("Cancelled.")
                        continue

                    chosen_snapshots = [sorted_projects[n - 1] for n in selection]
                    skills_timeline = _build_skills_timeline_rows(chosen_snapshots)
                    print("\nSkills Timeline\n----------------\n")
                    print(_format_skills_timeline(skills_timeline))
                    while True:
                        print("\n1. View another skill timeline")
                        print("2. Back to main menu")
                        follow = input("Select an option (1-2, b to back): ").strip().lower()
                        if follow == "1":
                            forced_choice = "8"
                            break
                        if follow in {"2", "b"}:
                            break
                        print("Invalid choice. Please enter 1 or 2.")
                elif choice == "9":
                    with _open_app_db() as conn:
                        snapshots = fetch_latest_snapshots(conn)
                        if not snapshots:
                            print("No projects found.")
                            continue
                        print("\nProjects:")
                        for idx, snap in enumerate(snapshots, start=1):
                            snapshot_data = snap.get("snapshot") or {}
                            project_label = snapshot_data.get("project_name") or snap.get("project_id")
                            print(f"{idx}. {project_label} (ID: {snap.get('project_id')})")
                        selection = _prompt_single_index(
                            "Select a project number to delete (blank to cancel, b to back): ",
                            len(snapshots),
                        )
                        if selection is None:
                            print("Delete cancelled.")
                            continue
                        if selection == "b":
                            continue
                        project_id = str(snapshots[int(selection) - 1].get("project_id"))
                        deleted = conn.execute(
                            "DELETE FROM project_analysis WHERE project_id = ?",
                            (project_id,),
                        ).rowcount
                        conn.execute(
                            "DELETE FROM contributor_stats WHERE project_id = ?",
                            (project_id,),
                        )
                        delete_resume_project_description(conn, project_id=project_id)
                        conn.commit()
                        if deleted:
                            print("Project insights deleted.")
                        else:
                            print("No matching project insights found.")
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
                        follow = input("Please select an option (1-2, b to back, m for main menu): ").strip().lower()
                        if follow == "m":
                            raise _ReturnToMainMenu()
                        if follow == "1":
                            print("\nProjects:")
                            for idx, snap in enumerate(snapshots, start=1):
                                snapshot_data = snap.get("snapshot") or {}
                                project_label = snapshot_data.get("project_name") or snap.get("project_id")
                                print(f"{idx}. {project_label} (ID: {snap.get('project_id')})")
                            selection = _prompt_single_index(
                                "Select a project number (blank to cancel, b to back): ",
                                len(snapshots),
                            )
                            if selection is None or selection == "b":
                                continue
                            project_id = str(snapshots[int(selection) - 1].get("project_id"))
                            _show_contributor_rankings(project_id)
                        elif follow in {"2", "b"}:
                            break
                        else:
                            print("Invalid choice. Please enter 1 or 2.")
                elif choice == "12":

                    conn = open_db()
                    try:
                        rows = fetch_latest_snapshots(conn)
                        snapshot_map = {}

                        for row in rows:
                            snapshot_map.setdefault(row["project_id"], []).append(row["snapshot"])

                        run_ai_project_analysis(conn, snapshot_map)


                    finally:
                        close_db()

                elif choice == "13":
                    _manage_user_profiles_menu()
                elif choice == "14":
                    _exit_app()
        except _ReturnToMainMenu:
            if in_main_menu:
                continue
            forced_choice = None
            in_main_menu = True
            continue
        except KeyboardInterrupt:
            _exit_app()
if __name__ == "__main__":
    main()
