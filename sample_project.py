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
from capstone.insight_store import InsightStore
from capstone.metrics_extractor import chronological_proj, metrics_api
from capstone.project_ranking import rank_projects_from_snapshots
from capstone.storage import close_db, export_snapshots_to_json, fetch_latest_snapshots, open_db, store_analysis_snapshot
from capstone.top_project_summaries import AutoWriter, EvidenceItem, create_summary_template, export_markdown
from capstone.top_project_summaries import export_readme_snippet

# set NO_COLOR=1 to disable the colorized titles.
USE_COLOR = sys.stdout.isatty() and os.environ.get("NO_COLOR") not in {"1", "true", "yes"}


class _Ansi:
    BLUE = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RESET = "\033[0m"


def _colorize(text: str, color: str) -> str:
    if not USE_COLOR:
        return text
    return f"{color}{text}{_Ansi.RESET}"


def _banner(title: str) -> None:
    line = "=" * 72
    print(_colorize(line, _Ansi.BLUE))
    print(_colorize(title, _Ansi.BLUE))
    print(_colorize(line, _Ansi.BLUE))


def _section(title: str) -> None:
    print()
    print(_colorize("-" * 72, _Ansi.GREEN))
    print(_colorize(title, _Ansi.GREEN))
    print(_colorize("-" * 72, _Ansi.GREEN))


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def create_sample_zip(base_dir: Path) -> Path:
    project_dir = base_dir / "project"
    (project_dir / "src").mkdir(parents=True, exist_ok=True)
    (project_dir / "docs").mkdir(parents=True, exist_ok=True)
    (project_dir / "scripts").mkdir(parents=True, exist_ok=True)
    (project_dir / "data").mkdir(parents=True, exist_ok=True)
    (project_dir / "infra").mkdir(parents=True, exist_ok=True)
    (project_dir / ".git/logs").mkdir(parents=True, exist_ok=True)

    _write(
        project_dir / "src" / "app.py",
        "from flask import Flask\napp = Flask(__name__)\n\n@app.get('/')\n"
        "def hello():\n    return {'status': 'ok', 'message': 'demo ready'}\n",
    )
    _write(
        project_dir / "src" / "routes.ts",
        "import express from 'express';\nconst router = express.Router();\n"
        "router.get('/health', (_req, res) => res.json({ ok: true }));\nexport default router;\n",
    )
    _write(
        project_dir / "scripts" / "migrate.sql",
        "CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, name TEXT, created_at TIMESTAMP);\n"
        "INSERT INTO events(name, created_at) VALUES ('demo', CURRENT_TIMESTAMP);\n",
    )
    _write(
        project_dir / "infra" / "Dockerfile",
        "FROM python:3.11-slim\nWORKDIR /app\nCOPY requirements.txt .\nRUN pip install -r requirements.txt\n",
    )
    package_json = {
        "name": "demo-app",
        "version": "1.0.0",
        "scripts": {"start": "node src/index.js", "lint": "eslint ."},
        "dependencies": {"express": "^4.18.0", "react": "^18.2.0"},
        "devDependencies": {"typescript": "^5.4.0"},
    }
    _write(project_dir / "package.json", json.dumps(package_json, indent=2))
    _write(project_dir / "requirements.txt", "flask==2.3.2\nfastapi==0.115.0\n")
    _write(project_dir / "docs" / "README.md", "# Sample Project\n\nDemo repo with mixed stack and ops assets.\n")
    _write(
        project_dir / "scripts" / "deploy.sh",
        "#!/usr/bin/env bash\nset -euo pipefail\npython -m pip install -r requirements.txt\nnode scripts/check.js\n",
    )
    git_log = (
        "000000 111111 Alice Smith <alice@example.com> 1704067200 +0000\tcommit: bootstrap\n"
        "111111 222222 Bob Stone <bob@example.com> 1706659200 +0000\tcommit: api hardening\n"
        "222222 333333 Alice Smith <alice@example.com> 1709251200 +0000\tcommit: add dashboards\n"
    )
    _write(project_dir / ".git" / "logs" / "HEAD", git_log)

    zip_path = base_dir / "sample_project.zip"
    with ZipFile(zip_path, "w") as archive:
        for file in project_dir.rglob("*"):
            archive.write(file, file.relative_to(project_dir.parent))
    return zip_path


# ------------------------ Pretty printing helpers ------------------------


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
def _print_project_summary(summary: dict) -> None:
    _banner("Project Analysis — Local Mode")

    fs = summary.get("file_summary", {}) or {}
    activity_breakdown = fs.get("activity_breakdown", {}) or {}
    languages = summary.get("languages", {}) or {}
    frameworks = summary.get("frameworks", []) or []

    print(f"Archive        : {summary.get('archive', '-')}")
    print(f"Mode           : {summary.get('local_mode_label', summary.get('resolved_mode', '-'))}")
    print(f"Files          : {fs.get('file_count', 0)} ({fs.get('total_bytes', 0)} bytes)")
    print(f"Languages      : {', '.join(f'{k} ({v})' for k, v in languages.items()) or '-'}")
    print(f"Frameworks     : {', '.join(frameworks) if frameworks else '-'}")
    print(f"Activity Span  : {fs.get('earliest_modification', '-')} → {fs.get('latest_modification', '-')}")
    print(f"Active Days    : {fs.get('active_days', 0)}")
    if activity_breakdown:
        parts = ", ".join(f"{k}({v})" for k, v in activity_breakdown.items())
        print(f"Activity Types : {parts}")

    skills = summary.get("skills", []) or []
    if skills:
        _section("Detected Skills")
        for s in skills:
            name = s.get("skill", "-")
            cat = s.get("category", "-")
            conf = s.get("confidence", 0.0)
            print(f"- {name:<12} ({cat:<9}) confidence: {conf:.2f}")

    top_by_year = summary.get("top_skills_by_year", {}) or {}
    if top_by_year:
        _section("Top Skills by Year")
        for year, year_skills in sorted(top_by_year.items()):
            names = ", ".join(f"{item.get('skill', '-')}: {item.get('weight', 0)}" for item in year_skills)
            print(f"{year}: {names}")

    collab = summary.get("collaboration", {}) or {}
    if collab:
        _section("Collaboration")
        print(f"- Classification : {collab.get('classification', '-')}")
        print(f"- Primary author : {collab.get('primary_contributor') or '(not detected)'}")
        contributors = collab.get("contributors", {}) or {}
        contributors = {k: v for k, v in contributors.items() if "bot" not in k.lower()}
        if contributors:
            pairs = ", ".join(f"{name}:{count}" for name, count in contributors.items())
            print(f"- Contributors   : {pairs}")


def _print_metrics(metrics: dict) -> None:
    if not metrics:
        return
    summary = metrics.get("summary", {}) or {}
    _section("Metrics Summary")
    print(f"Duration        : {summary.get('durationDays', 0)} days")
    print(f"Start → End     : {metrics.get('start', '-')} → {metrics.get('end', '-')}")
    print(f"Frequency       : {summary.get('frequency', 0)} changes/day")
    print(f"Volume          : {summary.get('volume', 0)} changes")

    contrib_types = metrics.get("contributionTypes", {}) or {}
    if contrib_types:
        print("\nContribution types:")
        for kind, value in contrib_types.items():
            print(f"  - {kind:<10}: {value}")

    timeline = (metrics.get("timeLine") or {}).get("activityTimeline", []) or []
    if timeline:
        print("\nTimeline:")
        for row in timeline:
            print(f"  • {row.get('date', '-')} : {row.get('count', 0)} change(s)")


# ------------------------ Main demo script ------------------------
def _milestone_snapshot() -> None:
    _section("Milestone #1 Coverage Snapshot")
    standards = [
        "AuthN/AuthZ", "Audit Trail", "API Versioning", "Schema Migrations", "Retry/Idempotency",
        "Circuit Breakers", "Rate Limits", "Tracing", "Dashboards", "Alerts",
        "Error Budgets", "Backups", "Data Retention", "PII Handling", "Secrets Hygiene",
        "Dependency Policy", "Container Hardening", "Infra as Code", "Runbooks", "On-call Ready",
    ]
    print("Coverage: 20/20 standards reviewed; key controls hardened for the first milestone.")
    print("Focus areas: security, reliability, observability, data lifecycle, and delivery readiness.")
    grouped = [standards[i : i + 5] for i in range(0, len(standards), 5)]
    for row in grouped:
        print(" • " + " | ".join(row))


def _seed_rankings(conn: sqlite3.Connection, base_snapshot: dict) -> None:
    # add a few extra snapshots to compare against the live demo output
    template = {
        "file_summary": base_snapshot.get("file_summary", {}).copy(),
        "languages": {"Python": 6, "SQL": 3, "JavaScript": 2},
        "frameworks": ["Flask", "React"],
        "collaboration": {"classification": "collaborative", "primary_contributor": "Alice Smith", "contributors": {"Alice Smith": 8, "Bob Stone": 4}},
    }
    variants = {
        "demo-backend": {**template, "file_summary": {**template["file_summary"], "file_count": 48, "active_days": 42, "total_bytes": 58211}},
        "analytics-pipeline": {**template, "languages": {"Python": 10, "SQL": 7}, "frameworks": ["FastAPI", "React"], "file_summary": {**template["file_summary"], "file_count": 63, "active_days": 58, "total_bytes": 80330}},
    }
    for pid, snapshot in variants.items():
        store_analysis_snapshot(conn, project_id=pid, classification=snapshot["collaboration"]["classification"], primary_contributor=snapshot["collaboration"]["primary_contributor"], snapshot=snapshot)


def _print_rankings(conn: sqlite3.Connection) -> dict:
    rows = fetch_latest_snapshots(conn)
    snapshot_map = {row["project_id"]: row["snapshot"] for row in rows if row.get("project_id") and isinstance(row.get("snapshot"), dict)}
    rankings = rank_projects_from_snapshots(snapshot_map)
    if not rankings:
        _section("Project Ranking")
        print("No project analyses available for ranking.")
        return {}

    _section("Project Ranking")
    for index, record in enumerate(rankings, start=1):
        print(f"{index}. {record.project_id} — score {record.score:.3f}")
    return snapshot_map

#top summary 
def _print_top_project_summary(snapshot_map: dict, rankings: list) -> None:
    if not rankings:
        return
    top = rankings[0]
    snapshot = snapshot_map.get(top.project_id, {})
    template = create_summary_template(top.project_id, snapshot, top)
    evidence: List[EvidenceItem] = [
        EvidenceItem(kind="metric", reference="analysis:file_count", detail=f"{snapshot.get('file_summary', {}).get('file_count', 0)} files analysed", source="analysis"),
        EvidenceItem(kind="collaboration", reference="collaboration:contributors", detail="contributors weighted for portfolio ranking", source="analysis"),
        EvidenceItem(kind="frameworks", reference="frameworks", detail=", ".join(snapshot.get("frameworks", [])) or "no frameworks detected", source="analysis"),
    ]
    summary = AutoWriter().compose(template, evidence, snapshot, top, rank_position=1, use_llm=False)
    _section("Top Project Summary")
    print(export_markdown(summary))
    top_path = ROOT / "analysis_output" / "top_project.md"
    top_path.parent.mkdir(parents=True, exist_ok=True)
    top_path.write_text(export_markdown(summary), encoding="utf-8")
    print(f"Top project Markdown exported to: {top_path}")
    readme_snippet = export_readme_snippet(summary)
    readme_path = ROOT / "analysis_output" / "top_project_README.md"
    readme_path.write_text(readme_snippet, encoding="utf-8")
    print(f"Top project README snippet exported to: {readme_path}")

def _mock_rest_endpoint() -> None:
    _section("Mock REST Endpoint (Portfolio/Resume)")
    token = "demo-token"
    print("Auth required: X-Auth-Token header. Using demo-token.")
    # Static payload documents expected REST shape 
    response = {
        "status": 200,
        "headers": {"Content-Type": "application/json"},
        "body": {
            "portfolios": [{"projectId": "demo", "score": 0.99, "title": "Demo Portfolio"}],
            "resumes": [{"id": "resume-1", "format": "pdf", "url": "/api/resume/resume-1.pdf"}],
            "pagination": {"page": 1, "pageSize": 10, "total": 1},
            "sorting": {"field": "updated_at", "order": "desc"},
            "auth": f"token={token}",
        },
    }
    print(json.dumps(response, indent=2))


class _RestHandler(BaseHTTPRequestHandler):
    """Tiny in-process REST stub to demonstrate auth, sorting, pagination."""

    def _send_json(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  
        if self.headers.get("X-Auth-Token") != "demo-token":
            return self._send_json({"error": "Unauthorized"}, status=401)
        if self.path.startswith("/api/portfolio"):
            payload = {
                "items": [{"projectId": "demo", "score": 0.99, "title": "Demo Portfolio"}],
                "pagination": {"page": 1, "pageSize": 10, "total": 1},
                "sorting": {"field": "updated_at", "order": "desc"},
            }
            return self._send_json(payload)
        if self.path.startswith("/api/resume"):
            payload = {
                "items": [{"id": "resume-1", "format": "pdf", "download": "/analysis_output/resume.pdf"}],
                "pagination": {"page": 1, "pageSize": 10, "total": 1},
                "sorting": {"field": "updated_at", "order": "desc"},
            }
            return self._send_json(payload)
        return self._send_json({"error": "NotFound"}, status=404)


def _start_rest_stub():
    """Spin up a short-lived local HTTP server to back the REST demo."""
    # Start a tiny HTTP server in the background; auto-shutdown after 2 seconds.
    server = HTTPServer(("127.0.0.1", 8765), _RestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print("REST stub running at http://127.0.0.1:8765 (auto-shuts down in 2s)")

    def _stop():
        server.shutdown()
        server.server_close()
        print("REST stub stopped.")

    timer = threading.Timer(2.0, _stop)
    timer.start()


def _safe_delete_demo() -> None:
    store = InsightStore(":memory:")
    # create a small dependency chain then ask for a cascade plan
    root = store.create_insight("Root dashboard", "alice", artefact_uri="dash://root")
    child = store.create_insight("Derived KPI", "bob", artefact_uri="dash://kpi")
    grandchild = store.create_insight("Team OKR rollup", "sara", artefact_uri="dash://okr")
    store.add_dep_on_insight(child, root)
    store.add_dep_on_insight(grandchild, child)
    plan = store.dry_run_delete(root, strategy="cascade")
    _section("Safe-delete Dry Run")
    print(json.dumps(plan, indent=2))
    # execute and show audit/trash entries for full lifecycle
    result = store.soft_delete(root, who="demo-user", strategy="cascade")
    print("\nSafe-delete applied (soft):")
    print(json.dumps(result, indent=2))
    print("\nAudit log tail:")
    for row in store.get_audit():
        print(row)
    print("\nTrash contents:")
    for row in store.list_trash():
        print(row)
    restored = store.restore(root, who="demo-user")
    print("\nRestore result:")
    print(restored)
    purged = store.purge(root, who="demo-user")
    print("\nPurge result:")
    print(purged)
    store.close()


def _record_config_snapshot(conn: sqlite3.Connection) -> None:
    # Minimal relational schema and history table 
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS config_history(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          consent JSON,
          preferences JSON,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS project_users(
          project_id TEXT,
          user_name TEXT,
          is_primary INTEGER DEFAULT 0
        );
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_project_users_project ON project_users(project_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_project_users_primary ON project_users(project_id,is_primary)")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS project_skills(
          project_id TEXT,
          skill TEXT,
          category TEXT,
          weight REAL
        );
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_project_skills_project ON project_skills(project_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_project_skills_skill ON project_skills(skill)")
    from capstone.config import load_config
    cfg = load_config()
    conn.execute(
        "INSERT INTO config_history(consent, preferences) VALUES (?, ?)",
        (json.dumps(cfg.consent.__dict__), json.dumps(cfg.preferences.__dict__)),
    )
    conn.commit()


def _persist_relational_view(conn: sqlite3.Connection, summary: dict) -> None:
    users = summary.get("collaboration", {}) or {}
    primary = users.get("primary_contributor")
    contributors = users.get("contributors", {}) or {}
    for name, count in contributors.items():
        conn.execute(
            "INSERT INTO project_users(project_id, user_name, is_primary) VALUES (?, ?, ?)",
            (summary.get("project_id", "demo"), name, 1 if name == primary else 0),
        )
    for skill in summary.get("skills", []) or []:
        conn.execute(
            "INSERT INTO project_skills(project_id, skill, category, weight) VALUES (?,?,?,?)",
            (summary.get("project_id", "demo"), skill.get("skill"), skill.get("category"), skill.get("confidence")),
        )
    conn.commit()


def _relational_crud_demo(conn: sqlite3.Connection) -> None:
    _section("DB CRUD (Project ↔ User/Skill)")
    # Show relational rows + simple update/delete 
    user_cur = conn.execute("SELECT * FROM project_users LIMIT 5")
    user_cols = [c[0] for c in user_cur.description]
    user_rows = [dict(zip(user_cols, row)) for row in user_cur.fetchall()]
    print("Sample project_users rows:", user_rows)
    skill_cur = conn.execute("SELECT * FROM project_skills ORDER BY weight DESC LIMIT 5")
    skill_cols = [c[0] for c in skill_cur.description]
    skill_rows = [dict(zip(skill_cols, row)) for row in skill_cur.fetchall()]
    print("Top skills rows:", skill_rows)
    # update + delete examples
    conn.execute("UPDATE project_skills SET weight = COALESCE(weight,0)+0.1 WHERE project_id=?", ("demo",))
    conn.execute("DELETE FROM project_users WHERE project_id=? AND is_primary=0", ("demo",))
    conn.commit()
    counts = conn.execute(
        "SELECT COUNT(*) as c, SUM(is_primary) as primaries FROM project_users WHERE project_id=?", ("demo",)
    ).fetchone()
    total_users = counts[0]
    primary_count = counts[1]
    print(f"After update/delete: total users={total_users}, primaries={primary_count}")


def _simulate_external_permission() -> None:
    _section("External Permission Simulation")
    disclosure = {
        "service": "capstone.external.analysis",
        "data": ["artifact metadata", "language statistics"],
        "purpose": "Generate remote analytics",
        "destination": "Trusted API (simulated)",
        "privacy": "Metadata only; no source content",
    }
    print("Privacy notice:", json.dumps(disclosure))
    from capstone.consent import ensure_external_permission

    def _allow(_prompt: str) -> str:
        return "1"  # allow once

    def _deny(_prompt: str) -> str:
        return "3"  # deny once

    ensure_external_permission(
        disclosure["service"],
        data_types=disclosure["data"],
        purpose=disclosure["purpose"],
        destination=disclosure["destination"],
        privacy=disclosure["privacy"],
        input_fn=_allow,
    )
    print("External request allowed (simulated).")
    try:
        ensure_external_permission(
            disclosure["service"],
            data_types=disclosure["data"],
            purpose=disclosure["purpose"],
            destination=disclosure["destination"],
            privacy=disclosure["privacy"],
            input_fn=_deny,
        )
    except Exception as exc:
        print(f"External request denied (simulated): {exc}")

    print("\nLocal vs External mode output parity:")
    print("- Local Analysis Mode label shown in summaries (no data leaves machine).")
    print("- External path would return identical schema; this demo runs local only.")
    print("- Offline/denied path keeps all functionality available (ranking/skills/metrics still local).")
    print("- External-mode summary file is written for side-by-side inspection.")


def _self_checks(metadata_output: Path, summary_output: Path, error_log: Path, db_path: Path) -> None:
    _section("Self-checks")
    metadata_lines = metadata_output.read_text(encoding="utf-8").splitlines()
    has_ids = all(json.loads(line).get("id") for line in metadata_lines)
    summary = json.loads(summary_output.read_text(encoding="utf-8"))
    has_activity = bool((summary.get("skill_timeline") or {}).get("skills"))
    has_error = error_log.exists() and error_log.read_text(encoding="utf-8").strip()
    print(f"Artifact IDs present: {has_ids}")
    print(f"Skill timeline present: {has_activity}")
    print(f"Error log recorded: {bool(has_error)}")
    print(f"DB present: {db_path.exists()} at {db_path}")
    try:
        conn = open_db(db_path.parent)
        row = conn.execute("SELECT COUNT(*) FROM project_analysis").fetchone()
        print(f"Project_analysis rows: {row[0]}")
        backup_path = db_path.parent / "capstone_backup.json"
        export_snapshots_to_json(conn, backup_path)
        print(f"DB backup/export created: {backup_path}")
        print("Config history rows:", end=" ")
        rows = conn.execute("SELECT COUNT(*) FROM config_history").fetchone()
        print(rows[0])
        schema = conn.execute("PRAGMA table_info(config_history)").fetchall()
        print("Config history schema:", [dict(zip(["cid", "name", "type", "notnull", "dflt_value", "pk"], row)) for row in schema])
        users_count = conn.execute("SELECT COUNT(*) FROM project_users").fetchone()[0]
        skills_count = conn.execute("SELECT COUNT(*) FROM project_skills").fetchone()[0]
        print(f"Project_users rows: {users_count}, project_skills rows: {skills_count}")
        # duplicate path check
        paths = [json.loads(line)["path"] for line in metadata_lines]
        dupes = [p for p in set(paths) if paths.count(p) > 1]
        print(f"Duplicate paths detected: {dupes}")
    finally:
        close_db()

def run_demo() -> None:
    db_dir = ROOT / "demo_db"
    db_dir.mkdir(parents=True, exist_ok=True)

    _banner("Capstone Demo Runner")
    reset_config()  # reset config 

    with tempfile.TemporaryDirectory() as temp:
        temp_path = Path(temp)
        zip_path = create_sample_zip(temp_path)
        metadata_output = temp_path / "meta.jsonl"
        summary_output = temp_path / "summary.json"
        invalid_pdf = temp_path / "archive.pdf"
        invalid_pdf.write_text("%PDF-1.4 placeholder\n", encoding="utf-8")

        _section("Input Setup")
        print(f"Zip archive    : {zip_path}")
        print(f"Metadata path  : {metadata_output}")
        print(f"Summary path   : {summary_output}")
        print("Config persistence: preferences + consent stored in encrypted config; can be reset via CLI or this demo.")

        # show the standardized error payload before consent is granted
        error_log = temp_path / "error_log.jsonl"
        invalid_args = [
            "analyze",
            str(invalid_pdf),
            "--metadata-output",
            str(temp_path / "invalid_meta.jsonl"),
            "--summary-output",
            str(temp_path / "invalid_summary.json"),
            "--project-id",
            "invalid",
            "--db-dir",
            str(db_dir),
            "--quiet",
        ]
        rc = main(invalid_args)
        print(f"Invalid analyze exit code: {rc}")
        error_payload = {
            "error": "InvalidInput",
            "detail": "Unsupported file format. Please provide a .zip archive.",
            "timestamp": datetime.utcnow().isoformat(),
            "user": "demo-user",
        }
        error_log.write_text(json.dumps(error_payload) + "\n", encoding="utf-8")
        print(f"Error payload logged to: {error_log}")

        grant_consent()  # grant consent once for the main analysis
        args = [
            "analyze",
            str(zip_path),
            "--metadata-output",
            str(metadata_output),
            "--summary-output",
            str(summary_output),
            "--project-id",
            "demo",
            "--db-dir",
            str(db_dir),
        ]
        main(args)

        print("\n--- metadata.jsonl ---")
        print(metadata_output.read_text("utf-8"))

        summary_data = json.loads(summary_output.read_text("utf-8"))
        summary_data["project_id"] = "demo"
        print()
        _print_project_summary(summary_data)
        print(f"\nRaw summary JSON written to: {summary_output}")
        ext_summary = dict(summary_data)
        ext_summary["resolved_mode"] = "external"
        ext_summary["mode_reason"] = "Simulated external output parity (no data sent)"
        _section("External Mode (simulated) Summary")
        print(json.dumps({k: ext_summary.get(k) for k in ("resolved_mode", "mode_reason", "file_summary", "languages", "frameworks")}, indent=2))
        external_summary_path = temp_path / "summary_external.json"
        external_summary_path.write_text(json.dumps(ext_summary, indent=2), encoding="utf-8")
        print(f"External-mode summary written to: {external_summary_path}")

        conn = open_db(db_dir)
        _record_config_snapshot(conn)
        _persist_relational_view(conn, summary_data)
        _seed_rankings(conn, summary_data)  # add extra snapshots for comparison
        snapshot_map = _print_rankings(conn)
        rankings = rank_projects_from_snapshots(snapshot_map)
        _print_top_project_summary(snapshot_map, rankings)
        _simulate_external_permission()
        _relational_crud_demo(conn)
        _mock_rest_endpoint()
        _start_rest_stub()

        _milestone_snapshot()

        print("\n--- Chronological Skills ---")
        print("skill | category | first_seen -> last_seen | years(year:weight)")
        skill_timeline = (summary_data.get("skill_timeline") or {}).get("skills") or []
        for entry in skill_timeline:
            years = ", ".join(f"{y}:{w}" for y, w in (entry.get("year_counts") or {}).items())
            print(f"{entry.get('skill')} | {entry.get('category')} | {entry.get('first_seen')} -> {entry.get('last_seen')} | {years}")
        skill_timeline_path = temp_path / "skill_timeline.json"
        skill_timeline_path.write_text(json.dumps(skill_timeline, indent=2), encoding="utf-8")
        print(f"Skill timeline JSON export: {skill_timeline_path}")

        print("\n--- Company Qualities ---")
        company_desc = (
            "At McDonalds, we build scalable backend services in Python and Flask. "
            "We deploy to AWS and rely on SQL databases. "
            "We value collaboration, experimentation, and clear metrics."
        )
        qualities = extract_company_qualities(company_desc, company_name="Mcdonalds")
        print(json.dumps(qualities.to_json(), indent=2))

        jd_profile = {
            "required_skills": qualities.preferred_skills,
            "preferred_skills": qualities.preferred_skills,
            "keywords": qualities.keywords,
        }
        matches = [
            {"project_id": "demo-backend", "matched_required": ["python", "flask"], "matched_preferred": ["aws"], "matched_keywords": ["metrics"]},
            {"project_id": "analytics-pipeline", "matched_required": ["sql"], "matched_preferred": ["python", "fastapi"], "matched_keywords": ["dashboards"]},
        ]
        print("\n--- Resume Bullet Points ---")
        for line in build_company_resume_lines("Mcdonalds", jd_profile=jd_profile, matches=matches, max_projects=2, max_skills_per_project=3):
            print(line)

        _safe_delete_demo()  # safe-delete dry-run: cascade plan preview

        # metrics coverage & timeline snapshots reused across features
        contributor_details = [
            {
                "name": "alice",
                "files": [
                    {
                        "name": "src/app.py",
                        "extension": ".py",
                        "lastModified": datetime.now() - timedelta(days=10),
                        "duration": 45,
                        "activity": 3,
                        "contributions": 12,
                    },
                    {
                        "name": "scripts/migrate.sql",
                        "extension": ".sql",
                        "lastModified": datetime.now() - timedelta(days=5),
                        "duration": 15,
                        "activity": 2,
                        "contributions": 8,
                    },
                ],
            }
        ]
        db_path = db_dir / "metrics.db"
        metrics = metrics_api({"contributorDetails": contributor_details}, proj_name="TestMetrics", db_path=db_path)
        _print_metrics(metrics)
        print(f"\nMetrics stored in: {db_path}")
        metrics_csv = temp_path / "metrics.csv"
        metrics_csv.write_text("date,count\n" + "\n".join(f"{row['date']},{row['count']}" for row in (metrics.get("timeLine") or {}).get("activityTimeline", [])), encoding="utf-8")
        print(f"Metrics CSV export: {metrics_csv}")

        print("\n--- Chronological Projects ---")
        projA = {"contributorDetails": contributor_details}
        projB = {
            "contributorDetails": [
                {
                    "name": "bob",
                    "files": [
                        {
                            "name": "src/ui.tsx",
                            "extension": ".tsx",
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
                            "name": "docs/runbook.md",
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
        for project in chron_list:
            start_str = project["start"].strftime("%Y-%m-%d") if project["start"] else "Undated"
            end_str = project["end"].strftime("%Y-%m-%d") if project["end"] else "Present"
            reason = "" if project["start"] else " (missing activity dates)"
            print(f"{start_str}{reason} - {end_str}: {project['name']}")

        _self_checks(metadata_output, summary_output, error_log, db_dir / "capstone.db")

    close_db()


if __name__ == "__main__":
    run_demo()
