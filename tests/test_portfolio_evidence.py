from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi")
from capstone.api.server import create_app
from fastapi.testclient import TestClient
from capstone import storage


def _insert_snapshot(tmp_path: Path, project_id: str = "p1"):
    snapshot = {
        "metrics": {"Accuracy": "92%", "Users": "50+"},
        "skills": ["Python"],
    }
    conn = storage.open_db()
    storage.store_analysis_snapshot(
        conn,
        project_id=project_id,
        classification="demo",
        primary_contributor="raunak",
        snapshot=snapshot,
    )
    storage.close_db()


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
    storage.open_db()  # initialise schema; no data inserted
    storage.close_db()

    app = create_app(db_dir=str(tmp_path), auth_token=None)
    client = TestClient(app)

    try:
        resp = client.get("/portfolios/evidence?projectId=does-not-exist")
        assert resp.status_code == 404, resp.text
    finally:
        storage.close_db()
        storage.BASE_DIR = original_base_dir
