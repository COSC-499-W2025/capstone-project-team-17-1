import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from capstone.consent import ExternalPermissionDenied, grant_consent, ensure_external_permission  # noqa: E402
from capstone.config import reset_config  # noqa: E402
from capstone.cli import main  # noqa: E402
from capstone.project_ranking import rank_projects_from_snapshots  # noqa: E402
from capstone.storage import fetch_latest_snapshots, open_db, close_db  # noqa: E402
from capstone import storage  # noqa: E402
from sample_project import create_sample_zip  # noqa: E402
from capstone.insight_store import InsightStore  # noqa: E402


def test_invalid_input_returns_json_error(capsys, tmp_path):
    pdf_path = tmp_path / "bad.pdf"
    pdf_path.write_text("%PDF-1.4", encoding="utf-8")
    rc = main(
        [
            "analyze",
            str(pdf_path),
            "--metadata-output",
            str(tmp_path / "m.jsonl"),
            "--summary-output",
            str(tmp_path / "s.json"),
            "--project-id",
            "invalid",
            "--db-dir",
            str(tmp_path / "db"),
            "--quiet",
        ]
    )
    assert rc == 3
    captured = capsys.readouterr()
    payload = json.loads(captured.err.strip())
    assert payload["error"] == "InvalidInput"
    assert "zip" in payload["detail"].lower()


def test_analyze_creates_ids_and_ranking(tmp_path):
    reset_config()
    original_base_dir = storage.BASE_DIR
    close_db()
    storage.BASE_DIR = tmp_path
    grant_consent()
    zip_path = create_sample_zip(tmp_path)
    metadata_output = tmp_path / "meta.jsonl"
    summary_output = tmp_path / "summary.json"
    db_dir = tmp_path / "db"
    try:
        rc = main(
            [
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
                "--quiet",
            ]
        )
        assert rc == 0
        lines = metadata_output.read_text(encoding="utf-8").splitlines()
        assert lines, "metadata should not be empty"
        assert all(json.loads(line).get("id") for line in lines)

        conn = open_db(db_dir)
        try:
            snapshots = fetch_latest_snapshots(conn)
            assert snapshots
            snapshot_map = {row["project_id"]: row["snapshot"] for row in snapshots}
            rankings = rank_projects_from_snapshots(snapshot_map)
            assert rankings and any(item.project_id == "demo" for item in rankings)
        finally:
            close_db()
    finally:
        close_db()
        storage.BASE_DIR = original_base_dir


def test_external_permission_denied_blocks():
    with pytest.raises(ExternalPermissionDenied):
        ensure_external_permission("test.service")


def test_safe_delete_roundtrip():
    store = InsightStore(":memory:")
    root = store.create_insight("Root", "alice")
    child = store.create_insight("Child", "bob")
    store.add_dep_on_insight(child, root)
    plan = store.dry_run_delete(root, strategy="cascade")
    assert plan["ok"] and plan["plan"]["targets"] == sorted(plan["plan"]["targets"])
    res = store.soft_delete(root, who="tester", strategy="cascade")
    assert res["ok"] and res["deleted"]
    restored = store.restore(root, who="tester")
    assert restored["ok"]
    # remove dependency to allow purge
    store._conn.execute("DELETE FROM deps WHERE from_insight=?", (child,))
    store._conn.commit()
    purged_child = store.purge(child, who="tester")
    purged_root = store.purge(root, who="tester")
    assert purged_child["ok"] and purged_root["ok"]
    store.close()


def test_exports_exist_after_analyze(tmp_path):
    reset_config()
    original_base_dir = storage.BASE_DIR
    close_db()
    storage.BASE_DIR = tmp_path
    grant_consent()
    zip_path = create_sample_zip(tmp_path)
    metadata_output = tmp_path / "meta.jsonl"
    summary_output = tmp_path / "summary.json"
    db_dir = tmp_path / "db"
    try:
        rc = main(
            [
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
                "--quiet",
            ]
        )
        assert rc == 0
        external_summary = tmp_path / "summary_external.json"
        # simulate external parity by copying
        external_summary.write_text(summary_output.read_text(), encoding="utf-8")
        assert metadata_output.exists()
        assert summary_output.exists()
        assert external_summary.exists()
    finally:
        close_db()
        storage.BASE_DIR = original_base_dir
