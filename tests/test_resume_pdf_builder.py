import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from capstone.resume_pdf_builder import _pick_bullets, _pick_tex_engine, render_latex_from_template


def test_render_latex_skips_placeholder_replacement_in_comments(tmp_path):
    template = tmp_path / "template.tex"
    template.write_text(
        "\n".join(
            [
                "% __CORE_SKILL_BLOCK__",
                r"\ResumeHeader{__FULL_NAME__}{__LOCATION__}{__EMAIL__}{__PHONE__}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    rendered = render_latex_from_template(
        resume={
            "fullName": "Alice",
            "location": "Kelowna, BC",
            "email": "alice@example.com",
            "phone": "123",
            "skills": ["Python"],
        },
        template_path=template,
    )

    assert "% __CORE_SKILL_BLOCK__" in rendered
    assert r"\SkillRow{Tools}{N/A}" not in rendered
    assert r"\ResumeHeader{Alice}{Kelowna, BC}{alice@example.com}{123}" in rendered


def test_render_latex_default_education_experience_labels(tmp_path):
    template = tmp_path / "template.tex"
    template.write_text(
        "\n".join(
            [
                "__EDUCATION_SECTION__",
                "__EXPERIENCE_SECTION__",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    rendered = render_latex_from_template(
        resume={
            "sections": [
                {"name": "education", "items": [{}]},
                {"name": "experience", "items": [{}]},
            ]
        },
        template_path=template,
    )

    assert r"\ResumeEntry{University}{Date}{Degree Program}{Location}" in rendered
    assert r"\ResumeEntry{Event}{Date}{Company}{Location}" in rendered
    assert r"\item Content..." in rendered


# ---------------------------------------------------------------------------
# _pick_bullets — content field fallback (added in refactoring)
# ---------------------------------------------------------------------------


def test_pick_bullets_returns_explicit_bullets_list():
    entry = {"bullets": ["Did A", "Did B"]}
    assert _pick_bullets(entry) == ["Did A", "Did B"]


def test_pick_bullets_skips_empty_bullets_falls_to_content():
    entry = {"bullets": [], "content": "Built the API layer."}
    result = _pick_bullets(entry)
    assert result == ["Built the API layer."]


def test_pick_bullets_uses_content_when_no_bullets():
    entry = {"content": "Implemented REST endpoints."}
    result = _pick_bullets(entry)
    assert result == ["Implemented REST endpoints."]


def test_pick_bullets_content_preferred_over_fallback():
    entry = {"content": "Real description."}
    result = _pick_bullets(entry, fallback="Implemented core features and improvements.")
    assert result == ["Real description."]
    assert "Implemented core features" not in " ".join(result)


def test_pick_bullets_fallback_used_when_no_content():
    entry = {}
    result = _pick_bullets(entry, fallback="Default bullet.")
    assert result == ["Default bullet."]


def test_pick_bullets_multiline_content_becomes_multiple_bullets():
    entry = {"content": "Line one.\nLine two.\nLine three."}
    result = _pick_bullets(entry)
    assert result == ["Line one.", "Line two.", "Line three."]


def test_pick_bullets_highlights_list_used_before_content():
    entry = {"highlights": ["Highlight A"], "content": "Should not appear"}
    result = _pick_bullets(entry)
    assert result == ["Highlight A"]


def test_pick_bullets_empty_entry_with_no_fallback_returns_empty():
    assert _pick_bullets({}) == []


def test_pick_tex_engine_prefers_tectonic():
    with patch("capstone.resume_pdf_builder.shutil.which") as which_mock:
        which_mock.side_effect = lambda name: "/usr/local/bin/tectonic" if name == "tectonic" else None
        assert _pick_tex_engine() == "tectonic"
