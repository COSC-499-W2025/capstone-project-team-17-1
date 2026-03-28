import json
import sqlite3
from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi")
from capstone.api.server import create_app
from fastapi.testclient import TestClient
from capstone import storage


def _make_db(tmp_path: Path):
    """
    Create the SQLite DB in the exact location expected by API helpers:
      sqlite3.connect(Path(db_dir) / "capstone.db")
    """
    db_path = tmp_path / "data" / "guest" / "capstone.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
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
    return db_path


def _insert_snapshot(tmp_path: Path, project_id: str = "p1"):
    db_path = _make_db(tmp_path)
    conn = sqlite3.connect(db_path)

    snapshot = {
        "metrics": {"Accuracy": "92%", "Users": "50+"},
        "skills": ["Python"],
    }

    conn.execute(
        "INSERT INTO project_analysis(project_id, classification, primary_contributor, snapshot, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (project_id, "demo", "raunak", json.dumps(snapshot), "2026-01-11T00:00:00Z"),
    )
    conn.commit()
    conn.close()


def test_portfolios_evidence_happy_path(tmp_path, monkeypatch):
    if TestClient is None:
        return
    original_base_dir = storage.BASE_DIR
    storage.close_db()
    storage.BASE_DIR = tmp_path
    storage.CURRENT_USER = None
    _insert_snapshot(tmp_path, project_id="p1")

    app = create_app(db_dir=str(tmp_path), auth_token=None)
    client = TestClient(app)

    try:
        resp = client.get("/portfolios/evidence?projectId=p1")
        assert resp.status_code == 200, resp.text

        body = resp.json()
        assert body["error"] is None
        assert body["data"]["projectId"] == "p1"

        evidence = body["data"]["evidence"]
        assert evidence["type"] == "metrics"
        assert any(
            i["label"] == "Accuracy" and i["value"] == "92%"
            for i in evidence["items"]
        )
    finally:
        storage.close_db()
        storage.BASE_DIR = original_base_dir


def test_portfolios_evidence_missing_project_id(tmp_path, monkeypatch):
    if TestClient is None:
        return
    original_base_dir = storage.BASE_DIR
    storage.close_db()
    storage.BASE_DIR = tmp_path
    storage.CURRENT_USER = None

    app = create_app(db_dir=str(tmp_path), auth_token=None)
    client = TestClient(app)

    try:
        resp = client.get("/portfolios/evidence")
        assert resp.status_code in {400, 422}, resp.text
    finally:
        storage.close_db()
        storage.BASE_DIR = original_base_dir


def test_portfolios_evidence_not_found(tmp_path, monkeypatch):
    if TestClient is None:
        return
    original_base_dir = storage.BASE_DIR
    storage.close_db()
    storage.BASE_DIR = tmp_path
    storage.CURRENT_USER = None
    _make_db(tmp_path)  # empty DB but table exists

    app = create_app(db_dir=str(tmp_path), auth_token=None)
    client = TestClient(app)

    try:
        resp = client.get("/portfolios/evidence?projectId=does-not-exist")
        assert resp.status_code == 404, resp.text
    finally:
        storage.close_db()
        storage.BASE_DIR = original_base_dir
