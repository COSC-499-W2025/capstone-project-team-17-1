from fastapi.testclient import TestClient
from capstone.api.server import get_app_for_tests
from pathlib import Path

def _any_zip():
    # pick an existing demo zip from repo (adjust if your filenames differ)
    for name in ["demo.zip", "demo-2.zip", "demo-4.zip", "demo1.zip"]:
        p = Path(name)
        if p.exists():
            return p
    raise FileNotFoundError("No demo zip found (demo.zip/demo-2.zip/demo-4.zip/demo1.zip)")

def test_incremental_upload_creates_multiple_upload_rows(tmp_path):
    app = get_app_for_tests(str(tmp_path))
    client = TestClient(app)

    zip_path = _any_zip()

    # First upload creates a project_id
    with open(zip_path, "rb") as f:
        r1 = client.post("/projects/upload", files={"file": (zip_path.name, f, "application/zip")})
    assert r1.status_code == 200
    project_id = r1.json()["project_id"]

    # Second upload reuses the same project_id (incremental snapshot)
    with open(zip_path, "rb") as f:
        r2 = client.post(f"/projects/upload?project_id={project_id}", files={"file": (zip_path.name, f, "application/zip")})
    assert r2.status_code == 200
    assert r2.json()["project_id"] == project_id

    # Check we have >=2 upload records for that project_id
    r3 = client.get(f"/projects/{project_id}/uploads")
    assert r3.status_code == 200
    assert r3.json()["count"] >= 2

def test_duplicate_upload_sets_dedup_true(tmp_path):
    app = get_app_for_tests(str(tmp_path))
    client = TestClient(app)

    zip_path = _any_zip()

    with open(zip_path, "rb") as f:
        r1 = client.post("/projects/upload", files={"file": (zip_path.name, f, "application/zip")})
    assert r1.status_code == 200

    project_id = r1.json()["project_id"]

    # reupload same zip under same project_id should dedup the file (hash already exists)
    with open(zip_path, "rb") as f:
        r2 = client.post(f"/projects/upload?project_id={project_id}", files={"file": (zip_path.name, f, "application/zip")})
    assert r2.status_code == 200
    assert r2.json()["dedup"] is True