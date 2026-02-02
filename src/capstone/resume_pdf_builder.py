# capstone/resume_pdf_builder.py

from __future__ import annotations
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any
import textwrap


def _generate_markdown(resume: Dict[str, Any]) -> str:
    lines = []

    # -----------------------
    # TITLE
    # -----------------------
    lines.append("# Tailored Resume\n")

    # -----------------------
    # SKILLS SECTION (FIXED)
    # -----------------------
    skills_set = set()

    project_context = resume.get("projectContext", {})

    for project in project_context.values():
        for skill in project.get("skills", []):
            if isinstance(skill, dict) and "skill" in skill:
                skills_set.add(skill["skill"])

    if skills_set:
        lines.append("## Skills\n")
        lines.append(", ".join(sorted(skills_set)))
        lines.append("")

    # -----------------------
    # PROJECTS SECTION
    # -----------------------
    lines.append("## Projects\n")

    for section in resume.get("sections", []):
        if section.get("name") != "projects":
            continue

        for item in section.get("items", []):
            title = item.get("title", "Untitled Project")
            summary = item.get("entrySummary") or item.get("entryBody", "")

            lines.append(f"### {title}")
            lines.append(summary.strip())
            lines.append("")

    return "\n".join(lines)



from pathlib import Path

def build_pdf_with_pandoc(resume: Dict[str, Any], output_path: Path) -> Path:
    """
    Render PDF using Pandoc.
    Requires pandoc installed system-wide.
    """

    # 🔒 DEFENSIVE FIX: normalize path
    output_path = Path(output_path)


    with tempfile.TemporaryDirectory() as tmpdir:
        md_path = Path(tmpdir) / "resume.md"
        pdf_path = Path(tmpdir) / "resume.pdf"
        md_path.write_text(markdown_text, encoding="utf-8")

        try:
            subprocess.run(
                ["pandoc", md_path, "-o", pdf_path, "--pdf-engine=wkhtmltopdf"],
                check=True
            )
        except FileNotFoundError:
            raise RuntimeError(
                "Pandoc is not installed. Install it from https://pandoc.org"
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_bytes = pdf_path.read_bytes()
        output_path.write_bytes(output_bytes)

        return output_path
