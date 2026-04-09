import json
import pytest

from fastapi.testclient import TestClient
from capstone.api.server import create_app
from capstone import storage

@pytest.fixture()
def showcase_client(tmp_path):
    original_base_dir = storage.BASE_DIR
    storage.close_db()
    storage.BASE_DIR = tmp_path
    storage._bind_storage_user(None)
    app = create_app(auth_token=None)
    client = TestClient(app)

    r = client.get("/showcase/users")
    assert r.status_code == 200

    try:
        yield client
    finally:
        storage.close_db()
        storage.BASE_DIR = original_base_dir

def seed_snapshot(project_id: str, snapshot: dict):
    conn = storage.open_db()
    try:
        storage.store_analysis_snapshot(
            conn,
            project_id=project_id,
            classification="ok",
            primary_contributor="alice",
            snapshot=snapshot,
        )
    finally:
        conn.close()

def seed_contributor(project_id: str, contributor: str = "alice"):
    conn = storage.open_db()
    try:
        user_id = storage.upsert_contributor(conn, contributor)
        storage.upsert_project(conn, project_id)
        storage.store_contributor_stats(
            conn,
            project_id=project_id,
            contributor=contributor,
            user_id=user_id,
            commits=1,
            score=1.0,
        )
    finally:
        conn.close()

def test_showcase_users_returns_list(showcase_client):
    client = showcase_client

    # seed contributor to ensure at least one user is returned
    seed_snapshot("demo", {"summary": "seed"})
    seed_contributor("demo", "alice")

    r = client.get("/showcase/users")
    assert r.status_code == 200
    body = r.json()
    assert body["error"] is None
    assert isinstance(body["data"], list)

def test_showcase_auth_enforced_with_db(tmp_path):
    original_base_dir = storage.BASE_DIR
    storage.close_db()
    storage.BASE_DIR = tmp_path
    storage._bind_storage_user(None)
    app = create_app(auth_token="secret-token")
    client = TestClient(app)

    # missing token blocked
    resp = client.get("/showcase/users")
    assert resp.status_code == 401

    # valid token initializes db
    resp_init = client.get("/showcase/users", headers={"Authorization": "Bearer secret-token"})
    assert resp_init.status_code == 200

    try:
        seed_snapshot("demo", {"summary": "seed"})
        seed_contributor("demo", "alice")

        # valid token works -> returns list
        resp2 = client.get("/showcase/users", headers={"Authorization": "Bearer secret-token"})
        assert resp2.status_code == 200
        assert resp2.json()["error"] is None
        assert isinstance(resp2.json()["data"], list)
    finally:
        storage.close_db()
        storage.BASE_DIR = original_base_dir
