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
import tempfile
import unittest
import uuid
import zipfile
from pathlib import Path

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


# ---------------------------------------------------------------------------
# Base test class — handles isolation and teardown
# ---------------------------------------------------------------------------

class _ProjectsAPIBase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        storage.BASE_DIR = Path(self._tmpdir.name)
        app = create_app(db_dir=self._tmpdir.name, auth_token=None)
        self.client = TestClient(app)

    def tearDown(self) -> None:
        storage.close_db()
        storage.BASE_DIR = _ORIGINAL_BASE_DIR
        self._tmpdir.cleanup()


# ---------------------------------------------------------------------------
# GET /projects — list
# ---------------------------------------------------------------------------

class TestListProjects(_ProjectsAPIBase):
    def test_list_empty_returns_zero_count(self) -> None:
        resp = self.client.get("/projects")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["count"], 0)
        self.assertEqual(body["projects"], [])

    def test_list_after_upload_returns_one_project(self) -> None:
        _upload_project(self.client)
        resp = self.client.get("/projects")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["count"], 1)
        self.assertEqual(len(body["projects"]), 1)

    def test_list_project_has_required_fields(self) -> None:
        _upload_project(self.client)
        resp = self.client.get("/projects")
        project = resp.json()["projects"][0]
        for field in ("project_id", "filename", "file_id", "hash", "created_at", "size_bytes"):
            self.assertIn(field, project, f"Missing field: {field}")

    def test_list_multiple_uploads_returns_all(self) -> None:
        for i in range(3):
            name, data, mime = _make_zip(f"proj{i}.zip", unique_tag=str(i))
            pid = f"multi-proj-{i}-{uuid.uuid4().hex[:6]}"
            self.client.post(f"/projects/upload?project_id={pid}", files={"file": (name, data, mime)})
        resp = self.client.get("/projects")
        self.assertEqual(resp.json()["count"], 3)

    def test_list_filename_matches_uploaded_name(self) -> None:
        name, data, mime = _make_zip("myproject.zip")
        pid = f"name-test-{uuid.uuid4().hex[:6]}"
        self.client.post(f"/projects/upload?project_id={pid}", files={"file": (name, data, mime)})
        resp = self.client.get("/projects")
        self.assertEqual(resp.json()["projects"][0]["filename"], "myproject.zip")


# ---------------------------------------------------------------------------
# GET /projects/{id} — single project
# ---------------------------------------------------------------------------

class TestGetProject(_ProjectsAPIBase):
    def test_get_existing_project_returns_200(self) -> None:
        pid = _upload_project(self.client)
        resp = self.client.get(f"/projects/{pid}")
        self.assertEqual(resp.status_code, 200)

    def test_get_existing_project_has_correct_id(self) -> None:
        pid = _upload_project(self.client)
        resp = self.client.get(f"/projects/{pid}")
        self.assertEqual(resp.json()["project_id"], pid)

    def test_get_existing_project_has_required_fields(self) -> None:
        pid = _upload_project(self.client)
        body = self.client.get(f"/projects/{pid}").json()
        for field in ("project_id", "filename", "file_id", "hash", "created_at", "size_bytes"):
            self.assertIn(field, body, f"Missing field: {field}")

    def test_get_nonexistent_project_returns_404(self) -> None:
        resp = self.client.get("/projects/does-not-exist")
        self.assertEqual(resp.status_code, 404)

    def test_get_project_matches_list_entry(self) -> None:
        pid = _upload_project(self.client)
        single = self.client.get(f"/projects/{pid}").json()
        listed = self.client.get("/projects").json()["projects"][0]
        self.assertEqual(single["project_id"], listed["project_id"])
        self.assertEqual(single["hash"], listed["hash"])


# ---------------------------------------------------------------------------
# DELETE /projects/{id}
# ---------------------------------------------------------------------------

class TestDeleteProject(_ProjectsAPIBase):
    def test_delete_existing_project_returns_200(self) -> None:
        pid = _upload_project(self.client)
        resp = self.client.delete(f"/projects/{pid}")
        self.assertEqual(resp.status_code, 200)

    def test_delete_response_body_has_deleted_flag(self) -> None:
        pid = _upload_project(self.client)
        body = self.client.delete(f"/projects/{pid}").json()
        self.assertTrue(body["data"]["deleted"])
        self.assertEqual(body["data"]["project_id"], pid)
        self.assertIsNone(body["error"])

    def test_delete_removes_project_from_list(self) -> None:
        pid = _upload_project(self.client)
        self.client.delete(f"/projects/{pid}")
        resp = self.client.get("/projects")
        self.assertEqual(resp.json()["count"], 0)

    def test_get_after_delete_returns_404(self) -> None:
        pid = _upload_project(self.client)
        self.client.delete(f"/projects/{pid}")
        resp = self.client.get(f"/projects/{pid}")
        self.assertEqual(resp.status_code, 404)

    def test_delete_nonexistent_project_returns_404(self) -> None:
        resp = self.client.delete("/projects/ghost-id")
        self.assertEqual(resp.status_code, 404)

    def test_delete_only_removes_target_project(self) -> None:
        pid1 = _upload_project(self.client)
        pid2 = _upload_project(self.client)
        self.client.delete(f"/projects/{pid1}")
        remaining = self.client.get("/projects").json()
        self.assertEqual(remaining["count"], 1)
        self.assertEqual(remaining["projects"][0]["project_id"], pid2)

    def test_delete_is_idempotent_second_call_returns_404(self) -> None:
        pid = _upload_project(self.client)
        self.client.delete(f"/projects/{pid}")
        resp = self.client.delete(f"/projects/{pid}")
        self.assertEqual(resp.status_code, 404)


# ---------------------------------------------------------------------------
# GET /projects/{id}/overrides
# ---------------------------------------------------------------------------

class TestGetProjectOverrides(_ProjectsAPIBase):
    def test_get_overrides_no_overrides_returns_404(self) -> None:
        pid = _upload_project(self.client)
        resp = self.client.get(f"/projects/{pid}/overrides")
        self.assertEqual(resp.status_code, 404)

    def test_get_overrides_after_patch_returns_200(self) -> None:
        pid = _upload_project(self.client)
        self.client.patch(f"/projects/{pid}", json={"key_role": "Lead Dev"})
        resp = self.client.get(f"/projects/{pid}/overrides")
        self.assertEqual(resp.status_code, 200)

    def test_get_overrides_contains_data_and_error_keys(self) -> None:
        pid = _upload_project(self.client)
        self.client.patch(f"/projects/{pid}", json={"key_role": "QA"})
        body = self.client.get(f"/projects/{pid}/overrides").json()
        self.assertIn("data", body)
        self.assertIn("error", body)

    def test_get_overrides_reflects_patched_values(self) -> None:
        pid = _upload_project(self.client)
        self.client.patch(
            f"/projects/{pid}",
            json={"key_role": "Backend", "portfolio_blurb": "Built APIs"},
        )
        data = self.client.get(f"/projects/{pid}/overrides").json()["data"]
        self.assertEqual(data["key_role"], "Backend")
        self.assertEqual(data["portfolio_blurb"], "Built APIs")

    def test_get_overrides_nonexistent_project_returns_404(self) -> None:
        resp = self.client.get("/projects/no-such-id/overrides")
        self.assertEqual(resp.status_code, 404)


# ---------------------------------------------------------------------------
# PATCH /projects/{id} — update overrides
# ---------------------------------------------------------------------------

class TestPatchProject(_ProjectsAPIBase):
    def test_patch_key_role_returns_200(self) -> None:
        pid = _upload_project(self.client)
        resp = self.client.patch(f"/projects/{pid}", json={"key_role": "Fullstack"})
        self.assertEqual(resp.status_code, 200)

    def test_patch_portfolio_blurb(self) -> None:
        pid = _upload_project(self.client)
        resp = self.client.patch(f"/projects/{pid}", json={"portfolio_blurb": "Great project"})
        self.assertEqual(resp.status_code, 200)

    def test_patch_resume_bullets(self) -> None:
        pid = _upload_project(self.client)
        bullets = ["Implemented feature X", "Wrote tests"]
        resp = self.client.patch(f"/projects/{pid}", json={"resume_bullets": bullets})
        self.assertEqual(resp.status_code, 200)

    def test_patch_multiple_fields_at_once(self) -> None:
        pid = _upload_project(self.client)
        payload = {
            "key_role": "DevOps",
            "portfolio_blurb": "CI/CD pipeline",
            "selected": True,
            "rank": 1,
        }
        resp = self.client.patch(f"/projects/{pid}", json=payload)
        self.assertEqual(resp.status_code, 200)

    def test_patch_nonexistent_project_returns_404(self) -> None:
        resp = self.client.patch("/projects/ghost", json={"key_role": "Nobody"})
        self.assertEqual(resp.status_code, 404)

    def test_patch_persists_across_requests(self) -> None:
        pid = _upload_project(self.client)
        self.client.patch(f"/projects/{pid}", json={"key_role": "Architect"})
        overrides = self.client.get(f"/projects/{pid}/overrides").json()["data"]
        self.assertEqual(overrides["key_role"], "Architect")

    def test_patch_selected_false(self) -> None:
        pid = _upload_project(self.client)
        self.client.patch(f"/projects/{pid}", json={"selected": True})
        self.client.patch(f"/projects/{pid}", json={"selected": False})
        overrides = self.client.get(f"/projects/{pid}/overrides").json()["data"]
        self.assertFalse(overrides["selected"])


if __name__ == "__main__":
    unittest.main()
