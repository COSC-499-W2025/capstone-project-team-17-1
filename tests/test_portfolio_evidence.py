import json
import sqlite3

import capstone.portfolio_retrieval as pr


def _make_db_with_one_snapshot(tmp_path):
    db_path = tmp_path / "capstone.db"
    conn = sqlite3.connect(db_path)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS project_analysis (
        project_id TEXT NOT NULL,
        classification TEXT,
        primary_contributor TEXT,
        snapshot TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    snapshot = {
        "metrics": {"Accuracy": "92%", "Users": "50+"},
        "skills": ["Python", "Flask"]
    }

    conn.execute(
        "INSERT INTO project_analysis(project_id, classification, primary_contributor, snapshot, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        ("p1", "demo", "raunak", json.dumps(snapshot), "2026-01-11T00:00:00Z"),
    )
    conn.commit()
    conn.close()
    return db_path


def test_portfolios_evidence_happy_path(tmp_path, monkeypatch):
    # Force portfolio_retrieval to use local sqlite fallback instead of capstone.storage.open_db
    monkeypatch.setattr(pr, "_open_db", None)
    monkeypatch.setattr(pr, "_close_db", None)
    monkeypatch.setattr(pr, "_fetch_latest_snapshot", None)

    _make_db_with_one_snapshot(tmp_path)

    app = pr.create_app(db_dir=str(tmp_path), auth_token=None)
    client = app.test_client()

    resp = client.get("/portfolios/evidence?projectId=p1")

    # If it fails, show body to make debugging instant
    assert resp.status_code == 200, resp.get_data(as_text=True)

    body = resp.get_json()
    assert body["error"] is None
    assert body["data"]["projectId"] == "p1"

    evidence = body["data"]["evidence"]
    assert evidence["type"] == "metrics"
    assert any(i["label"] == "Accuracy" and i["value"] == "92%" for i in evidence["items"])


def test_portfolios_evidence_missing_project_id(tmp_path, monkeypatch):
    monkeypatch.setattr(pr, "_open_db", None)
    monkeypatch.setattr(pr, "_close_db", None)
    monkeypatch.setattr(pr, "_fetch_latest_snapshot", None)

    app = pr.create_app(db_dir=str(tmp_path), auth_token=None)
    client = app.test_client()

    resp = client.get("/portfolios/evidence")
    assert resp.status_code == 400


def test_portfolios_evidence_not_found(tmp_path, monkeypatch):
    monkeypatch.setattr(pr, "_open_db", None)
    monkeypatch.setattr(pr, "_close_db", None)
    monkeypatch.setattr(pr, "_fetch_latest_snapshot", None)

    # Create empty DB with table so it doesn't 500
    db_path = tmp_path / "capstone.db"
    conn = sqlite3.connect(db_path)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS project_analysis (
        project_id TEXT NOT NULL,
        classification TEXT,
        primary_contributor TEXT,
        snapshot TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)
    conn.commit()
    conn.close()

    app = pr.create_app(db_dir=str(tmp_path), auth_token=None)
    client = app.test_client()

    resp = client.get("/portfolios/evidence?projectId=does-not-exist")
    assert resp.status_code == 404
