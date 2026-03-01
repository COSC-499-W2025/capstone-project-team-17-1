import pytest
from fastapi.testclient import TestClient

from capstone.api.server import create_app


AUTH_TOKEN = "t"
AUTH_HEADER = {"Authorization": f"Bearer {AUTH_TOKEN}"}
BAD_AUTH_HEADER = {"Authorization": "Bearer wrong-token"}


@pytest.fixture()
def client(tmp_path):
    # Use a temp db_dir so the test doesn't touch real data
    app = create_app(db_dir=str(tmp_path), auth_token=AUTH_TOKEN)
    return TestClient(app)


# Only include endpoints we *know* are auth-protected already (based on your 401 results/tests).
PROTECTED_ENDPOINTS = [
    ("GET", "/users/raunak/projects"),
    ("GET", "/showcase/users"),
    ("GET", "/portfolios/latest?projectId=demo"),
]


@pytest.mark.parametrize("method,path", PROTECTED_ENDPOINTS)
def test_auth_required_no_token_returns_401(client: TestClient, method: str, path: str):
    r = getattr(client, method.lower())(path)
    assert r.status_code == 401


@pytest.mark.parametrize("method,path", PROTECTED_ENDPOINTS)
def test_auth_required_wrong_token_returns_401(client: TestClient, method: str, path: str):
    r = getattr(client, method.lower())(path, headers=BAD_AUTH_HEADER)
    assert r.status_code == 401


@pytest.mark.parametrize("method,path", PROTECTED_ENDPOINTS)
def test_auth_required_valid_token_not_401(client: TestClient, method: str, path: str):
    r = getattr(client, method.lower())(path, headers=AUTH_HEADER)
    assert r.status_code != 401