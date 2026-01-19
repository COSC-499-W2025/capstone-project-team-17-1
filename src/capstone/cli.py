from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from capstone.llm_client import build_default_llm
from .consent import (
    ConsentError,
    ExternalPermissionDenied,
    ensure_consent,
    ensure_external_permission,
    grant_consent,
    prompt_for_consent,
    revoke_consent,
    export_consent,
)
from .config import load_config, reset_config
from .insight_store import InsightStore
from .logging_utils import get_logger
from .modes import ModeResolution, resolve_mode
from .project_ranking import WEIGHTS as RANK_WEIGHTS, rank_projects_from_snapshots
from .services import (
    ArchiveAnalysisError,
    ArchiveAnalyzerService,
    ConfigService,
    ConsentService,
    RankingService,
    SnapshotStore,
    SnapshotSummaryService,
    TimelineService,
    TopSummaryService,
)
from .storage import close_db, fetch_contributor_rankings, fetch_latest_snapshots, open_db
from .zip_analyzer import ZipAnalyzer
from .job_matching import match_job_to_project, build_resume_snippet
from .resume_retrieval import (
    build_resume_preview,
    export_resume,
    query_resume_entries,
    ensure_resume_schema,
    get_resume_project_description,
    list_resume_project_descriptions,
    upsert_resume_project_description,
)
from .job_matching import build_jd_profile, rank_projects_for_job
from .resume_generator import generate_tailored_resume, resume_to_json, resume_to_pdf
from .portfolio_retrieval import create_app as create_portfolio_app
from .portfolio_retrieval import ensure_indexes as ensure_portfolio_indexes
from .portfolio_retrieval import list_snapshots as list_portfolio_snapshots
from .portfolio_retrieval import get_latest_snapshot as get_portfolio_latest
from .top_project_summaries import export_markdown, generate_top_project_summaries
from .github_contributors import sync_contributor_stats

logger = get_logger(__name__)

def _print(obj):
    print(json.dumps(obj, indent=2))

# ----------------------------- Parsers ---------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Capstone zip analyzer (Python implementation)."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # consent
    consent_parser = subparsers.add_parser("consent", help="Manage user consent")
    consent_sub = consent_parser.add_subparsers(dest="consent_scope", required=True)

    # ─── General (local) consent ────────────────────────────────────────────────
    general_parser = consent_sub.add_parser("local", help="Manage local analysis consent")
    general_sub = general_parser.add_subparsers(dest="consent_action", required=True)

    grant_parser = general_sub.add_parser("grant", help="Grant local consent")
    grant_parser.add_argument(
        "--decision",
        choices=["allow", "allow_once", "allow_always"],
        default="allow",
        help="Consent decision to record",
    )

    revoke_parser = general_sub.add_parser("revoke", help="Revoke local consent")
    revoke_parser.add_argument(
        "--decision",
        choices=["deny", "deny_once", "deny_always"],
        default="deny",
        help="Revocation detail",
    )

    general_sub.add_parser("status", help="Show current local consent state")

    # ─── External consent ───────────────────────────────────────────────────────
    external_parser = consent_sub.add_parser("external", help="Manage external analysis consent")
    external_sub = external_parser.add_subparsers(dest="consent_action", required=True)

    external_grant = external_sub.add_parser("grant", help="Grant external analysis consent")
    external_grant.add_argument(
        "--decision",
        choices=["allow", "allow_once", "allow_always"],
        default="allow",
        help="External consent decision to record",
    )

    external_revoke = external_sub.add_parser("revoke", help="Revoke external analysis consent")
    external_revoke.add_argument(
        "--decision",
        choices=["deny", "deny_once", "deny_always"],
        default="deny",
        help="Revocation detail for external consent",
    )

    external_sub.add_parser("status", help="Show current external consent state")

    # config
    config_parser = subparsers.add_parser("config", help="Manage configuration")
    config_sub = config_parser.add_subparsers(dest="config_action", required=True)
    config_sub.add_parser(
        "show", help="Display current configuration (decrypted in-memory)"
    )
    config_sub.add_parser("reset", help="Reset configuration to defaults")

    # analyze
    analyze_parser = subparsers.add_parser(
        "analyze", help="Scan a zip archive for metadata"
    )
    analyze_parser.add_argument(
        "archive", type=str, help="Path to the .zip archive to analyze"
    )
    analyze_parser.add_argument(
        "--metadata-output",
        type=Path,
        default=Path("analysis_output/metadata.jsonl"),
        help="Path to save JSONL metadata",
    )
    analyze_parser.add_argument(
        "--summary-output",
        type=Path,
        default=Path("analysis_output/summary.json"),
        help="Path to save the analysis summary",
    )
    analyze_parser.add_argument(
        "--analysis-mode",
        choices=["local", "external", "auto"],
        default="local",
        help="Requested analysis mode (default: local)",
    )
    analyze_parser.add_argument(
        "--quiet", action="store_true", help="Suppress terminal output and only write files"
    )
    analyze_parser.add_argument(
        "--summary-to-stdout",
        action="store_true",
        help="Print summary JSON directly to stdout",
    )
    analyze_parser.add_argument(
        "--project-id",
        type=str,
        default=None,
        help="Identifier used when persisting analysis snapshots",
    )
    analyze_parser.add_argument(
        "--db-dir",
        type=Path,
        default=None,
        help="Directory where the analysis database (SQLite) should be stored",
    )

    # import-repo: clone a git repo by URL and run the same analysis pipeline
    import_parser = subparsers.add_parser(
        "import-repo",
        help="Clone a git repository from a URL, zip it, and analyse the snapshot",
    )
    import_parser.add_argument("url", type=str, help="Git repository URL (e.g., https://github.com/org/repo)")
    import_parser.add_argument(
        "--branch",
        type=str,
        default=None,
        help="Optional branch or tag to checkout before analysis",
    )
    import_parser.add_argument(
        "--depth",
        type=int,
        default=0,
        help="Shallow clone depth (0 means full clone)",
    )
    import_parser.add_argument(
        "--metadata-output",
        type=Path,
        default=Path("analysis_output/metadata.jsonl"),
        help="Path to save JSONL metadata",
    )
    import_parser.add_argument(
        "--summary-output",
        type=Path,
        default=Path("analysis_output/summary.json"),
        help="Path to save the analysis summary",
    )
    import_parser.add_argument(
        "--analysis-mode",
        choices=["local", "external", "auto"],
        default="local",
        help="Requested analysis mode (default: local)",
    )
    import_parser.add_argument(
        "--quiet", action="store_true", help="Suppress terminal output and only write files"
    )
    import_parser.add_argument(
        "--summary-to-stdout",
        action="store_true",
        help="Print summary JSON directly to stdout",
    )
    import_parser.add_argument(
        "--project-id",
        type=str,
        default=None,
        help="Identifier used when persisting analysis snapshots",
    )
    import_parser.add_argument(
        "--db-dir",
        type=Path,
        default=None,
        help="Directory where the analysis database (SQLite) should be stored",
    )

    # clean (Req. 18)
    clean_parser = subparsers.add_parser(
        "clean", help="Delete generated analysis outputs safely"
    )
    clean_parser.add_argument(
        "--path",
        type=Path,
        default=Path("analysis_output"),
        help="Directory to wipe (default: analysis_output)",
    )
    clean_parser.add_argument(
        "--all",
        action="store_true",
        help="Also remove ./out if it exists",
    )
    rank_parser = subparsers.add_parser("rank-projects", help="Rank analysed projects by contribution weights")

    rank_parser.add_argument(
        "--user",
        type=str,
        default=None,
        help="Contributor name to weight when ranking (defaults to primary contributor)",
    )
    rank_parser.add_argument(
        "--db-dir",
        type=Path,
        default=None,
        help="Directory containing the analysis database (defaults to internal storage)",
    )
    rank_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of projects to display",
    )
        # summarize-projects (Step 2 – CLI wrapper around top project summaries)
    summarize_parser = subparsers.add_parser(
        "summarize-projects",
        help="Summarize top ranked projects for a user",
    )
    summarize_parser.add_argument(
        "--db-dir",
        type=Path,
        default=None,
        help="Directory where capstone.db is stored",
    )
    summarize_parser.add_argument(
        "--user",
        type=str,
        default=None,
        help="Contributor name/email to personalize ranking (defaults to primary contributor)",
    )
    summarize_parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Maximum number of projects to summarize",
    )
    summarize_parser.add_argument(
        "--use-llm",
        action="store_true",
        help="Use the default LLM to polish summaries",
    )
    summarize_parser.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format",
    )
        # generate-resume (Step 4)
    resume_parser = subparsers.add_parser(
        "generate-resume",
        help="Generate a tailored resume JSON (and optional PDF) for a target company",
    )
    resume_parser.add_argument(
        "--company",
        required=True,
        help="Target company name (e.g., 'Microsoft')",
    )
    resume_parser.add_argument(
        "--job-file",
        type=Path,
        required=True,
        help="Path to a text file containing the job description",
    )
    resume_parser.add_argument(
        "--db-dir",
        type=Path,
        default=None,
        help="Directory containing the analysis database (defaults to internal storage)",
    )
    resume_parser.add_argument(
        "--max-projects",
        type=int,
        default=3,
        help="Maximum number of projects to include in the resume",
    )
    resume_parser.add_argument(
        "--json-output",
        type=Path,
        default=None,
        help="Where to write the tailored resume JSON (default: stdout only)",
    )
    resume_parser.add_argument(
        "--pdf-output",
        type=Path,
        default=None,
        help="Optional path to write a one-page resume PDF",
    )

    job_parser = subparsers.add_parser(
        "job-match",
        help="Compare a job description with a project and print a resume snippet",
    )
    job_parser.add_argument(
        "--project-id",
        required=True,
        help="Project id to compare",
    )
    job_parser.add_argument(
        "--db-dir",
        type=Path,
        default=None,
        help="Directory where capstone.db is stored",
    )
    job_parser.add_argument(
        "--job-file",
        type=Path,
        required=True,
        help="Path to a text file that contains the job description",
    )

    resume_parser = subparsers.add_parser(
        "resume",
        help="Retrieve previously generated resume entries and export them",
    )
    resume_parser.add_argument(
        "--db-dir",
        type=Path,
        default=None,
        help="Directory where capstone.db is stored",
    )
    resume_parser.add_argument(
        "--section",
        dest="sections",
        action="append",
        help="Filter resume entries by section (can be repeated)",
    )
    resume_parser.add_argument(
        "--keyword",
        dest="keywords",
        action="append",
        help="Filter entries that mention the keyword in title, summary, or body",
    )
    resume_parser.add_argument(
        "--start-date",
        dest="start_date",
        type=str,
        help="Only include entries created on/after this ISO date",
    )
    resume_parser.add_argument(
        "--end-date",
        dest="end_date",
        type=str,
        help="Only include entries created on/before this ISO date",
    )
    resume_parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum number of resume entries to load",
    )
    resume_parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Offset for pagination when retrieving resume entries",
    )
    resume_parser.add_argument(
        "--format",
        choices=["preview", "markdown", "json", "pdf"],
        default="preview",
        help="How to render the retrieved resume data",
    )
    resume_parser.add_argument(
        "--output",
        type=Path,
        help="Optional file path for exports (recommended for PDF output)",
    )
    resume_parser.add_argument(
        "--include-outdated",
        action="store_true",
        help="Include entries flagged as outdated or expired",
    )

    resume_project_parser = subparsers.add_parser(
        "resume-project",
        help="Save or retrieve resume-specific project wording",
    )
    resume_project_parser.add_argument(
        "action",
        choices=["set", "get", "list"],
        help="Action to perform",
    )
    resume_project_parser.add_argument(
        "--db-dir",
        type=Path,
        default=None,
        help="Directory where capstone.db is stored",
    )
    resume_project_parser.add_argument(
        "--project-id",
        action="append",
        help="Project id to target (repeatable for list)",
    )
    resume_project_parser.add_argument(
        "--summary",
        type=str,
        help="Resume-specific project summary text",
    )
    resume_project_parser.add_argument(
        "--summary-file",
        type=Path,
        help="File containing the resume-specific project summary text",
    )
    resume_project_parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum number of resume project descriptions to load",
    )
    resume_project_parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Offset for pagination when listing resume project descriptions",
    )

    api_parser = subparsers.add_parser(
        "api",
        help="Run the local API service",
    )
    api_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host interface to bind (default: 127.0.0.1)",
    )
    api_parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Port to listen on (default: 5000)",
    )
    api_parser.add_argument(
        "--db-dir",
        type=Path,
        default=None,
        help="Directory where capstone.db is stored",
    )
    api_parser.add_argument(
        "--token",
        type=str,
        default=None,
        help="Optional Bearer token to protect API routes",
    )

    # portfolio retrieval
    portfolio_parser = subparsers.add_parser(
        "portfolio",
        help="Retrieve stored portfolio snapshots",
    )
    portfolio_sub = portfolio_parser.add_subparsers(dest="portfolio_action", required=True)

    portfolio_latest = portfolio_sub.add_parser(
        "latest", help="Fetch the latest snapshot for a project"
    )
    portfolio_latest.add_argument("--project-id", required=True, help="Project id to fetch")
    portfolio_latest.add_argument(
        "--db-dir",
        type=Path,
        default=None,
        help="Directory where capstone.db is stored",
    )

    portfolio_list = portfolio_sub.add_parser(
        "list", help="List snapshots for a project (paginated)"
    )
    portfolio_list.add_argument("--project-id", required=True, help="Project id to list")
    portfolio_list.add_argument(
        "--db-dir",
        type=Path,
        default=None,
        help="Directory where capstone.db is stored",
    )
    portfolio_list.add_argument("--page", type=int, default=1, help="Page number (1-indexed)")
    portfolio_list.add_argument("--page-size", type=int, default=20, help="Page size (max 200)")
    portfolio_list.add_argument(
        "--sort",
        type=str,
        default="created_at:desc",
        help="Sort field and direction, e.g. created_at:desc or classification:asc",
    )
    portfolio_list.add_argument(
        "--classification",
        type=str,
        help="Optional classification filter (e.g., collaborative/individual)",
    )
    portfolio_list.add_argument(
        "--primary-contributor",
        type=str,
        help="Optional primary contributor filter",
    )

    # collaboration summary (thin wrapper to inspect latest collab state)
    collab_summary_parser = subparsers.add_parser(
        "collab-summary",
        help="Show collaboration summary (classification and contributors) for a project",
    )
    collab_summary_parser.add_argument("--project-id", required=True, help="Project id to inspect")
    collab_summary_parser.add_argument(
        "--db-dir",
        type=Path,
        default=None,
        help="Directory where capstone.db is stored",
    )

    # tech summary (thin wrapper to inspect languages/frameworks for a project)
    tech_summary_parser = subparsers.add_parser(
        "tech-summary",
        help="Show technology summary (languages/frameworks) for a project",
    )
    tech_summary_parser.add_argument("--project-id", required=True, help="Project id to inspect")
    tech_summary_parser.add_argument(
        "--db-dir",
        type=Path,
        default=None,
        help="Directory where capstone.db is stored",
    )

    # skill summary (thin wrapper to inspect skills/timeline for a project)
    skill_summary_parser = subparsers.add_parser(
        "skill-summary",
        help="Show skill summary (skills and timeline) for a project",
    )
    skill_summary_parser.add_argument("--project-id", required=True, help="Project id to inspect")
    skill_summary_parser.add_argument(
        "--db-dir",
        type=Path,
        default=None,
        help="Directory where capstone.db is stored",
    )

    # contributor stats
    contributors_parser = subparsers.add_parser(
        "contributors",
        help="Sync or rank contributor stats for a GitHub repository",
    )
    contributors_sub = contributors_parser.add_subparsers(dest="contributors_action", required=True)

    contributors_sync = contributors_sub.add_parser(
        "sync",
        help="Fetch GitHub contribution stats and store them",
    )
    contributors_sync.add_argument("--repo-url", required=True, help="GitHub repository URL")
    contributors_sync.add_argument(
        "--project-id",
        default=None,
        help="Project id to store (defaults to owner/repo)",
    )
    contributors_sync.add_argument(
        "--token",
        default=None,
        help="GitHub token (defaults to GITHUB_TOKEN env var)",
    )
    contributors_sync.add_argument(
        "--db-dir",
        type=Path,
        default=None,
        help="Directory where capstone.db is stored",
    )
    contributors_sync.add_argument(
        "--max-contributors",
        type=int,
        default=50,
        help="Maximum number of contributors to fetch",
    )

    contributors_rank = contributors_sub.add_parser(
        "rank",
        help="Rank contributors for a project",
    )
    contributors_rank.add_argument("--project-id", required=True, help="Project id to rank")
    contributors_rank.add_argument(
        "--db-dir",
        type=Path,
        default=None,
        help="Directory where capstone.db is stored",
    )
    contributors_rank.add_argument(
        "--sort-by",
        choices=["score", "commits", "line_changes", "pull_requests", "issues", "reviews"],
        default="score",
        help="Metric to sort by",
    )

    # metrics summary (thin wrapper to inspect file metrics/timeline for a project)
    metrics_summary_parser = subparsers.add_parser(
        "metrics-summary",
        help="Show file metrics summary (file counts/sizes/timeline) for a project",
    )
    metrics_summary_parser.add_argument("--project-id", required=True, help="Project id to inspect")
    metrics_summary_parser.add_argument(
        "--db-dir",
        type=Path,
        default=None,
        help="Directory where capstone.db is stored",
    )

    # top-project summary (exports markdown/readme)
    # Generate top project summary exports.
    top_parser = subparsers.add_parser(
        "top-summary",
        help="Generate top project summary exports",
    )
    top_parser.add_argument(
        "--db-dir",
        type=Path,
        default=None,
        help="Directory where capstone.db is stored",
    )
    top_parser.add_argument(
        "--project-id",
        type=str,
        help="Optional project id; defaults to top-ranked project",
    )
    top_parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("analysis_output"),
        help="Directory to write summary exports",
    )
    top_parser.add_argument(
        "--pdf-output",
        type=Path,
        default=None,
        help="Optional PDF one-pager path (writes markdown content with .pdf extension)",
    )

    # timelines
    # Export chronological list of projects to CSV.
    pt_parser = subparsers.add_parser(
        "projects-timeline",
        help="Export chronological list of projects to CSV",
    )
    pt_parser.add_argument(
        "--db-dir",
        type=Path,
        default=None,
        help="Directory where capstone.db is stored",
    )
    pt_parser.add_argument(
        "--output",
        type=Path,
        default=Path("analysis_output/projects_timeline.csv"),
        help="CSV output path",
    )

    # Export chronological list of skills to CSV.
    st_parser = subparsers.add_parser(
        "skills-timeline",
        help="Export chronological list of skills to CSV",
    )
    st_parser.add_argument(
        "--db-dir",
        type=Path,
        default=None,
        help="Directory where capstone.db is stored",
    )
    st_parser.add_argument(
        "--output",
        type=Path,
        default=Path("analysis_output/skills_timeline.csv"),
        help="CSV output path",
    )

    # insight safe-delete dry-run
    idr_parser = subparsers.add_parser(
        "insight-dry-run",
        help="Dry-run safe delete for an insight id",
    )
    idr_parser.add_argument("--db", default="analysis_output/insights_demo.db", help="Path to insight DB")
    idr_parser.add_argument("--id", required=True, help="Insight id to delete")
    idr_parser.add_argument(
        "--strategy", choices=["block", "cascade"], default="block", help="Deletion strategy"
    )

    # insight demo (create, link, dry-run, soft-delete)
    # Create sample insights, wire dependencies, and run safe-delete demo.
    demo_parser = subparsers.add_parser(
        "insight-demo",
        help="Create sample insights, run dry-run and soft-delete, output summary",
    )
    demo_parser.add_argument("--db", default="analysis_output/insights_cli.db", help="Path to insight DB")
    demo_parser.add_argument("--reset-db", action="store_true", help="Delete existing DB before running")
    demo_parser.add_argument("--title-a", default="Perf", help="Title for insight A")
    demo_parser.add_argument("--owner-a", default="alice", help="Owner for insight A")
    demo_parser.add_argument("--title-b", default="Root cause", help="Title for insight B")
    demo_parser.add_argument("--owner-b", default="bob", help="Owner for insight B")
    demo_parser.add_argument("--dry-strategy", choices=["block", "cascade"], default="block")
    demo_parser.add_argument("--soft-strategy", choices=["block", "cascade"], default="cascade")

    return parser


# ----------------------------- Handlers --------------------------------
def _handle_job_match(args: argparse.Namespace) -> int:
    job_text = args.job_file.read_text(encoding="utf-8", errors="ignore")
    result = match_job_to_project(job_text, args.project_id, args.db_dir)
    snippet = build_resume_snippet(result)
    print(snippet)
    return 0


def _handle_resume(args: argparse.Namespace) -> int:
    store = SnapshotStore(args.db_dir)
    conn = store.open()
    try:
        ensure_resume_schema(conn)
        result = query_resume_entries(
            conn,
            sections=args.sections,
            keywords=args.keywords,
            start_date=args.start_date,
            end_date=args.end_date,
            include_outdated=args.include_outdated,
            limit=args.limit,
            offset=args.offset,
        )
        if args.format == "preview":
            preview = build_resume_preview(result, conn=conn)
            print(json.dumps(preview, indent=2))
            return 0

        entries = result.entries
        if not entries:
            print("No resume entries found that match the provided filters.")
            return 0

        project_ids = sorted({pid for entry in entries for pid in entry.project_ids})
        description_map = {}
        if project_ids:
            descriptions = list_resume_project_descriptions(
                conn,
                project_ids=project_ids,
                limit=len(project_ids),
            )
            description_map = {item.project_id: item for item in descriptions}
        data = export_resume(
            entries,
            fmt=args.format,
            destination=args.output,
            project_descriptions=description_map,
        )
        if args.output:
            print(f"Wrote resume {args.format} export to {args.output}")
            return 0

        if args.format == "pdf":
            import base64
            encoded = base64.b64encode(data).decode("ascii")
            print("base64_pdf_payload:")
            print(encoded)
        else:
            print(data.decode("utf-8"))
        return 0
    finally:
        store.close()
        try:
            close_db()
        except Exception:
            pass


def _handle_resume_project(args: argparse.Namespace) -> int:
    store = SnapshotStore(args.db_dir)
    conn = store.open()
    try:
        ensure_resume_schema(conn)
        project_ids = args.project_id or []
        if args.action in {"set", "get"}:
            if len(project_ids) != 1:
                print("resume-project set/get requires exactly one --project-id", file=sys.stderr)
                return 2
            project_id = project_ids[0]

        if args.action == "set":
            summary = args.summary
            if args.summary_file:
                summary = args.summary_file.read_text(encoding="utf-8", errors="ignore").strip()
            if not summary:
                print("resume-project set requires --summary or --summary-file", file=sys.stderr)
                return 2
            result = upsert_resume_project_description(
                conn,
                project_id=project_id,
                summary=summary,
            )
            print(json.dumps(result.to_dict(), indent=2))
            return 0

        if args.action == "get":
            result = get_resume_project_description(conn, project_id)
            if not result:
                print(json.dumps({"error": "NotFound", "detail": "No resume project description found"}, indent=2))
                return 0
            print(json.dumps(result.to_dict(), indent=2))
            return 0

        if args.action == "list":
            results = list_resume_project_descriptions(
                conn,
                project_ids=project_ids or None,
                limit=args.limit,
                offset=args.offset,
            )
            print(json.dumps([item.to_dict() for item in results], indent=2))
            return 0

        print("Unknown resume-project action", file=sys.stderr)
        return 1
    finally:
        store.close()


def _handle_api(args: argparse.Namespace) -> int:
    db_dir = str(args.db_dir) if args.db_dir else None
    app = create_portfolio_app(db_dir=db_dir, auth_token=args.token)
    app.run(host=args.host, port=args.port)
    return 0


def _handle_portfolio(args: argparse.Namespace) -> int:
    store = SnapshotStore(args.db_dir)
    conn = store.open()
    try:
        ensure_portfolio_indexes(conn)
        if args.portfolio_action == "latest":
            data = get_portfolio_latest(conn, args.project_id)
            if data is None:
                print(json.dumps({"error": "NotFound", "detail": "No snapshots found"}, indent=2))
                return 0
            print(json.dumps({"data": data, "projectId": args.project_id}, indent=2))
            return 0

        if args.portfolio_action == "list":
            sort_field, _, sort_dir = (args.sort or "created_at:desc").partition(":")
            items, total = list_portfolio_snapshots(
                conn,
                project_id=args.project_id,
                page=args.page,
                page_size=args.page_size,
                sort_field=sort_field or "created_at",
                sort_dir=sort_dir or "desc",
                classification=args.classification,
                primary_contributor=args.primary_contributor,
            )
            payload = {
                "total": total,
                "page": args.page,
                "pageSize": args.page_size,
                "data": [s.snapshot for s in items],
                "projectId": args.project_id,
            }
            print(json.dumps(payload, indent=2))
            return 0

        print("Unknown portfolio action", file=sys.stderr)
        return 1
    finally:
        store.close()


def _handle_collab_summary(args: argparse.Namespace) -> int:
    store = SnapshotStore(args.db_dir)
    service = SnapshotSummaryService(store)
    try:
        payload = service.collab_summary(args.project_id)
        print(json.dumps(payload, indent=2))
        return 0
    finally:
        store.close()


def _handle_tech_summary(args: argparse.Namespace) -> int:
    store = SnapshotStore(args.db_dir)
    service = SnapshotSummaryService(store)
    try:
        payload = service.tech_summary(args.project_id)
        print(json.dumps(payload, indent=2))
        return 0
    finally:
        store.close()


def _handle_skill_summary(args: argparse.Namespace) -> int:
    store = SnapshotStore(args.db_dir)
    service = SnapshotSummaryService(store)
    try:
        payload = service.skill_summary(args.project_id)
        print(json.dumps(payload, indent=2))
        return 0
    finally:
        store.close()


def _handle_contributors(args: argparse.Namespace) -> int:
    if args.contributors_action == "sync":
        token = args.token or os.environ.get("GITHUB_TOKEN")
        if not token:
            print("GitHub token missing. Provide --token or set GITHUB_TOKEN.", file=sys.stderr)
            return 2
        stats = sync_contributor_stats(
            repo_url=args.repo_url,
            token=token,
            project_id=args.project_id,
            db_dir=args.db_dir,
            max_contributors=args.max_contributors,
        )
        for index, row in enumerate(stats, start=1):
            print(
                f"{index}. {row.contributor} "
                f"(Total Score: {row.score:.2f}, Commits: {row.commits}, "
                f"Line Changes: {row.line_changes}, PRs: {row.pull_requests}, "
                f"Issues: {row.issues}, Reviews: {row.reviews})"
            )
        return 0

    if args.contributors_action == "rank":
        conn = open_db(args.db_dir)
        try:
            rankings = fetch_contributor_rankings(conn, args.project_id, sort_by=args.sort_by)
        finally:
            close_db()
        if not rankings:
            print("No contributor stats found.")
            return 0
        for index, row in enumerate(rankings, start=1):
            print(
                f"{index}. {row['contributor']} "
                f"(Total Score: {row['score']:.2f}, Commits: {row['commits']}, "
                f"Line Changes: {row['line_changes']}, PRs: {row['pull_requests']}, "
                f"Issues: {row['issues']}, Reviews: {row['reviews']})"
            )
        return 0

    print("Unknown contributors action", file=sys.stderr)
    return 1


def _handle_metrics_summary(args: argparse.Namespace) -> int:
    store = SnapshotStore(args.db_dir)
    service = SnapshotSummaryService(store)
    try:
        payload = service.metrics_summary(args.project_id)
        print(json.dumps(payload, indent=2))
        return 0
    finally:
        store.close()


def _handle_top_summary(args: argparse.Namespace) -> int:
    g = globals()
    store = SnapshotStore(args.db_dir, fetch_all_fn=g.get("fetch_latest_snapshots", fetch_latest_snapshots))
    service = TopSummaryService(store, ranker=g.get("rank_projects_from_snapshots", rank_projects_from_snapshots))
    try:
        payload = service.generate(
            project_id=args.project_id,
            output_dir=args.output_dir,
            pdf_output=args.pdf_output,
        )
        if payload.get("error"):
            print(json.dumps(payload, indent=2))
            return 1
        if payload.get("detail"):
            print(payload.get("detail"))
            return 0
        print(json.dumps(payload, indent=2))
        return 0
    finally:
        store.close()


def _handle_projects_timeline(args: argparse.Namespace) -> int:
    rows = TimelineService().export_projects(args.db_dir, args.output)
    print(json.dumps({"rows": rows, "output": str(args.output)}, indent=2))
    return 0


def _handle_skills_timeline(args: argparse.Namespace) -> int:
    rows = TimelineService().export_skills(args.db_dir, args.output)
    print(json.dumps({"rows": rows, "output": str(args.output)}, indent=2))
    return 0


def _handle_insight_dry_run(args: argparse.Namespace) -> int:
    store = InsightStore(args.db)
    try:
        result = store.dry_run_delete(args.id, strategy=args.strategy)
        print(json.dumps(result, indent=2))
        return 0
    finally:
        try:
            store.close()
        except Exception:
            pass

def _handle_insight_demo(args: argparse.Namespace) -> int:
    db_path = Path(args.db)
    if args.reset_db and db_path.exists():
        db_path.unlink()
    store = InsightStore(str(db_path))
    try:
        # Create two insights and link b -> a to exercise dependency and delete flow.
        a = store.create_insight(args.title_a, args.owner_a)
        b = store.create_insight(args.title_b, args.owner_b)
        store.add_dep_on_insight(b, a)
        result = {
            "db": str(db_path),
            "a": a,
            "b": b,
            "dependents": store.get_dependents(a),
            "dry_run": store.dry_run_delete(a, strategy=args.dry_strategy),
            "soft_delete": store.soft_delete(a, who="cli", strategy=args.soft_strategy),
            "trash": store.list_trash(),
            "audit": store.get_audit(a),
        }
        print(json.dumps(result, indent=2))
        return 0
    finally:
        try:
            store.close()
        except Exception:
            pass


def _handle_consent(args: argparse.Namespace) -> int:
    # ---------------------------
    # LOCAL CONSENT (existing)
    # ---------------------------
    if args.consent_scope == "local":
        if args.consent_action == "grant":
            config = grant_consent(decision=args.decision)
            logger.info("Local consent granted: %s", config.consent)
            print("Local consent granted.")
            return 0

        if args.consent_action == "revoke":
            config = revoke_consent(decision=args.decision)
            logger.info("Local consent revoked: %s", config.consent)
            print("Local consent revoked.")
            return 0

        if args.consent_action == "status":
            state = export_consent()
            print(json.dumps(state, indent=2))
            return 0

    # ---------------------------
    # EXTERNAL CONSENT (new)
    # ---------------------------
    if args.consent_scope == "external":
        from capstone.consent import (
            grant_external_consent,
            revoke_external_consent,
            show_external_consent_status,
        )

        if args.consent_action == "grant":
            grant_external_consent(decision=args.decision)
            logger.info("External consent granted (%s)", args.decision)
            return 0

        if args.consent_action == "revoke":
            revoke_external_consent(decision=args.decision)
            logger.info("External consent revoked (%s)", args.decision)
            return 0

        if args.consent_action == "status":
            show_external_consent_status()
            return 0

    print("Unknown consent action", file=sys.stderr)
    return 1

def _handle_preview(args: argparse.Namespace) -> int:
    from capstone.sample_preview import run_preview  # we will create this file

    try:
        run_preview(zip_path=args.zip_path)
        return 0
    except Exception as exc:
        print(f"Preview failed: {exc}", file=sys.stderr)
        return 1


def _handle_config(args: argparse.Namespace) -> int:
    g = globals()  # allow legacy tests 
    config_service = ConfigService(
        load_fn=g.get("load_config", load_config),
        reset_fn=g.get("reset_config", reset_config),
        export_consent_fn=g.get("export_consent", export_consent),
    )
    config_state = config_service.load()
    if args.config_action == "show":
        payload = {
            "consent": config_state.consent.__dict__,
            "preferences": config_state.preferences.__dict__,
        }
        print(json.dumps(payload, indent=2))
        return 0
    if args.config_action == "reset":
        reset = config_service.reset()
        logger.info("Configuration reset to defaults")
        print("Configuration reset. Current preferences:")
        print(json.dumps(reset.preferences.__dict__, indent=2))
        return 0
    print("Unknown config action", file=sys.stderr)
    return 1


def _infer_repo_name(url: str) -> str:
    slug = url.rstrip("/").rsplit("/", 1)[-1]
    name = slug.split(":")[-1].removesuffix(".git")
    return name or "repository"


def _clone_repository(url: str, *, branch: str | None, depth: int, dest_root: Path) -> Path:
    repo_name = _infer_repo_name(url)
    target_dir = dest_root / repo_name
    cmd = ["git", "clone"]
    if depth and depth > 0:
        cmd += ["--depth", str(depth)]
    if branch:
        cmd += ["--branch", branch]
    cmd += [url, str(target_dir)]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except FileNotFoundError:
        raise RuntimeError("git executable not found in PATH") from None
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.strip() or exc.stdout.strip() or str(exc)
        raise RuntimeError(f"git clone failed: {detail}") from exc
    return target_dir


def _write_git_log(repo_path: Path) -> None:
    """Persist git log into .git/logs for downstream contribution analysis."""
    cmd = [
        "git",
        "-C",
        str(repo_path),
        "log",
        "--no-color",
        "--pretty=format:commit:%H|%an|%ae|%ct|%s",
        "--numstat",
    ]
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.strip() or exc.stdout.strip() or str(exc)
        logger.warning("Unable to capture git log for %s: %s", repo_path, detail)
        return
    except FileNotFoundError:
        logger.warning("git executable not found; skipping git log capture for %s", repo_path)
        return

    log_dir = repo_path / ".git" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "capstone_git_log").write_text(result.stdout, encoding="utf-8")
    # Also drop a copy at repo root so we can delete most of .git before zipping.
    (repo_path / "capstone_git_log.txt").write_text(result.stdout, encoding="utf-8")


def _prune_repository(repo_path: Path) -> None:
    """Drop bulky/non-essential folders before zipping to avoid noisy warnings."""
    prune_targets = [
        ".git",
        ".venv",
    ]
    for rel in prune_targets:
        target = repo_path / rel
        if target.exists():
            try:
                shutil.rmtree(target)
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("Failed to prune %s: %s", target, exc)


def _handle_analyze(args: argparse.Namespace) -> int:
    archive_service = ArchiveAnalyzerService(ZipAnalyzer())
    archive_path, payload, code = archive_service.validate_archive(args.archive)
    if payload:
        print(json.dumps(payload), file=sys.stderr)
        return code

    g = globals()  # keep test patches 
    consent_service = ConsentService(
        ensure_consent_fn=g.get("ensure_consent", ensure_consent),
        prompt_fn=g.get("prompt_for_consent", prompt_for_consent),
        grant_fn=g.get("grant_consent", grant_consent),
        ensure_external_fn=g.get("ensure_external_permission", ensure_external_permission),
    )
    try:
        consent = consent_service.ensure_local_consent()
    except ConsentError as exc:
        privacy_message = (
            "This analysis runs locally and reads file metadata (paths, sizes, timestamps). "
            "No data leaves your machine unless you later export results."
        )
        print(privacy_message)
        try:
            consent = consent_service.prompt_and_grant()
            logger.info("Consent granted interactively: %s", consent)
        except ConsentError:
            payload = {"error": "ConsentRequired", "detail": str(exc)}
            print(json.dumps(payload), file=sys.stderr)
            return 2

    config = ConfigService(
        load_fn=g.get("load_config", load_config),
        reset_fn=g.get("reset_config", reset_config),
        export_consent_fn=g.get("export_consent", export_consent),
    ).load()
    mode: ModeResolution = resolve_mode(args.analysis_mode, consent)
    try:
        consent_service.ensure_external(
            mode,
            service="capstone.external.analysis",
            data_types=["artifact metadata", "language statistics", "collaboration summaries"],
            purpose="Generate remote analytics for the selected archive",
            destination="Configured external analysis provider",
            privacy="No source code is transmitted; only derived metadata is shared.",
            source="cli",
        )
    except ExternalPermissionDenied as exc:
        payload = {"error": "ExternalPermissionDenied", "detail": str(exc)}
        print(json.dumps(payload), file=sys.stderr)
        return 6

    try:
        summary = archive_service.analyze(
            zip_path=archive_path,
            metadata_path=args.metadata_output,
            summary_path=args.summary_output,
            mode=mode,
            preferences=config.preferences,
            project_id=args.project_id,
            db_dir=args.db_dir,
        )
    except ArchiveAnalysisError as exc:
        print(json.dumps(exc.payload), file=sys.stderr)
        return 3

    if summary.get("warnings") and not args.quiet:
        print(json.dumps({"warnings": summary["warnings"]}, indent=2), file=sys.stderr)

    # --- summary_to_stdout mode: behave exactly like original tests expect ---
    if args.summary_to_stdout:
        print(json.dumps(summary, indent=2))
        return 0

    # --- human-summary mode (original behavior) ---
    if not args.quiet:
        _print_human_summary(summary, args)

    # --- Save analysis snapshot to SQLite (for resume / ranking) ---
    store = SnapshotStore(args.db_dir)
    try:
        store.store_snapshot(
            project_id=summary.get("project_id") or args.project_id or archive_path.stem,
            classification=summary.get("collaboration", {}).get("classification", "unknown"),
            primary_contributor=summary.get("collaboration", {}).get("primary_contributor"),
            snapshot=summary,
        )
        if not args.quiet:
            print("[analyze] Snapshot saved to SQLite database.")
    except Exception as exc:
        print(f"[analyze] WARNING: Failed to store snapshot in DB: {exc}", file=sys.stderr)
    finally:
        store.close()

    return 0


def _handle_import_repo(args: argparse.Namespace) -> int:
    with tempfile.TemporaryDirectory(prefix="capstone-import-") as temp_dir:
        temp_path = Path(temp_dir)
        try:
            repo_path = _clone_repository(args.url, branch=args.branch, depth=args.depth or 0, dest_root=temp_path)
        except Exception as exc:
            print(f"[import-repo] Failed to clone repository: {exc}", file=sys.stderr)
            return 4

        # Capture git log to feed collaboration analysis (avoids relying on reflog only).
        try:
            _write_git_log(repo_path)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to persist git log for analysis: %s", exc)

        # Remove bulky/unnecessary bits that trigger warnings but don't affect analysis.
        _prune_repository(repo_path)

        try:
            archive_path = Path(shutil.make_archive(str(temp_path / repo_path.name), "zip", root_dir=repo_path))
        except Exception as exc:
            print(f"[import-repo] Failed to package repository: {exc}", file=sys.stderr)
            return 5

        project_id = args.project_id or repo_path.name
        analyze_args = argparse.Namespace(
            archive=str(archive_path),
            metadata_output=args.metadata_output,
            summary_output=args.summary_output,
            analysis_mode=args.analysis_mode,
            quiet=args.quiet,
            summary_to_stdout=args.summary_to_stdout,
            project_id=project_id,
            db_dir=args.db_dir,
        )
        return _handle_analyze(analyze_args)


def _handle_rank_projects(args: argparse.Namespace) -> int:
    g = globals()
    store = SnapshotStore(args.db_dir, fetch_all_fn=g.get("fetch_latest_snapshots", fetch_latest_snapshots))
    service = RankingService(store, ranker=g.get("rank_projects_from_snapshots", rank_projects_from_snapshots))
    try:
        rankings, snapshot_map = service.rank(user=args.user, limit=args.limit)
        if not snapshot_map:
            print("No project analyses available for ranking.")
            return 0

        contributor_label = args.user or "primary contributor"
        print(f"Project rankings for {contributor_label}:")
        for index, ranking in enumerate(rankings, start=1):
            print(f"{index}. {ranking.project_id} — score {ranking.score:.4f}")
            for factor in ("artifact", "bytes", "recency", "activity", "diversity"):
                weight = RANK_WEIGHTS[factor]
                print(f"   - {factor}: weight {weight:.2f}, contribution {ranking.breakdown[factor]:.3f}")
            details = ranking.details
            print(
                "     raw metrics: "
                f"files={details['artifact_count']:.0f}, "
                f"bytes={details['total_bytes']:.0f}, "
                f"recency_days={details['recency_days']:.1f}, "
                f"active_days={details['active_days']:.0f}, "
                f"diversity={details['diversity_elements']:.0f}, "
                f"contribution_ratio={details['contribution_ratio']:.2f}"
            )
        return 0
    finally:
        store.close()

def _handle_summarize_projects(args: argparse.Namespace) -> int:
    """Summarize top ranked projects, optionally using an LLM."""
    g = globals()  # tests patch fetch_latest_snapshots
    close_fn = g.get("close_db", close_db)
    store = SnapshotStore(
        args.db_dir,
        open_fn=g.get("open_db", open_db),
        fetch_all_fn=g.get("fetch_latest_snapshots", fetch_latest_snapshots),
        close_fn=close_fn,
    )
    service = RankingService(store, ranker=g.get("rank_projects_from_snapshots", rank_projects_from_snapshots))
    try:
        rankings, snapshot_map = service.rank(user=args.user, limit=args.limit)
        if not snapshot_map:
            print("No project analyses available for summary.")
            return 0

        if not rankings:
            print("No ranked projects available for summary.")
            return 0

        # Optional LLM
        llm = None
        use_llm = bool(args.use_llm)
        if use_llm:
            llm = build_default_llm()

        summaries = generate_top_project_summaries(
            snapshots=snapshot_map,
            rankings=rankings,
            limit=args.limit,
            llm=llm,
            use_llm=use_llm,
        )

        if args.format == "json":
            def to_jsonable(s):
                if isinstance(s, dict):
                    return s
                if hasattr(s, "model_dump"):
                    return s.model_dump()
                if hasattr(s, "__dict__"):
                    return s.__dict__
                return {"value": str(s)}

            payload = [to_jsonable(s) for s in summaries]
            print(json.dumps(payload, indent=2))
        else:
            parts = []
            for s in summaries:
                try:
                    parts.append(export_markdown(s))
                except Exception:
                    md = getattr(s, "markdown", None) or str(s)
                    parts.append(md)
            print("\n\n".join(parts))

        return 0
    finally:
        store.close()


def _handle_generate_resume(args: argparse.Namespace) -> int:
    """
    Step 4: glue together job description matching (step 2),
    company profile (step 3), and resume generation.
    """
    # 1) Read the job description text
    try:
        jd_text = args.job_file.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"[generate-resume] Failed to read job description: {exc}", file=sys.stderr)
        return 3

    if not jd_text.strip():
        print("[generate-resume] Job description file is empty.", file=sys.stderr)
        return 3

    # 2) Build a JD profile (step 2 helper – lives in job_matching.py)
    jd_profile = build_jd_profile(jd_text)

    # 3) Rank projects for this job (step 2 output)
    #
    # rank_projects_for_job is expected to return a sequence of JobMatchResult-like
    # objects (project_id, score, matched_required, matched_preferred, matched_keywords).
    # If your implementation has a slightly different signature, tweak this call.
    # 3) Load latest project snapshots
    # 3) Open DB and load all project snapshots
    store = SnapshotStore(args.db_dir)
    snapshots = store.fetch_all_latest()
    store.close()

    if not snapshots:
        print("[generate-resume] No analyzed projects found in database. Run 'capstone analyze' first.")
        return 4

    project_snapshots = [row["snapshot"] for row in snapshots]


    # 4) Rank projects for this job
    matches = rank_projects_for_job(
        jd_profile,
        project_snapshots,
    )


    # 4) Combine with the company profile + build tailored resume object (step 4)
    resume = generate_tailored_resume(
        company_name=args.company,
        jd_profile=jd_profile,
        matches=matches,
        max_projects=args.max_projects,
    )

    # 5) JSON output (always)
    resume_json = resume_to_json(resume)

    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(resume_json, indent=2), encoding="utf-8")
        print(f"[generate-resume] Wrote JSON resume to {args.json_output}")
    else:
        # Default: pretty-print to stdout
        print(json.dumps(resume_json, indent=2))

    # 6) Optional PDF output
    if args.pdf_output:
        resume_to_pdf(resume, args.pdf_output)       
        print(f"[generate-resume] Wrote PDF resume to {args.pdf_output}")

    return 0

def _print_human_summary(summary: dict[str, object], args: argparse.Namespace) -> None:
    print(f"Analysis mode: {summary['resolved_mode']}")
    print(f"Metadata written to: {summary['metadata_output']}")
    print(f"Summary written to: {args.summary_output}")
    file_summary = summary.get("file_summary", {})
    if file_summary:
        print(
            f"Processed {file_summary.get('file_count', 0)} files, total {file_summary.get('total_bytes', 0)} bytes"
        )
    languages = summary.get("languages", {})
    if languages:
        top_languages = ", ".join(f"{lang} ({count})" for lang, count in languages.items())
        print(f"Detected languages: {top_languages}")
    frameworks = summary.get("frameworks", [])
    if frameworks:
        print(f"Identified frameworks: {', '.join(frameworks)}")
    collaboration = summary.get("collaboration", {})
    if collaboration:
        print("Collaboration classification:", collaboration.get("classification", "unknown"))
        contributors = collaboration.get("contributors (commits, line changes, reviews)", {}) or {}
        if contributors:
            formula = collaboration.get(
                "contribution_compute",
                "weightedScore = commits*1.0 + line_changes*0.0 + reviews*0.5",
            )
            print(f"Contribution formula: {formula}")
            print("Contributors (commits, line changes, reviews):")
            def _parse_counts(data) -> tuple[int, int, int]:
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

            sorted_items = sorted(
                contributors.items(),
                key=lambda item: (-_parse_counts(item[1])[0], item[0]),
            )
            for author, values in sorted_items:
                commits, lines, reviews = _parse_counts(values)
                print(f" - {author}: {commits}, {lines}, {reviews}")
    print(f"Scan duration: {summary.get('scan_duration_seconds', 0)} seconds")


# ----------------------------- Clean -----------------------------------
def _safe_wipe_dir(target: Path, repo_root: Path) -> int:
    """Remove a file/dir under repo_root. Refuse anything outside."""
    try:
        target = target.resolve()
        repo_root = repo_root.resolve()
        try:
            target.relative_to(repo_root)  # raises ValueError if outside
        except ValueError:
            print(f"[clean] Refusing to delete outside repo: {target}", file=sys.stderr)
            return 2

        if not target.exists():
            print(f"[clean] Nothing to remove at: {target}")
            return 0

        if target.is_dir():
            shutil.rmtree(target)
            print(f"[clean] Removed directory: {target}")
        else:
            target.unlink()
            print(f"[clean] Removed file: {target}")
        return 0
    except Exception as e:
        print(f"[clean] Error removing {target}: {e}", file=sys.stderr)
        return 1


def _handle_clean(args: argparse.Namespace) -> int:
    repo_root = Path.cwd()
    rc = _safe_wipe_dir(Path(args.path), repo_root)
    if args.all:
        rc |= _safe_wipe_dir(repo_root / "out", repo_root)
    return rc


# ----------------------------- Main ------------------------------------
def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "consent":
        return _handle_consent(args)
    elif args.command == "preview":
        return _handle_preview(args)
    if args.command == "config":
        return _handle_config(args)
    if args.command == "analyze":
        return _handle_analyze(args)
    if args.command == "import-repo":
        return _handle_import_repo(args)
    if args.command == "clean":
        return _handle_clean(args)
    if args.command == "rank-projects":
        return _handle_rank_projects(args)
    if args.command == "rank-projects":
        return _handle_rank_projects(args)
    if args.command == "summarize-projects":
        return _handle_summarize_projects(args)
    if args.command == "job-match":
        return _handle_job_match(args)

    if args.command == "job-match":
        return _handle_job_match(args)
    if args.command == "resume":
        return _handle_resume(args)
    if args.command == "resume-project":
        return _handle_resume_project(args)
    if args.command == "api":
        return _handle_api(args)
    if args.command == "generate-resume":
        return _handle_generate_resume(args)
    if args.command == "portfolio":
        return _handle_portfolio(args)
    if args.command == "collab-summary":
        return _handle_collab_summary(args)
    if args.command == "tech-summary":
        return _handle_tech_summary(args)
    if args.command == "skill-summary":
        return _handle_skill_summary(args)
    if args.command == "contributors":
        return _handle_contributors(args)
    if args.command == "metrics-summary":
        return _handle_metrics_summary(args)
    if args.command == "top-summary":
        return _handle_top_summary(args)
    if args.command == "projects-timeline":
        return _handle_projects_timeline(args)
    if args.command == "skills-timeline":
        return _handle_skills_timeline(args)
    if args.command == "insight-dry-run":
        return _handle_insight_dry_run(args)
    if args.command == "insight-demo":
        return _handle_insight_demo(args)

    parser.print_help()
    p = argparse.ArgumentParser(prog="capstone")
    p.add_argument("--db", default="capstone.db", help="SQLite DB path")
    sub = p.add_subparsers(dest="cmd", required=True)

    sc = sub.add_parser("insight-create", help="Create a new insight")
    sc.add_argument("--title", required=True)
    sc.add_argument("--owner", required=True)
    sc.add_argument("--uri")

    sd = sub.add_parser("dep-add", help="Add dependency (insight -> insight)")
    sd.add_argument("--from", dest="from_id", required=True)
    sd.add_argument("--to", dest="to_id", required=True)

    sdd = sub.add_parser("delete", help="Safe delete workflow")
    sdd.add_argument("--id", required=True)
    sdd.add_argument("--strategy", choices=["block", "cascade"], default="block")
    sdd.add_argument("--dry-run", action="store_true")
    sdd.add_argument("--who", default="cli")

    sr = sub.add_parser("restore", help="Restore from trash by root id")
    sr.add_argument("--id", required=True)
    sr.add_argument("--who", default="cli")

    sp = sub.add_parser("purge", help="Hard delete a single insight (must be free)")
    sp.add_argument("--id", required=True)
    sp.add_argument("--who", default="cli")

    st = sub.add_parser("trash", help="List trash")
    sa = sub.add_parser("audit", help="List audit")
    sa.add_argument("--target")

    args = p.parse_args()
    store = InsightStore(args.db)

    if args.cmd == "insight-create":
        iid = store.create_insight(args.title, args.owner, args.uri)
        _print({"id": iid})
    elif args.cmd == "dep-add":
        store.add_dep_on_insight(args.from_id, args.to_id)
        _print({"ok": True})
    elif args.cmd == "delete":
        if args.dry_run:
            _print(store.dry_run_delete(args.id, args.strategy))
        else:
            _print(store.soft_delete(args.id, who=args.who, strategy=args.strategy))
    elif args.cmd == "restore":
        _print(store.restore(args.id, who=args.who))
    elif args.cmd == "purge":
        _print(store.purge(args.id, who=args.who))
    elif args.cmd == "trash":
        _print(store.list_trash())
    elif args.cmd == "audit":
        _print(store.get_audit(args.target))
    return 1

if __name__ == "__main__":  # pragma: no cover - CLI entry
    sys.exit(main())
