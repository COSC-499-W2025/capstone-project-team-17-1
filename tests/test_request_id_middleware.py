from fastapi.testclient import TestClient
from capstone.api.server import create_app


def test_request_id_generated_when_missing(tmp_path):
    app = create_app(db_dir=str(tmp_path), auth_token=None)
    client = TestClient(app)

    r = client.get("/health")
    assert r.status_code == 200
    assert "X-Request-ID" in r.headers
    assert len(r.headers["X-Request-ID"]) > 5


def test_request_id_echoed_when_provided(tmp_path):
    app = create_app(db_dir=str(tmp_path), auth_token=None)
    client = TestClient(app)

    rid = "my-fixed-id-123"
    r = client.get("/health", headers={"X-Request-ID": rid})
    assert r.status_code == 200
    assert r.headers["X-Request-ID"] == rid