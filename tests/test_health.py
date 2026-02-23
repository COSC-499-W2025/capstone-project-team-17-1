from fastapi.testclient import TestClient
from capstone.api.server import get_app_for_tests

def test_health(tmp_path):
    app = get_app_for_tests(str(tmp_path))
    client = TestClient(app)

    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}