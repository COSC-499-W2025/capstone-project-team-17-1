# tests/test_resume_instant_preview.py
import sys
import types
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# Avoid importing the real capstone.cli (pulls UI/LLM deps).
dummy_cli = types.ModuleType("capstone.cli")
dummy_cli.main = lambda argv=None: 0
dummy_cli.prompt_project_metadata = lambda *args, **kwargs: {}
dummy_cli.pick_zip_file = lambda *args, **kwargs: ""
sys.modules["capstone.cli"] = dummy_cli

import main as app  # noqa: E402

# Reset dummy so other tests can import the real CLI module.
sys.modules.pop("capstone.cli", None)


def test_build_user_resume_preview_includes_sections_and_contrib():
    chosen_snapshots = [
        {
            "project_id": "demo-project",
            "snapshot": {
                "project_id": "demo-project",
                "project_name": "Demo Project",
                "skills": [{"skill": "python"}, {"skill": "pandas"}],
                "frameworks": ["fastapi"],
            },
            "created_at": "2026-02-01T00:00:00Z",
        }
    ]
    contribution_map = {
        "demo-project": {
            "commits": 5,
            "pull_requests": 2,
            "issues": 1,
            "reviews": 3,
            "score": 10.0,
        }
    }

    preview = app._build_user_resume_preview(
        selected_username="alice",
        chosen_snapshots=chosen_snapshots,
        contribution_map=contribution_map,
    )

    sections = {section.get("name") for section in preview.get("sections", [])}
    assert "summary" in sections
    assert "projects" in sections
    assert "skills" in sections

    projects = [
        item
        for section in preview.get("sections", [])
        if section.get("name") == "projects"
        for item in section.get("items", [])
    ]
    assert len(projects) == 1
    proj = projects[0]
    assert "demo-project" in proj.get("projectIds", [])
    # Contribution line should be part of excerpt
    assert "commits" in proj.get("excerpt", "").lower()
    assert "5" in proj.get("excerpt", "")

    skills_section = [
        section for section in preview.get("sections", []) if section.get("name") == "skills"
    ]
    assert skills_section and "python" in skills_section[0].get("items", [])[0].get("excerpt", "")


class _MiniCursor:
    def __init__(self, rows):
        self._rows = rows

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return list(self._rows)


class _MiniConn:
    def __init__(self, item_rows_by_section):
        self.item_rows_by_section = item_rows_by_section

    def execute(self, sql, params=()):
        normalized = " ".join(sql.split()).lower()
        if "select metadata_json from resume_items" in normalized:
            return _MiniCursor([])
        if "select title, subtitle, start_date, end_date, location, content, is_enabled from resume_items" in normalized:
            section_id = params[0]
            return _MiniCursor(self.item_rows_by_section.get(section_id, []))
        raise AssertionError(f"Unexpected SQL in test double: {sql}")


def test_build_resume_preview_filters_disabled_sections_and_items():
    sections = [
        {"id": "sec_summary", "key": "summary", "label": "Summary", "sort_order": 1, "is_enabled": 0},
        {"id": "sec_experience", "key": "experience", "label": "Experience", "sort_order": 2, "is_enabled": 1},
        {"id": "sec_custom_on", "key": "custom_on", "label": "Custom On", "sort_order": 3, "is_enabled": 1},
        {"id": "sec_custom_off", "key": "custom_off", "label": "Custom Off", "sort_order": 4, "is_enabled": 0},
    ]
    item_rows_by_section = {
        "sec_summary": [("Summary", "", "", "", "", "should-not-render", 1)],
        "sec_experience": [
            ("Role A", "Company A", "2024", "2025", "Vancouver", "keep", 1),
            ("Role B", "Company B", "2023", "2024", "Kelowna", "drop", 0),
        ],
    }
    custom_items_by_section = {
        "sec_custom_on": [
            {
                "id": "i1",
                "title": "Enabled Custom Item",
                "subtitle": "",
                "start_date": "",
                "end_date": "",
                "location": "",
                "content": "visible",
                "sort_order": 1,
                "is_enabled": 1,
            }
        ],
        "sec_custom_off": [
            {
                "id": "i2",
                "title": "Disabled Custom Item",
                "subtitle": "",
                "start_date": "",
                "end_date": "",
                "location": "",
                "content": "hidden",
                "sort_order": 1,
                "is_enabled": 1,
            }
        ],
    }
    conn = _MiniConn(item_rows_by_section)

    with (
        patch.object(app, "get_user_profile", return_value={"full_name": "Alice"}),
        patch.object(app, "_list_resume_sections", return_value=sections),
        patch.object(
            app,
            "_list_resume_section_items",
            side_effect=lambda _conn, section_id: custom_items_by_section.get(section_id, []),
        ),
    ):
        payload = app._build_resume_preview_from_modular_resume(
            conn,
            resume_id="r1",
            user_id=1,
        )

    names = [sec.get("name") for sec in payload.get("sections", [])]
    assert "summary" not in names
    assert "experience" in names
    assert "custom::custom_on" in names
    assert "custom::custom_off" not in names

    experience_section = next(sec for sec in payload["sections"] if sec.get("name") == "experience")
    assert len(experience_section.get("items", [])) == 1
    assert experience_section["items"][0]["title"] == "Role A"
