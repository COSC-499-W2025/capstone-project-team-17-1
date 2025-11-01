"""Command-line entrypoint for the capstone analyzer."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import load_config, reset_config
from .consent import (
    ConsentError,
    ensure_consent,
    ensure_external_permission,
    export_consent,
    grant_consent,
    prompt_for_consent,
    revoke_consent,
)
from .logging_utils import get_logger
from .modes import ModeResolution, resolve_mode
from .zip_analyzer import InvalidArchiveError, ZipAnalyzer


logger = get_logger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Capstone zip analyzer (Python implementation).")
    subparsers = parser.add_subparsers(dest="command", required=True)

    consent_parser = subparsers.add_parser("consent", help="Manage user consent")
    consent_sub = consent_parser.add_subparsers(dest="consent_action", required=True)

    grant_parser = consent_sub.add_parser("grant", help="Grant consent for local/external processing")
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

    config_parser = subparsers.add_parser("config", help="Manage configuration")
    config_sub = config_parser.add_subparsers(dest="config_action", required=True)
    config_sub.add_parser("show", help="Display current configuration (decrypted in-memory)")
    config_sub.add_parser("reset", help="Reset configuration to defaults")

    analyze_parser = subparsers.add_parser("analyze", help="Scan a zip archive for metadata")
    analyze_parser.add_argument("archive", type=str, help="Path to the .zip archive to analyze")
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
        default="auto",
        help="Requested analysis mode",
    )
    analyze_parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress terminal output and only write files",
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

    return parser


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
            payload = {
                "error": "ConsentRequired",
                "detail": str(exc),
            }
            print(json.dumps(payload), file=sys.stderr)
            return 2

    config = load_config()
    mode: ModeResolution = resolve_mode(args.analysis_mode, consent)
    if mode.resolved == "external":
        ensure_external_permission(
            "capstone.external.analysis",
            data_types=["artifact metadata", "language statistics", "collaboration summaries"],
            purpose="Generate remote analytics for the selected archive",
            destination="Configured external analysis provider",
            privacy="No source code is transmitted; only derived metadata is shared.",
            source="cli",
        )
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
        print(
            "Collaboration classification:",
            collaboration.get("classification", "unknown"),
        )
    print(f"Scan duration: {summary.get('scan_duration_seconds', 0)} seconds")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "consent":
        return _handle_consent(args)
    if args.command == "config":
        return _handle_config(args)
    if args.command == "analyze":
        return _handle_analyze(args)

    parser.print_help()
    return 1


if __name__ == "__main__":  # pragma: no cover - CLI entry
    sys.exit(main())
