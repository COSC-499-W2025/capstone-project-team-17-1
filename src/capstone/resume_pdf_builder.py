# capstone/resume_pdf_builder.py

from __future__ import annotations
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any
import textwrap


def _generate_markdown(resume: Dict[str, Any]) -> str:
    """
    Convert the resume JSON structure into Markdown that Pandoc
    will render into a clean, professional PDF.
    """
    company = resume.get("company", "")
    projects = resume.get("projects", [])
    skills = resume.get("skills", [])
    values = resume.get("values", [])
    work_style = resume.get("work_style", [])
    traits = resume.get("traits", [])

    md = []

    # Title
    md.append(f"# Tailored Resume — {company}\n")

    # Skills section
    md.append("## Skills")
    for s in skills:
        flags = []
        if s["in_required"]:
            flags.append("Required")
        if s["in_preferred"]:
            flags.append("Preferred")
        if s["in_company_profile"]:
            flags.append("Company Profile")
        flag_str = f" ({', '.join(flags)})" if flags else ""
        md.append(f"- **{s['name']}**{flag_str}")
    md.append("")

    # Values / Traits / Work Style
    if values:
        md.append("## Company Values Alignment")
        for v in values:
            md.append(f"- {v}")
        md.append("")

    if work_style:
        md.append("## Work Style Match")
        for w in work_style:
            md.append(f"- {w}")
        md.append("")

    if traits:
        md.append("## Traits")
        for t in traits:
            md.append(f"- {t}")
        md.append("")

    # Projects
    md.append("## Relevant Projects")
    for p in projects:
        md.append(f"### {p['project_id']}")
        md.append(f"- **Relevance Score:** {p['relevance_score']:.3f}")
        md.append(f"- **Bullet:** {p['resume_bullet']}")
        md.append("")
    md.append("")

    return "\n".join(md)


def build_pdf_with_pandoc(resume: Dict[str, Any], output_path: Path) -> Path:
    """
    Render PDF using Pandoc.
    Requires pandoc installed system-wide.
    """
    markdown_text = _generate_markdown(resume)

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
