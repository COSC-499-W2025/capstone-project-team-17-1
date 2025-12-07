from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from .insight_store import InsightStore
from .config import load_config, reset_config
from .consent import (
    ConsentError,
    ExternalPermissionDenied,
    ensure_consent,
    ensure_external_permission,
    export_consent,
    grant_consent,
    prompt_for_consent,
    revoke_consent,
)
from .logging_utils import get_logger
from .modes import ModeResolution, resolve_mode
from .project_ranking import WEIGHTS as RANK_WEIGHTS, rank_projects_from_snapshots
from .storage import fetch_latest_snapshot, fetch_latest_snapshots, open_db, close_db
from .zip_analyzer import InvalidArchiveError, ZipAnalyzer
from .job_matching import match_job_to_project, build_resume_snippet
from .resume_retrieval import (
    build_resume_preview,
    export_resume,
    query_resume_entries,
    ensure_resume_schema,
)
from .portfolio_retrieval import ensure_indexes as ensure_portfolio_indexes
from .portfolio_retrieval import list_snapshots as list_portfolio_snapshots
from .portfolio_retrieval import get_latest_snapshot as get_portfolio_latest
from .timeline import write_projects_timeline, write_skills_timeline
from .top_project_summaries import (
    create_summary_template,
    AutoWriter,
    EvidenceItem,
    export_markdown,
    export_readme_snippet,
)

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
    conn = open_db(args.db_dir)
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

        data = export_resume(entries, fmt=args.format, destination=args.output)
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
        close_db()

def _handle_portfolio(args: argparse.Namespace) -> int:
    conn = open_db(args.db_dir)
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
        close_db()


def _handle_top_summary(args: argparse.Namespace) -> int:
    conn = open_db(args.db_dir)
    try:
        raw = fetch_latest_snapshots(conn)
        snapshots = {row["project_id"]: row["snapshot"] for row in raw if row.get("project_id") and isinstance(row.get("snapshot"), dict)}
        if not snapshots:
            print("No project analyses available for summary.")
            return 0
        rankings = rank_projects_from_snapshots(snapshots)
        target_id = args.project_id or (rankings[0].project_id if rankings else None)
        if not target_id:
            print("No project available for summary.")
            return 0
        snapshot = snapshots.get(target_id)
        if not snapshot:
            print(f"Project '{target_id}' not found in snapshots.")
            return 1
        ranking = next((r for r in rankings if r.project_id == target_id), None)
        template = create_summary_template(target_id, snapshot, ranking)
        # Keep evidence explicit to ground the summary; no LLM used.
        evidence = [
            EvidenceItem(kind="metric", reference="analysis:file_count", detail=f"{snapshot.get('file_summary', {}).get('file_count', 0)} files", source="analysis"),
            EvidenceItem(kind="collaboration", reference="collaboration:contributors", detail="contributors weighted", source="analysis"),
            EvidenceItem(kind="languages", reference="languages", detail=", ".join(snapshot.get("languages", {}).keys()), source="analysis"),
        ]
        summary = AutoWriter().compose(template, evidence, snapshot, ranking, rank_position=1, use_llm=False)
        out_dir = args.output_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        md_path = out_dir / "top_project.md"
        readme_path = out_dir / "top_project_README.md"
        md_path.write_text(export_markdown(summary), encoding="utf-8")
        readme_path.write_text(export_readme_snippet(summary), encoding="utf-8")
        pdf_path = args.pdf_output or (out_dir / "top_project.pdf")
        pdf_path.write_bytes(export_markdown(summary).encode("utf-8"))
        payload = {
            "top_project": summary.title,
            "markdown": str(md_path),
            "readme": str(readme_path),
            "pdf": str(pdf_path),
            "evidence": [e.__dict__ for e in evidence],
            "confidence": {"llm_used": False, "mode": "offline", "guardrails": "facts quoted with references in markdown/readme/pdf"},
        }
        print(json.dumps(payload, indent=2))
        return 0
    finally:
        close_db()


def _handle_projects_timeline(args: argparse.Namespace) -> int:
    rows = write_projects_timeline(args.db_dir, args.output)
    print(json.dumps({"rows": rows, "output": str(args.output)}, indent=2))
    return 0


def _handle_skills_timeline(args: argparse.Namespace) -> int:
    rows = write_skills_timeline(args.db_dir, args.output)
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
    config_state = load_config()
    if args.config_action == "show":
        payload = {
            "consent": config_state.consent.__dict__,
            "preferences": config_state.preferences.__dict__,
        }
        print(json.dumps(payload, indent=2))
        return 0
    if args.config_action == "reset":
        reset = reset_config()
        logger.info("Configuration reset to defaults")
        print("Configuration reset. Current preferences:")
        print(json.dumps(reset.preferences.__dict__, indent=2))
        return 0
    print("Unknown config action", file=sys.stderr)
    return 1


def _handle_analyze(args: argparse.Namespace) -> int:
    archive_arg = (args.archive or "").strip()
    if not archive_arg:
        payload = {"error": "InvalidInput", "detail": "Archive path must not be empty"}
        print(json.dumps(payload), file=sys.stderr)
        return 5

    archive_path = Path(archive_arg).expanduser()
    if not archive_path.exists():
        detail = f"Archive not found: {archive_path}"
        payload = {"error": "FileNotFound", "detail": detail}
        print(json.dumps(payload), file=sys.stderr)
        return 4
    if archive_path.suffix.lower() != ".zip":
        payload = {
            "error": "InvalidInput",
            "detail": "Unsupported file format. Please provide a .zip archive.",
        }
        print(json.dumps(payload), file=sys.stderr)
        return 3

    try:
        consent = ensure_consent(require_granted=True)
    except ConsentError as exc:
        privacy_message = (
            "This analysis runs locally and reads file metadata (paths, sizes, timestamps). "
            "No data leaves your machine unless you later export results."
        )
        print(privacy_message)
        decision = prompt_for_consent()
        if decision == "accepted":
            config_state = grant_consent()
            consent = config_state.consent
            logger.info("Consent granted interactively: %s", consent)
        else:
            payload = {"error": "ConsentRequired", "detail": str(exc)}
            print(json.dumps(payload), file=sys.stderr)
            return 2

    config = load_config()
    mode: ModeResolution = resolve_mode(args.analysis_mode, consent)
    if mode.resolved == "external":
        try:
            ensure_external_permission(
                "capstone.external.analysis",
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
    analyzer = ZipAnalyzer()
    try:
        summary = analyzer.analyze(
            zip_path=archive_path,
            metadata_path=args.metadata_output,
            summary_path=args.summary_output,
            mode=mode,
            preferences=config.preferences,
            project_id=args.project_id,
            db_dir=args.db_dir,
        )
    except InvalidArchiveError as exc:
        payload = getattr(exc, "payload", {"error": "InvalidInput", "detail": str(exc)})
        print(json.dumps(payload), file=sys.stderr)
        return 3

    if args.summary_to_stdout:
        print(json.dumps(summary, indent=2))
    elif not args.quiet:
        _print_human_summary(summary, args)
    return 0


def _handle_rank_projects(args: argparse.Namespace) -> int:
    conn = open_db(args.db_dir)
    try:
        raw_snapshots = fetch_latest_snapshots(conn)
        snapshot_map: dict[str, dict] = {}
        for row in raw_snapshots:
            pid = row.get("project_id")
            snap = row.get("snapshot")
            if not pid or not isinstance(snap, dict):
                continue
            snapshot_map[pid] = snap

        if not snapshot_map:
            print("No project analyses available for ranking.")
            return 0

        rankings = rank_projects_from_snapshots(snapshot_map, user=args.user)
        if args.limit is not None and args.limit >= 0:
            rankings = rankings[: args.limit]

        contributor_label = args.user or "primary contributor"
        print(f"Project rankings for {contributor_label}:")
        for index, ranking in enumerate(rankings, start=1):
            print(f"{index}. {ranking.project_id} — score {ranking.score:.4f}")
            for factor in ("artifact", "bytes", "recency", "activity", "diversity"):
                weight = RANK_WEIGHTS[factor]
                print(f"   - {factor}: weight {weight:.2f}, contribution {ranking.breakdown[factor]:.3f}")
            details = ranking.details
            # Expose raw metrics so users understand how each factor influenced the score.
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
        close_db()


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
    if args.command == "clean":
        return _handle_clean(args)
    if args.command == "rank-projects":
        return _handle_rank_projects(args)
    if args.command == "job-match":
        return _handle_job_match(args)
    if args.command == "resume":
        return _handle_resume(args)
    if args.command == "portfolio":
        return _handle_portfolio(args)
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
