from fastapi.testclient import TestClient
from capstone.api.server import get_app_for_tests
from pathlib import Path
from capstone import storage
import uuid

def _any_zip():
    for name in ["demo.zip", "demo-2.zip", "demo-4.zip", "demo1.zip"]:
        p = Path(name)
        if p.exists():
            return p
    raise FileNotFoundError("No demo zip found")

def test_project_edit_roundtrip(tmp_path):
    original_base_dir = storage.BASE_DIR
    storage.close_db()
    storage.BASE_DIR = tmp_path
    app = get_app_for_tests(str(tmp_path))
    client = TestClient(app)

    zip_path = _any_zip()
    try:
        with open(zip_path, "rb") as f:
            r = client.post(
                "/projects/upload",
                params={"project_id": f"project-edit-{uuid.uuid4().hex[:8]}"},
                files={"file": (zip_path.name, f, "application/zip")},
            )
        assert r.status_code == 200
        project_id = r.json()["project_id"]

        patch = {
            "key_role": "Backend Developer",
            "evidence": "Added incremental uploads + API tests.",
            "portfolio_blurb": "Built a FastAPI upload and analysis pipeline.",
            "resume_bullets": ["Implemented upload dedupe", "Added incremental snapshots"],
            "selected": True,
            "rank": 1,
        }

        r2 = client.patch(f"/projects/{project_id}", json=patch)
        assert r2.status_code == 200
        assert r2.json()["data"]["key_role"] == "Backend Developer"

        r3 = client.get(f"/projects/{project_id}/overrides")
        assert r3.status_code == 200
        assert r3.json()["data"]["rank"] == 1
    finally:
        storage.close_db()
        storage.BASE_DIR = original_base_dir
