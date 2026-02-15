import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from capstone.resume_pdf_builder import render_latex_from_template


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
