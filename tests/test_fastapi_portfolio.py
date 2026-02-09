from fastapi.testclient import TestClient
from capstone.api.server import app

client = TestClient(app)

def test_get_portfolio_success():
    response = client.get("/portfolio/demo")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "portfolio" in data
    assert data["portfolio"]["id"] == "demo"
    
def test_get_portfolio_not_found():
    response = client.get("/portfolio/does-not-exist")
    
    assert response.status_code == 404
    assert response.json()["detail"] == "Portfolio not found"
    
def test_generate_portfolio():
    payload = {
        "project_ids": ["proj1", "proj2"],
        "owner": "user123",
        "style": ":default"
    }
    
    response = client.post("/portfolio/generate", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    
    portfolio = data["portfolio"]
    assert portfolio["owner"] == "user123"
    assert len(portfolio["projects"]) == 2
    
def test_edit_portfolio_success():
    payload = {
        "projects": [
            {
                "project_id": "proj1",
                "title": "Updated Project",
                "technologies": ["Python"],
                "highlights": ["FastAPI"]
            }
        ]
    }
    
    response = client.post("/portfolio/demo/edit", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["portfolio"]["id"] == "demo"
    assert len(data["portfolio"]["projects"]) == 1
    
def test_edit_portfolio_not_found():
    payload = {
        "title": "Should not work here"
    }
    
    response = client.post("/portfolio/invalid/edit", json=payload)
    
    assert response.status_code == 404
    assert response.json()["detail"] == "Portfolio not found"
    
def test_export_portfolio_json():
    response = client.get("/portfolio/demo/export")
    
    assert response.status_code == 200
    assert "portfolio_id" in response.json()
    
def test_export_portfolio_markdown():
    response = client.get("/portfolio/demo/export?format=markdown")
    
    assert response.status_code == 200
    assert "content" in response.json()
    
def test_export_portfolio_pdf():
    response = client.get("/portfolio/demo/export?format=pdf")
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"].startswith("attachment")
    
    assert response.content.startswith(b"%PDF")
    
def test_export_portfolio_invalid_format():
    response = client.get("/portfolio/demo/export?format=exe")
    assert response.status_code == 422
    
    body = response.json()
    assert body["detail"][0]["loc"][-1] == "format"