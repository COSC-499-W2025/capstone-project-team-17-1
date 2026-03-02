from fastapi.testclient import TestClient
from capstone.api.server import get_app_for_tests
from pathlib import Path


EARLIER_ZIP = Path("test_data/test-data-code-collab-earlier.zip")
LATER_ZIP = Path("test_data/test-data-code-collab-later.zip")


def test_auto_detect_project_id_and_snapshot_diff(tmp_path):
    app = get_app_for_tests(str(tmp_path))
    client = TestClient(app)

    with open(EARLIER_ZIP, "rb") as f:
        r1 = client.post("/projects/upload", files={"file": (EARLIER_ZIP.name, f, "application/zip")})
    assert r1.status_code == 200
    p1 = r1.json()["project_id"]
    assert p1
    assert isinstance(r1.json()["auto_detected_project_id"], bool)

    with open(LATER_ZIP, "rb") as f:
        r2 = client.post("/projects/upload", files={"file": (LATER_ZIP.name, f, "application/zip")})
    assert r2.status_code == 200
    body2 = r2.json()
    assert body2["project_id"] == p1
    assert body2["auto_detected_project_id"] is True

    r3 = client.get(f"/projects/{p1}/uploads")
    assert r3.status_code == 200
    assert r3.json()["count"] >= 2

    uploads_body = r3.json()
    diff = uploads_body["snapshot_diff"]
    assert diff is not None
    assert "app/feature.py" in diff["files"]["added"]
    assert "infra/deploy.yml" in diff["files"]["added"]
    assert "python" in diff["skills"]["before"]
    assert "yaml" in diff["skills"]["after"]
    assert any(change["name"] == "yaml" and change["delta"] > 0 for change in diff["skills"]["changes"])
