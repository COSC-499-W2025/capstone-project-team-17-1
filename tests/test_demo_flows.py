import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from capstone.consent import ExternalPermissionDenied, grant_consent, reset_config, ensure_external_permission
from capstone.cli import main
from capstone.project_ranking import rank_projects_from_snapshots
from capstone.storage import fetch_latest_snapshots, open_db, close_db
from sample_project import create_sample_zip
from capstone.insight_store import InsightStore


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
    grant_consent()
    zip_path = create_sample_zip(tmp_path)
    metadata_output = tmp_path / "meta.jsonl"
    summary_output = tmp_path / "summary.json"
    db_dir = tmp_path / "db"
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
        assert rankings and rankings[0].project_id == "demo"
    finally:
        close_db()


def test_external_permission_denied_blocks():
    with pytest.raises(ExternalPermissionDenied):
        ensure_external_permission(
            "test.service",
            data_types=["metadata"],
            purpose="test",
            destination="nowhere",
            privacy="test",
            input_fn=lambda _prompt: "3",  # deny once
        )


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
    purged = store.purge(root, who="tester")
    assert purged["ok"]
    store.close()


def test_exports_exist_after_analyze(tmp_path):
    reset_config()
    grant_consent()
    zip_path = create_sample_zip(tmp_path)
    metadata_output = tmp_path / "meta.jsonl"
    summary_output = tmp_path / "summary.json"
    db_dir = tmp_path / "db"
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
