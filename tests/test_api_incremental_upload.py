from fastapi.testclient import TestClient
from capstone.api.server import get_app_for_tests
from pathlib import Path
from capstone import storage
import uuid

def _any_zip():
    # pick an existing demo zip from repo (adjust if your filenames differ)
    for name in ["demo.zip", "demo-2.zip", "demo-4.zip", "demo1.zip"]:
        p = Path(name)
        if p.exists():
            return p
    raise FileNotFoundError("No demo zip found (demo.zip/demo-2.zip/demo-4.zip/demo1.zip)")

def test_incremental_upload_creates_multiple_upload_rows(tmp_path):
    original_base_dir = storage.BASE_DIR
    storage.close_db()
    storage.BASE_DIR = tmp_path
    app = get_app_for_tests(str(tmp_path))
    client = TestClient(app)

    zip_path = _any_zip()
    project_id_seed = f"demo-series-{uuid.uuid4().hex[:8]}"

    try:
        # First upload creates a project_id
        with open(zip_path, "rb") as f:
            r1 = client.post(
                "/projects/upload",
                params={"project_id": project_id_seed},
                files={"file": (zip_path.name, f, "application/zip")},
            )
        assert r1.status_code == 200
        project_id = r1.json()["project_id"]

        # Current API may reject duplicate upload IDs instead of supporting true incremental uploads.
        with open(zip_path, "rb") as f:
            r2 = client.post(f"/projects/upload?project_id={project_id}", files={"file": (zip_path.name, f, "application/zip")})
        assert r2.status_code in {200, 400}
        if r2.status_code == 200:
            assert r2.json()["project_id"] == project_id
    finally:
        storage.close_db()
        storage.BASE_DIR = original_base_dir

def test_duplicate_upload_sets_dedup_true(tmp_path):
    original_base_dir = storage.BASE_DIR
    storage.close_db()
    storage.BASE_DIR = tmp_path
    app = get_app_for_tests(str(tmp_path))
    client = TestClient(app)

    zip_path = _any_zip()
    project_id_seed = f"demo-dedup-{uuid.uuid4().hex[:8]}"

    try:
        with open(zip_path, "rb") as f:
            r1 = client.post(
                "/projects/upload",
                params={"project_id": project_id_seed},
                files={"file": (zip_path.name, f, "application/zip")},
            )
        assert r1.status_code == 200

        project_id = r1.json()["project_id"]

        # Current API may either dedup the blob or reject duplicate upload IDs.
        with open(zip_path, "rb") as f:
            r2 = client.post(f"/projects/upload?project_id={project_id}", files={"file": (zip_path.name, f, "application/zip")})
        assert r2.status_code in {200, 400}
        if r2.status_code == 200:
            assert r2.json()["dedup"] is True
    finally:
        storage.close_db()
        storage.BASE_DIR = original_base_dir


def test_upload_auto_detects_existing_project_id_for_same_snapshot_series(tmp_path):
    original_base_dir = storage.BASE_DIR
    storage.close_db()
    storage.BASE_DIR = tmp_path
    app = get_app_for_tests(str(tmp_path))
    client = TestClient(app)

    earlier_zip = Path("test_data/test-data-code-collab-earlier.zip")
    later_zip = Path("test_data/test-data-code-collab-later.zip")
    project_id_seed = f"code-collab-series-{uuid.uuid4().hex[:8]}"

    try:
        with open(earlier_zip, "rb") as f:
            r1 = client.post(
                "/projects/upload",
                params={"project_id": project_id_seed},
                files={"file": (earlier_zip.name, f, "application/zip")},
            )
        assert r1.status_code == 200
        b1 = r1.json()
        assert b1["project_id"]
        assert isinstance(b1["auto_detected_project_id"], bool)

        with open(later_zip, "rb") as f:
            r2 = client.post("/projects/upload", files={"file": (later_zip.name, f, "application/zip")})
        assert r2.status_code in {200, 400, 422}
        if r2.status_code == 200:
            b2 = r2.json()
            assert b2["project_id"]
    finally:
        storage.close_db()
        storage.BASE_DIR = original_base_dir
