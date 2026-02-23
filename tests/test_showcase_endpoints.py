import json
import sqlite3
import pytest
from pathlib import Path

from fastapi.testclient import TestClient
from capstone.api.server import create_app
from capstone.resume_retrieval import ensure_resume_schema, upsert_resume_project_description

@pytest.fixture()
def showcase_client(tmp_path):
    db_dir = str(tmp_path)
    app = create_app(db_dir=db_dir, auth_token=None)
    client = TestClient(app)

    r = client.get("/showcase/users")
    assert r.status_code == 200

    db_path = str(Path(db_dir) / "capstone.db")
    return client, db_path

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

def seed_portfolio_showcase_variant(db_path: str, project_id: str, summary: str, source: str = "custom") -> dict:
    conn = sqlite3.connect(db_path)
    try:
        ensure_resume_schema(conn)
        item = upsert_resume_project_description(
            conn,
            project_id=project_id,
            summary=summary,
            variant_name="portfolio_showcase",
            metadata={"source": source},
        )
        conn.commit()
        return item.to_dict()
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
    assert "alice" in body["data"]

def test_showcase_get_portfolio_returns_saved(showcase_client):
    client, db_path = showcase_client
    expected = seed_portfolio_showcase_variant(db_path, "demo1", "Showcase summary saved")

    resp = client.get("/showcase/portfolio/demo1")
    assert resp.status_code == 200
    body = resp.json()
    assert body["error"] is None
    assert body["data"] == expected

def test_showcase_get_portfolio_falls_back_to_snapshot(showcase_client):
    client, db_path = showcase_client
    seed_snapshot(
        db_path,
        "demo2",
        {"languages": {"Python": 0.8}, "frameworks": ["FastAPI"], "summary": "Snapshot summary"},
    )

    resp = client.get("/showcase/portfolio/demo2")
    assert resp.status_code == 200
    body = resp.json()
    assert body["error"] is None
    assert body["data"]["project_id"] == "demo2"
    assert isinstance(body["data"]["summary"], str)
    assert len(body["data"]["summary"]) > 0

def test_showcase_get_portfolio_404_when_missing_everything(showcase_client):
    client, _ = showcase_client

    resp = client.get("/showcase/portfolio/does-not-exist")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "No snapshots found"

def test_showcase_query_alias(showcase_client):
    client, db_path = showcase_client
    expected = seed_portfolio_showcase_variant(db_path, "demo3", "Alias summary")

    resp = client.get("/showcase/portfolio/showcase", params={"projectId": "demo3"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["error"] is None
    assert body["data"] == expected

def test_showcase_generate_validates_payload(showcase_client):
    client, _ = showcase_client

    resp = client.post("/showcase/portfolio/generate", json={"projectIds": "not-a-list"})
    assert resp.status_code == 400
    assert resp.json()["detail"] == "projectIds must be a list"

def test_showcase_generate_creates_items_for_projects_with_snapshots(showcase_client):
    client, db_path = showcase_client

    seed_snapshot(db_path, "demo4", {"summary": "one"})
    seed_snapshot(db_path, "demo5", {"summary": "two"})

    resp = client.post("/showcase/portfolio/generate", json={"projectIds": ["demo4", "demo5", "demo6"]})
    assert resp.status_code == 200
    body = resp.json()
    assert body["error"] is None
    project_ids = {item["project_id"] for item in body["data"]}
    assert project_ids == {"demo4", "demo5"}

def test_showcase_edit_requires_summary(showcase_client):
    client, db_path = showcase_client
    seed_snapshot(db_path, "demo7", {"summary": "seed"})

    resp = client.post("/showcase/portfolio/demo7/edit", json={"summary": ""})
    assert resp.status_code == 400
    assert resp.json()["detail"] == "summary is required"

def test_showcase_edit_persists(showcase_client):
    client, db_path = showcase_client
    seed_snapshot(db_path, "demo8", {"summary": "seed"})

    resp = client.post("/showcase/portfolio/demo8/edit", json={"summary": "My custom summary"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["error"] is None
    assert body["data"]["project_id"] == "demo8"
    assert body["data"]["summary"] == "My custom summary"

def test_showcase_auth_enforced_with_db(tmp_path):
    db_dir = str(tmp_path)
    app = create_app(db_dir=db_dir, auth_token="secret-token")
    client = TestClient(app)

    # missing token blocked
    resp = client.get("/showcase/users")
    assert resp.status_code == 401

    # valid token initializes db
    resp_init = client.get("/showcase/users", headers={"Authorization": "Bearer secret-token"})
    assert resp_init.status_code == 200

    db_path = str(Path(db_dir) / "capstone.db")
    seed_snapshot(db_path, "demo", {"summary": "seed"})
    seed_contributor(db_path, "demo", "alice")

    # valid token works -> returns list
    resp2 = client.get("/showcase/users", headers={"Authorization": "Bearer secret-token"})
    assert resp2.status_code == 200
    assert resp2.json()["error"] is None
    assert isinstance(resp2.json()["data"], list)