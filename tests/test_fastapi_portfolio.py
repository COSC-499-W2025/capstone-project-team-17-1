import json
import sqlite3
import pytest
from pathlib import Path

from fastapi.testclient import TestClient
from capstone.api.server import create_app

@pytest.fixture()
def client(tmp_path):
    db_dir = str(tmp_path)
    db_path = str(Path(db_dir) / "capstone.db")
    
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS project_analysis(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT NOT NULL,
            classification TEXT,
            primary_contributor TEXT,
            snapshot TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        conn.commit()
        
        snap = {
            "project_name": "Demo Project",
            "languages": {"Python": 1.0},
            "summary": "demo summary",
            "highlights": ["FastAPI"]
        }
        conn.execute(
            "INSERT INTO project_analysis(project_id, classification, primary_contributor, snapshot) VALUES (?, ?, ?, ?)",
            ("demo", "ok", "alice", json.dumps(snap)),
        )
        conn.commit()
    finally:
        conn.close()
    
    app = create_app(db_dir=db_dir, auth_token=None)
    return TestClient(app)


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