import json
import sqlite3
import pytest
from pathlib import Path

from fastapi.testclient import TestClient
from capstone.api.server import create_app
from capstone import storage

@pytest.fixture()
def showcase_client(tmp_path):
    original_base_dir = storage.BASE_DIR
    storage.close_db()
    storage.BASE_DIR = tmp_path
    storage.CURRENT_USER = None
    db_dir = str(tmp_path)
    app = create_app(db_dir=db_dir, auth_token=None)
    client = TestClient(app)

    r = client.get("/showcase/users")
    assert r.status_code == 200

    db_path = str(Path(db_dir) / "data" / "guest" / "capstone.db")
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    try:
        yield client, db_path
    finally:
        storage.close_db()
        storage.BASE_DIR = original_base_dir

def seed_snapshot(db_path: str, project_id: str, snapshot: dict):
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            INSERT INTO project_analysis(project_id, classification, primary_contributor, snapshot)
            VALUES (?, ?, ?, ?)
            """,
            (project_id, "ok", "alice", json.dumps(snapshot)),
        )
        conn.commit()
    finally:
        conn.close()

def seed_contributor(db_path: str, project_id: str, contributor: str = "alice"):
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            INSERT INTO contributor_stats(project_id, contributor, commits, pull_requests, issues, reviews, score, source)
            VALUES (?, ?, 1, 0, 0, 0, 1.0, "test")
            """,
            (project_id, contributor),
        )
        conn.commit()
    finally:
        conn.close()

def test_showcase_users_returns_list(showcase_client):
    client, db_path = showcase_client

    # seed contributor to ensure at least one user is returned
    seed_snapshot(db_path, "demo", {"summary": "seed"})
    seed_contributor(db_path, "demo", "alice")

    r = client.get("/showcase/users")
    assert r.status_code == 200
    body = r.json()
    assert body["error"] is None
    assert isinstance(body["data"], list)

def test_showcase_auth_enforced_with_db(tmp_path):
    original_base_dir = storage.BASE_DIR
    storage.close_db()
    storage.BASE_DIR = tmp_path
    storage.CURRENT_USER = None
    db_dir = str(tmp_path)
    app = create_app(db_dir=db_dir, auth_token="secret-token")
    client = TestClient(app)

    # missing token blocked
    resp = client.get("/showcase/users")
    assert resp.status_code == 401

    # valid token initializes db
    resp_init = client.get("/showcase/users", headers={"Authorization": "Bearer secret-token"})
    assert resp_init.status_code == 200

    db_path = str(Path(db_dir) / "data" / "guest" / "capstone.db")
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    try:
        seed_snapshot(db_path, "demo", {"summary": "seed"})
        seed_contributor(db_path, "demo", "alice")

        # valid token works -> returns list
        resp2 = client.get("/showcase/users", headers={"Authorization": "Bearer secret-token"})
        assert resp2.status_code == 200
        assert resp2.json()["error"] is None
        assert isinstance(resp2.json()["data"], list)
    finally:
        storage.close_db()
        storage.BASE_DIR = original_base_dir
