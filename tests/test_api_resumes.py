"""
Integration tests for the new /resumes API (routes/resumes.py).

Covers: resume CRUD, section CRUD, item CRUD, export (json/markdown),
and auto-generate from a user's linked projects.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pytest

fastapi = pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from capstone import storage
from capstone.api.server import get_app_for_tests


# ---------------------------------------------------------------------------
# Shared setUp helper
# ---------------------------------------------------------------------------


class _ResumeAPIBase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmpdir.name)
        self.app = get_app_for_tests(db_dir=str(self.tmp_path))
        self.client = TestClient(self.app)
        self.addCleanup(self._tmpdir.cleanup)
        self.addCleanup(storage.close_db)

        # Seed a user so all tests have a valid user_id
        conn = storage.open_db(self.tmp_path)
        self.user_id = storage.upsert_contributor(conn, "testuser", email="test@example.com")

    # ------------------------------------------------------------------ helpers

    def _create_resume(self, title: str = "My Resume") -> dict:
        r = self.client.post("/resumes", json={"user_id": self.user_id, "title": title})
        self.assertEqual(r.status_code, 201, r.text)
        return r.json()["data"]

    def _create_section(self, resume_id: str, key: str = "experience", label: str = "Experience") -> dict:
        r = self.client.post(
            f"/resumes/{resume_id}/sections",
            json={"key": key, "label": label},
        )
        self.assertEqual(r.status_code, 201, r.text)
        return r.json()["data"]

    def _create_item(self, resume_id: str, section_id: str, title: str = "Job Title") -> dict:
        r = self.client.post(
            f"/resumes/{resume_id}/sections/{section_id}/items",
            json={"title": title, "content": "Did some work."},
        )
        self.assertEqual(r.status_code, 201, r.text)
        return r.json()["data"]


# ---------------------------------------------------------------------------
# Resume CRUD
# ---------------------------------------------------------------------------


class ResumeCRUDTestCase(_ResumeAPIBase):

    def test_create_resume_returns_201_with_id(self):
        data = self._create_resume("Test Resume")
        self.assertIsNotNone(data.get("id"))
        self.assertEqual(data["title"], "Test Resume")
        self.assertEqual(data["user_id"], self.user_id)

    def test_create_resume_missing_user_id_returns_400(self):
        r = self.client.post("/resumes", json={"title": "No User"})
        self.assertEqual(r.status_code, 400)

    def test_get_resume_returns_200(self):
        created = self._create_resume()
        r = self.client.get(f"/resumes/{created['id']}")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["data"]["id"], created["id"])

    def test_get_nonexistent_resume_returns_404(self):
        r = self.client.get("/resumes/does-not-exist")
        self.assertEqual(r.status_code, 404)

    def test_list_resumes_for_user(self):
        self._create_resume("Resume A")
        self._create_resume("Resume B")
        r = self.client.get(f"/resumes?user_id={self.user_id}")
        self.assertEqual(r.status_code, 200)
        data = r.json()["data"]
        titles = [d["title"] for d in data]
        self.assertIn("Resume A", titles)
        self.assertIn("Resume B", titles)

    def test_update_resume_title(self):
        created = self._create_resume("Original Title")
        r = self.client.patch(f"/resumes/{created['id']}", json={"title": "Updated Title"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["data"]["title"], "Updated Title")

    def test_update_resume_target_role(self):
        created = self._create_resume()
        r = self.client.patch(f"/resumes/{created['id']}", json={"target_role": "Backend Engineer"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["data"]["target_role"], "Backend Engineer")

    def test_update_nonexistent_resume_returns_404(self):
        r = self.client.patch("/resumes/ghost", json={"title": "X"})
        self.assertEqual(r.status_code, 404)

    def test_delete_resume_then_404(self):
        created = self._create_resume()
        resume_id = created["id"]
        r = self.client.delete(f"/resumes/{resume_id}")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["data"]["deleted"])
        r2 = self.client.get(f"/resumes/{resume_id}")
        self.assertEqual(r2.status_code, 404)

    def test_delete_nonexistent_resume_returns_404(self):
        r = self.client.delete("/resumes/ghost")
        self.assertEqual(r.status_code, 404)


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


class ResumeExportTestCase(_ResumeAPIBase):

    def test_export_json(self):
        created = self._create_resume("Export Me")
        r = self.client.get(f"/resumes/{created['id']}/export?format=json")
        self.assertEqual(r.status_code, 200)
        data = r.json()["data"]
        self.assertEqual(data["title"], "Export Me")

    def test_export_markdown_contains_title(self):
        created = self._create_resume("Markdown Resume")
        r = self.client.get(f"/resumes/{created['id']}/export?format=markdown")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Markdown Resume", r.text)

    def test_export_invalid_format_returns_400(self):
        created = self._create_resume()
        r = self.client.get(f"/resumes/{created['id']}/export?format=docx")
        self.assertEqual(r.status_code, 400)

    def test_export_nonexistent_resume_returns_404(self):
        r = self.client.get("/resumes/ghost/export?format=json")
        self.assertEqual(r.status_code, 404)


# ---------------------------------------------------------------------------
# Section CRUD
# ---------------------------------------------------------------------------


class ResumeSectionTestCase(_ResumeAPIBase):

    def test_create_section_returns_201(self):
        resume = self._create_resume()
        section = self._create_section(resume["id"], key="skills", label="Skills")
        self.assertIsNotNone(section.get("id"))
        self.assertEqual(section["label"], "Skills")

    def test_create_section_missing_key_returns_400(self):
        resume = self._create_resume()
        r = self.client.post(f"/resumes/{resume['id']}/sections", json={"label": "No Key"})
        self.assertEqual(r.status_code, 400)

    def test_create_section_missing_label_returns_400(self):
        resume = self._create_resume()
        r = self.client.post(f"/resumes/{resume['id']}/sections", json={"key": "skills"})
        self.assertEqual(r.status_code, 400)

    def test_list_sections(self):
        resume = self._create_resume()
        self._create_section(resume["id"], key="experience", label="Experience")
        self._create_section(resume["id"], key="education", label="Education")
        r = self.client.get(f"/resumes/{resume['id']}/sections")
        self.assertEqual(r.status_code, 200)
        labels = [s["label"] for s in r.json()["data"]]
        self.assertIn("Experience", labels)
        self.assertIn("Education", labels)

    def test_update_section_label(self):
        resume = self._create_resume()
        section = self._create_section(resume["id"])
        r = self.client.patch(
            f"/resumes/{resume['id']}/sections/{section['id']}",
            json={"label": "Work Experience"},
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["data"]["label"], "Work Experience")

    def test_disable_section(self):
        resume = self._create_resume()
        section = self._create_section(resume["id"])
        r = self.client.patch(
            f"/resumes/{resume['id']}/sections/{section['id']}",
            json={"is_enabled": False},
        )
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.json()["data"]["is_enabled"])

    def test_update_nonexistent_section_returns_404(self):
        resume = self._create_resume()
        r = self.client.patch(f"/resumes/{resume['id']}/sections/ghost", json={"label": "X"})
        self.assertEqual(r.status_code, 404)

    def test_delete_section(self):
        resume = self._create_resume()
        section = self._create_section(resume["id"])
        r = self.client.delete(f"/resumes/{resume['id']}/sections/{section['id']}")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["data"]["deleted"])

    def test_delete_nonexistent_section_returns_404(self):
        resume = self._create_resume()
        r = self.client.delete(f"/resumes/{resume['id']}/sections/ghost")
        self.assertEqual(r.status_code, 404)

    def test_reorder_sections(self):
        resume = self._create_resume()
        s1 = self._create_section(resume["id"], key="s1", label="First")
        s2 = self._create_section(resume["id"], key="s2", label="Second")
        # Reverse order
        r = self.client.post(
            f"/resumes/{resume['id']}/sections/reorder",
            json={"ids": [s2["id"], s1["id"]]},
        )
        self.assertEqual(r.status_code, 200)
        ordered_ids = [s["id"] for s in r.json()["data"]]
        self.assertEqual(ordered_ids.index(s2["id"]), 0)
        self.assertLess(ordered_ids.index(s2["id"]), ordered_ids.index(s1["id"]))


# ---------------------------------------------------------------------------
# Item CRUD
# ---------------------------------------------------------------------------


class ResumeItemTestCase(_ResumeAPIBase):

    def setUp(self) -> None:
        super().setUp()
        self.resume = self._create_resume()
        self.section = self._create_section(self.resume["id"])

    def test_create_item_returns_201(self):
        item = self._create_item(self.resume["id"], self.section["id"], "Software Engineer")
        self.assertIsNotNone(item.get("id"))
        self.assertEqual(item["title"], "Software Engineer")

    def test_create_item_with_bullets(self):
        r = self.client.post(
            f"/resumes/{self.resume['id']}/sections/{self.section['id']}/items",
            json={
                "title": "Dev",
                "bullets": ["Built APIs", "Wrote tests"],
            },
        )
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()["data"]["bullets"], ["Built APIs", "Wrote tests"])

    def test_create_item_with_metadata(self):
        r = self.client.post(
            f"/resumes/{self.resume['id']}/sections/{self.section['id']}/items",
            json={"title": "Project", "metadata": {"project_id": "abc123"}},
        )
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()["data"]["metadata"]["project_id"], "abc123")

    def test_create_item_invalid_bullets_type_returns_400(self):
        r = self.client.post(
            f"/resumes/{self.resume['id']}/sections/{self.section['id']}/items",
            json={"title": "X", "bullets": "not a list"},
        )
        self.assertEqual(r.status_code, 400)

    def test_list_items(self):
        self._create_item(self.resume["id"], self.section["id"], "Item A")
        self._create_item(self.resume["id"], self.section["id"], "Item B")
        r = self.client.get(
            f"/resumes/{self.resume['id']}/sections/{self.section['id']}/items"
        )
        self.assertEqual(r.status_code, 200)
        titles = [i["title"] for i in r.json()["data"]]
        self.assertIn("Item A", titles)
        self.assertIn("Item B", titles)

    def test_update_item_content(self):
        item = self._create_item(self.resume["id"], self.section["id"])
        r = self.client.patch(
            f"/resumes/{self.resume['id']}/sections/{self.section['id']}/items/{item['id']}",
            json={"content": "Updated content."},
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["data"]["content"], "Updated content.")

    def test_disable_item(self):
        item = self._create_item(self.resume["id"], self.section["id"])
        r = self.client.patch(
            f"/resumes/{self.resume['id']}/sections/{self.section['id']}/items/{item['id']}",
            json={"is_enabled": False},
        )
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.json()["data"]["is_enabled"])

    def test_update_nonexistent_item_returns_404(self):
        r = self.client.patch(
            f"/resumes/{self.resume['id']}/sections/{self.section['id']}/items/ghost",
            json={"title": "X"},
        )
        self.assertEqual(r.status_code, 404)

    def test_delete_item(self):
        item = self._create_item(self.resume["id"], self.section["id"])
        r = self.client.delete(
            f"/resumes/{self.resume['id']}/sections/{self.section['id']}/items/{item['id']}"
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["data"]["deleted"])

    def test_delete_nonexistent_item_returns_404(self):
        r = self.client.delete(
            f"/resumes/{self.resume['id']}/sections/{self.section['id']}/items/ghost"
        )
        self.assertEqual(r.status_code, 404)

    def test_reorder_items(self):
        i1 = self._create_item(self.resume["id"], self.section["id"], "First")
        i2 = self._create_item(self.resume["id"], self.section["id"], "Second")
        r = self.client.post(
            f"/resumes/{self.resume['id']}/sections/{self.section['id']}/items/reorder",
            json={"ids": [i2["id"], i1["id"]]},
        )
        self.assertEqual(r.status_code, 200)
        ordered_ids = [i["id"] for i in r.json()["data"]]
        self.assertLess(ordered_ids.index(i2["id"]), ordered_ids.index(i1["id"]))


# ---------------------------------------------------------------------------
# section_count in list response
# ---------------------------------------------------------------------------


class ResumeSectionCountTestCase(_ResumeAPIBase):

    def test_list_resumes_includes_section_count(self):
        resume = self._create_resume("Counted Resume")
        self._create_section(resume["id"], key="experience", label="Experience")
        self._create_section(resume["id"], key="education", label="Education")
        r = self.client.get(f"/resumes?user_id={self.user_id}")
        self.assertEqual(r.status_code, 200)
        found = next(d for d in r.json()["data"] if d["id"] == resume["id"])
        self.assertEqual(found["section_count"], 2)

    def test_list_resumes_section_count_zero_for_empty_resume(self):
        resume = self._create_resume("Empty Resume")
        r = self.client.get(f"/resumes?user_id={self.user_id}")
        self.assertEqual(r.status_code, 200)
        found = next(d for d in r.json()["data"] if d["id"] == resume["id"])
        self.assertEqual(found["section_count"], 0)

    def test_list_resumes_section_count_excludes_disabled_sections(self):
        resume = self._create_resume("Mixed Resume")
        s1 = self._create_section(resume["id"], key="experience", label="Experience")
        s2 = self._create_section(resume["id"], key="education", label="Education")
        # Disable one section
        self.client.patch(
            f"/resumes/{resume['id']}/sections/{s2['id']}",
            json={"is_enabled": False},
        )
        r = self.client.get(f"/resumes?user_id={self.user_id}")
        self.assertEqual(r.status_code, 200)
        found = next(d for d in r.json()["data"] if d["id"] == resume["id"])
        # Only the enabled section should be counted
        self.assertEqual(found["section_count"], 1)


# ---------------------------------------------------------------------------
# Auto-generate resume from user's projects
# ---------------------------------------------------------------------------


class ResumeGenerateTestCase(_ResumeAPIBase):

    def setUp(self) -> None:
        super().setUp()
        # Inject a fake session so generate endpoint can resolve owner_id from Bearer token
        from capstone.api.routes.auth import _SESSIONS
        _SESSIONS["test-token"] = {
            "contributor_id": self.user_id,
            "user": {"username": "testuser", "email": "test@example.com"},
        }
        self.addCleanup(lambda: _SESSIONS.pop("test-token", None))
        self.auth_headers = {"Authorization": "Bearer test-token"}

    def _seed_project_for_user(self, project_id: str) -> None:
        self._seed_project_for_user_id(self.user_id, project_id)

    def _seed_project_for_user_id(self, user_id: int, project_id: str) -> None:
        conn = storage.open_db(self.tmp_path)
        snapshot = {
            "project_name": "Cool Project",
            "languages": {"Python": 5, "SQL": 2},
            "frameworks": ["fastapi"],
            "skills": [{"skill": "pytest"}],
            "collaboration": {"classification": "collaborative"},
            "file_summary": {"file_count": 10, "total_bytes": 5000, "active_days": 30},
        }
        storage.store_analysis_snapshot(
            conn,
            project_id=project_id,
            classification="collaborative",
            primary_contributor="testuser",
            snapshot=snapshot,
        )
        storage.link_user_to_project(conn, user_id, project_id, contributor_name="testuser")

    # --- fixed existing tests (now pass Bearer token) ---

    def test_generate_creates_resume_with_sections(self):
        self._seed_project_for_user("gen-proj-1")
        r = self.client.post("/resumes/generate", json={}, headers=self.auth_headers)
        self.assertEqual(r.status_code, 201, r.text)
        data = r.json()["data"]
        self.assertIsNotNone(data.get("id"))
        section_keys = [s["key"] for s in (data.get("sections") or [])]
        self.assertTrue(len(section_keys) > 0)

    def test_generate_without_auth_returns_400(self):
        # No Bearer token → owner_id cannot be resolved → 400
        r = self.client.post("/resumes/generate", json={})
        self.assertEqual(r.status_code, 400)

    def test_generate_includes_skills_from_snapshot(self):
        self._seed_project_for_user("gen-proj-2")
        r = self.client.post("/resumes/generate", json={}, headers=self.auth_headers)
        self.assertEqual(r.status_code, 201, r.text)
        resume_json = json.dumps(r.json()["data"])
        self.assertTrue(
            any(skill in resume_json for skill in ["Python", "python", "fastapi", "pytest"]),
            "Expected at least one skill from the project snapshot in the generated resume",
        )

    def test_generate_create_new_flag_makes_fresh_resume(self):
        self._seed_project_for_user("gen-proj-3")
        r1 = self.client.post("/resumes/generate", json={}, headers=self.auth_headers)
        self.assertEqual(r1.status_code, 201)
        id1 = r1.json()["data"]["id"]

        r2 = self.client.post(
            "/resumes/generate",
            json={"create_new": True, "resume_title": "New Resume"},
            headers=self.auth_headers,
        )
        self.assertEqual(r2.status_code, 201)
        id2 = r2.json()["data"]["id"]
        self.assertNotEqual(id1, id2)

    # --- new tests for owner_id / data_user_id separation ---

    def test_generate_without_user_id_defaults_to_session_owner(self):
        # Omitting user_id → data_user_id defaults to owner; resume stored under owner
        self._seed_project_for_user("gen-proj-self")
        r = self.client.post("/resumes/generate", json={}, headers=self.auth_headers)
        self.assertEqual(r.status_code, 201, r.text)
        self.assertEqual(r.json()["data"]["user_id"], self.user_id)

    def test_generate_for_other_contributor_owned_by_session_user(self):
        # user_id in body = other contributor → resume.user_id must still equal session owner
        conn = storage.open_db(self.tmp_path)
        other_id = storage.upsert_contributor(conn, "otheruser", email="other@example.com")
        self._seed_project_for_user_id(other_id, "other-proj-1")

        r = self.client.post(
            "/resumes/generate",
            json={"user_id": other_id},
            headers=self.auth_headers,
        )
        self.assertEqual(r.status_code, 201, r.text)
        self.assertEqual(
            r.json()["data"]["user_id"],
            self.user_id,
            "Resume must be owned by the session user, not the data contributor",
        )

    def test_generate_for_other_not_in_target_users_resume_list(self):
        # After generating for another user, their resume list should remain empty
        conn = storage.open_db(self.tmp_path)
        other_id = storage.upsert_contributor(conn, "otheruser2", email="other2@example.com")
        self._seed_project_for_user_id(other_id, "other-proj-2")

        self.client.post(
            "/resumes/generate",
            json={"user_id": other_id},
            headers=self.auth_headers,
        )

        r = self.client.get(f"/resumes?user_id={other_id}")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            len(r.json()["data"]),
            0,
            "Target contributor's resume list must stay empty when someone else generated for them",
        )


if __name__ == "__main__":
    unittest.main()
