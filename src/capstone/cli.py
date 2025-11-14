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
from .storage import fetch_latest_snapshots, open_db, close_db
from .zip_analyzer import InvalidArchiveError, ZipAnalyzer

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
    consent_sub = consent_parser.add_subparsers(dest="consent_action", required=True)

    grant_parser = consent_sub.add_parser(
        "grant", help="Grant consent for local/external processing"
    )
    grant_parser.add_argument(
        "--decision",
        choices=["allow", "allow_once", "allow_always"],
        default="allow",
        help="Consent decision to record",
    )

    revoke_parser = consent_sub.add_parser("revoke", help="Revoke consent")
    revoke_parser.add_argument(
        "--decision",
        choices=["deny", "deny_once", "deny_always"],
        default="deny",
        help="Revocation detail",
    )
    consent_sub.add_parser("status", help="Show current consent state")

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
    "--all", action="store_true", help="Also remove ./out if it exists"
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

    return parser


# ----------------------------- Handlers --------------------------------
def _handle_consent(args: argparse.Namespace) -> int:
    if args.consent_action == "grant":
        config = grant_consent(decision=args.decision)
        logger.info("Consent granted: %s", config.consent)
        print("Consent granted.")
        return 0
    if args.consent_action == "revoke":
        config = revoke_consent(decision=args.decision)
        logger.info("Consent revoked: %s", config.consent)
        print("Consent revoked.")
        return 0
    if args.consent_action == "status":
        state = export_consent()
        print(json.dumps(state, indent=2))
        return 0
    print("Unknown consent action", file=sys.stderr)
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
    if not archive_path.exists() or not archive_path.is_file():
        detail = f"Archive not found: {archive_path}"
        payload = {"error": "FileNotFound", "detail": detail}
        print(json.dumps(payload), file=sys.stderr)
        return 4

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
        snapshots = fetch_latest_snapshots(conn)
        if not snapshots:
            print("No project analyses available for ranking.")
            return 0

        rankings = rank_projects_from_snapshots(snapshots, user=args.user)
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
    print(summary["local_mode_label"], f"({summary['resolved_mode']})")
    print(f"Metadata written to: {summary['metadata_output']}")
    print(f"Summary written to: {args.summary_output}")
    file_summary = summary.get("file_summary", {})
    if file_summary:
        print(
            f"Processed {file_summary.get('file_count', 0)} files totaling {file_summary.get('total_bytes', 0)} bytes"
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
    if args.command == "config":
        return _handle_config(args)
    if args.command == "analyze":
        return _handle_analyze(args)
    if args.command == "clean":
        return _handle_clean(args)
    if args.command == "rank-projects":
        return _handle_rank_projects(args)

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
