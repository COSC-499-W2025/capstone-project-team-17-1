import json
import pytest

from fastapi.testclient import TestClient
from capstone.api.server import create_app
from capstone import storage

@pytest.fixture()
def client(tmp_path):
    original_base_dir = storage.BASE_DIR
    storage.close_db()
    storage.BASE_DIR = tmp_path
    storage._bind_storage_user(None)

    conn = storage.open_db()
    try:
        snap = {
            "project_name": "Demo Project",
            "languages": {"Python": 1.0},
            "summary": "demo summary",
            "highlights": ["FastAPI"]
        }
        storage.store_analysis_snapshot(
            conn,
            project_id="demo",
            classification="ok",
            primary_contributor="alice",
            snapshot=snap,
        )
    finally:
        conn.close()
    
    app = create_app(auth_token=None)
    test_client = TestClient(app)
    try:
        yield test_client
    finally:
        storage.close_db()
        storage.BASE_DIR = original_base_dir


def test_generate_portfolio_success(client):
    payload = {"project_ids": ["demo"], "owner": "alice"}
    response = client.post("/portfolio/generate", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    
    assert "portfolio" in data
    assert data["portfolio"]["owner"] == "alice"
    assert len(data["portfolio"]["projects"]) == 1
    assert data["portfolio"]["projects"][0]["project_id"] == "demo"
    
def test_generate_portfolio_snapshot_missing_404(client):
    payload = {"project_ids": ["nonexistent"], "owner": "bob"}
    response = client.post("/portfolio/generate", json=payload)
    
    assert response.status_code == 404
    assert "No snapshot found" in response.json()["detail"]
    
def test_edit_portfolio_success(client):
    payload = {
        "owner": "user",
        "projects": [
            {
                "project_id": "proj1",
                "title": "Bowling Game Project",
                "technologies": ["Python"],
                "highlights": ["FastAPI"]
            }
        ]
    }
    
    response = client.post("/portfolio/latest/edit", json=payload)
    assert response.status_code == 200
    
    data = response.json()["portfolio"]
    assert data["owner"] == "user"
    assert data["id"] == "latest"
    assert len(data["projects"]) == 1
    assert data["projects"][0]["project_id"] == "proj1"

def test_export_portfolio_json(client):
    response = client.get("/portfolio/latest/export?format=json")
    
    assert response.status_code == 200
    assert "portfolio_id" in response.json()
    
def test_export_portfolio_markdown(client):
    response = client.get("/portfolio/latest/export?format=markdown")
    
    assert response.status_code == 200
    assert "content" in response.json()
    
def test_export_portfolio_pdf(client):
    response = client.get("/portfolio/latest/export?format=pdf")
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"].startswith("attachment")
    
    assert response.content.startswith(b"%PDF")
    
def test_export_portfolio_invalid_format(client):
    response = client.get("/portfolio/latest/export?format=exe")
    assert response.status_code == 422
    
    body = response.json()
    assert body["detail"][0]["loc"][-1] == "format"
