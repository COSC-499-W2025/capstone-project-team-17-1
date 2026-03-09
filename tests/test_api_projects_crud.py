"""
API-level tests for project CRUD endpoints:
- GET  /projects          (list)
- GET  /projects/{id}     (get single)
- DELETE /projects/{id}   (delete)
- GET  /projects/{id}/overrides (get overrides)
- PATCH /projects/{id}    (update overrides)

A minimal in-memory ZIP is created per test so no external fixtures are needed.
"""

import io
import sys
import uuid
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import capstone.storage as storage  # noqa: E402
from capstone.api.server import create_app  # noqa: E402

_ORIGINAL_BASE_DIR = storage.BASE_DIR


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _client(tmp_path) -> TestClient:
    """Create an isolated TestClient that stores data in tmp_path."""
    storage.BASE_DIR = Path(tmp_path)
    app = create_app(db_dir=str(tmp_path), auth_token=None)
    return TestClient(app)


def _make_zip(name: str = "project.zip", unique_tag: str = "") -> tuple[str, bytes, str]:
    """Return (filename, bytes, mime) for a minimal valid ZIP.

    Pass a unique_tag to produce distinct ZIP content (avoids file dedup across uploads).
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("README.md", f"# Test project {unique_tag}\n")
        zf.writestr("main.py", "print('hello')\n")
        zf.writestr(
            "git_log.txt",
            "commit:abc123|Alice|alice@example.com|1700000000|Initial commit\n1\t0\tmain.py\n",
        )
    return name, buf.getvalue(), "application/zip"


def _upload_project(client: TestClient, project_id: str | None = None) -> str:
    """Upload a minimal ZIP with unique content and return the project_id."""
    pid = project_id or f"test-{uuid.uuid4().hex[:8]}"
    name, data, mime = _make_zip(unique_tag=pid)
    resp = client.post(
        f"/projects/upload?project_id={pid}",
        files={"file": (name, data, mime)},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["project_id"]


@pytest.fixture(autouse=True)
def restore_base_dir():
    """Restore storage.BASE_DIR after each test."""
    yield
    storage.BASE_DIR = _ORIGINAL_BASE_DIR
    storage.close_db()


# ---------------------------------------------------------------------------
# GET /projects — list
# ---------------------------------------------------------------------------

class TestListProjects:
    def test_list_empty_returns_zero_count(self, tmp_path):
        client = _client(tmp_path)
        resp = client.get("/projects")
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 0
        assert body["projects"] == []

    def test_list_after_upload_returns_one_project(self, tmp_path):
        client = _client(tmp_path)
        _upload_project(client)
        resp = client.get("/projects")
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 1
        assert len(body["projects"]) == 1

    def test_list_project_has_required_fields(self, tmp_path):
        client = _client(tmp_path)
        _upload_project(client)
        resp = client.get("/projects")
        project = resp.json()["projects"][0]
        for field in ("project_id", "filename", "file_id", "hash", "created_at", "size_bytes"):
            assert field in project, f"Missing field: {field}"

    def test_list_multiple_uploads_returns_all(self, tmp_path):
        client = _client(tmp_path)
        for i in range(3):
            name, data, mime = _make_zip(f"proj{i}.zip")
            pid = f"multi-proj-{i}-{uuid.uuid4().hex[:6]}"
            client.post(f"/projects/upload?project_id={pid}", files={"file": (name, data, mime)})
        resp = client.get("/projects")
        assert resp.json()["count"] == 3

    def test_list_filename_matches_uploaded_name(self, tmp_path):
        client = _client(tmp_path)
        name, data, mime = _make_zip("myproject.zip")
        pid = f"name-test-{uuid.uuid4().hex[:6]}"
        client.post(f"/projects/upload?project_id={pid}", files={"file": (name, data, mime)})
        resp = client.get("/projects")
        assert resp.json()["projects"][0]["filename"] == "myproject.zip"


# ---------------------------------------------------------------------------
# GET /projects/{id} — single project
# ---------------------------------------------------------------------------

class TestGetProject:
    def test_get_existing_project_returns_200(self, tmp_path):
        client = _client(tmp_path)
        pid = _upload_project(client)
        resp = client.get(f"/projects/{pid}")
        assert resp.status_code == 200

    def test_get_existing_project_has_correct_id(self, tmp_path):
        client = _client(tmp_path)
        pid = _upload_project(client)
        resp = client.get(f"/projects/{pid}")
        assert resp.json()["project_id"] == pid

    def test_get_existing_project_has_required_fields(self, tmp_path):
        client = _client(tmp_path)
        pid = _upload_project(client)
        body = client.get(f"/projects/{pid}").json()
        for field in ("project_id", "filename", "file_id", "hash", "created_at", "size_bytes"):
            assert field in body, f"Missing field: {field}"

    def test_get_nonexistent_project_returns_404(self, tmp_path):
        client = _client(tmp_path)
        resp = client.get("/projects/does-not-exist")
        assert resp.status_code == 404

    def test_get_project_matches_list_entry(self, tmp_path):
        client = _client(tmp_path)
        pid = _upload_project(client)
        single = client.get(f"/projects/{pid}").json()
        listed = client.get("/projects").json()["projects"][0]
        assert single["project_id"] == listed["project_id"]
        assert single["hash"] == listed["hash"]


# ---------------------------------------------------------------------------
# DELETE /projects/{id}
# ---------------------------------------------------------------------------

class TestDeleteProject:
    def test_delete_existing_project_returns_200(self, tmp_path):
        client = _client(tmp_path)
        pid = _upload_project(client)
        resp = client.delete(f"/projects/{pid}")
        assert resp.status_code == 200

    def test_delete_response_body_has_deleted_flag(self, tmp_path):
        client = _client(tmp_path)
        pid = _upload_project(client)
        body = client.delete(f"/projects/{pid}").json()
        assert body["data"]["deleted"] is True
        assert body["data"]["project_id"] == pid
        assert body["error"] is None

    def test_delete_removes_project_from_list(self, tmp_path):
        client = _client(tmp_path)
        pid = _upload_project(client)
        client.delete(f"/projects/{pid}")
        resp = client.get("/projects")
        assert resp.json()["count"] == 0

    def test_get_after_delete_returns_404(self, tmp_path):
        client = _client(tmp_path)
        pid = _upload_project(client)
        client.delete(f"/projects/{pid}")
        resp = client.get(f"/projects/{pid}")
        assert resp.status_code == 404

    def test_delete_nonexistent_project_returns_404(self, tmp_path):
        client = _client(tmp_path)
        resp = client.delete("/projects/ghost-id")
        assert resp.status_code == 404

    def test_delete_only_removes_target_project(self, tmp_path):
        client = _client(tmp_path)
        pid1 = _upload_project(client)
        pid2 = _upload_project(client)

        client.delete(f"/projects/{pid1}")

        remaining = client.get("/projects").json()
        assert remaining["count"] == 1
        assert remaining["projects"][0]["project_id"] == pid2

    def test_delete_is_idempotent_second_call_returns_404(self, tmp_path):
        client = _client(tmp_path)
        pid = _upload_project(client)
        client.delete(f"/projects/{pid}")
        resp = client.delete(f"/projects/{pid}")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /projects/{id}/overrides
# ---------------------------------------------------------------------------

class TestGetProjectOverrides:
    def test_get_overrides_no_overrides_returns_404(self, tmp_path):
        client = _client(tmp_path)
        pid = _upload_project(client)
        resp = client.get(f"/projects/{pid}/overrides")
        assert resp.status_code == 404

    def test_get_overrides_after_patch_returns_200(self, tmp_path):
        client = _client(tmp_path)
        pid = _upload_project(client)
        client.patch(f"/projects/{pid}", json={"key_role": "Lead Dev"})
        resp = client.get(f"/projects/{pid}/overrides")
        assert resp.status_code == 200

    def test_get_overrides_contains_data_and_error_keys(self, tmp_path):
        client = _client(tmp_path)
        pid = _upload_project(client)
        client.patch(f"/projects/{pid}", json={"key_role": "QA"})
        body = client.get(f"/projects/{pid}/overrides").json()
        assert "data" in body
        assert "error" in body

    def test_get_overrides_reflects_patched_values(self, tmp_path):
        client = _client(tmp_path)
        pid = _upload_project(client)
        client.patch(
            f"/projects/{pid}",
            json={"key_role": "Backend", "portfolio_blurb": "Built APIs"},
        )
        data = client.get(f"/projects/{pid}/overrides").json()["data"]
        assert data["key_role"] == "Backend"
        assert data["portfolio_blurb"] == "Built APIs"

    def test_get_overrides_nonexistent_project_returns_404(self, tmp_path):
        client = _client(tmp_path)
        resp = client.get("/projects/no-such-id/overrides")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /projects/{id} — update overrides
# ---------------------------------------------------------------------------

class TestPatchProject:
    def test_patch_key_role_returns_200(self, tmp_path):
        client = _client(tmp_path)
        pid = _upload_project(client)
        resp = client.patch(f"/projects/{pid}", json={"key_role": "Fullstack"})
        assert resp.status_code == 200

    def test_patch_portfolio_blurb(self, tmp_path):
        client = _client(tmp_path)
        pid = _upload_project(client)
        resp = client.patch(f"/projects/{pid}", json={"portfolio_blurb": "Great project"})
        assert resp.status_code == 200

    def test_patch_resume_bullets(self, tmp_path):
        client = _client(tmp_path)
        pid = _upload_project(client)
        bullets = ["Implemented feature X", "Wrote tests"]
        resp = client.patch(f"/projects/{pid}", json={"resume_bullets": bullets})
        assert resp.status_code == 200

    def test_patch_multiple_fields_at_once(self, tmp_path):
        client = _client(tmp_path)
        pid = _upload_project(client)
        payload = {
            "key_role": "DevOps",
            "portfolio_blurb": "CI/CD pipeline",
            "selected": True,
            "rank": 1,
        }
        resp = client.patch(f"/projects/{pid}", json=payload)
        assert resp.status_code == 200

    def test_patch_nonexistent_project_returns_404(self, tmp_path):
        client = _client(tmp_path)
        resp = client.patch("/projects/ghost", json={"key_role": "Nobody"})
        assert resp.status_code == 404

    def test_patch_persists_across_requests(self, tmp_path):
        client = _client(tmp_path)
        pid = _upload_project(client)
        client.patch(f"/projects/{pid}", json={"key_role": "Architect"})
        overrides = client.get(f"/projects/{pid}/overrides").json()["data"]
        assert overrides["key_role"] == "Architect"

    def test_patch_selected_false(self, tmp_path):
        client = _client(tmp_path)
        pid = _upload_project(client)
        client.patch(f"/projects/{pid}", json={"selected": True})
        client.patch(f"/projects/{pid}", json={"selected": False})
        overrides = client.get(f"/projects/{pid}/overrides").json()["data"]
        assert overrides["selected"] is False
