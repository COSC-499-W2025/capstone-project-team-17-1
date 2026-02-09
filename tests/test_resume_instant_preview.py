# tests/test_resume_instant_preview.py
import sys
import types
from pathlib import Path

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
