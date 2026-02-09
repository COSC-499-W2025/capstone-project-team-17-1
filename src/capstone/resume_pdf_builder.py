# capstone/resume_pdf_builder.py

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable


def _latex_escape(text: str) -> str:
    mapping = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    escaped = "".join(mapping.get(ch, ch) for ch in text)
    return escaped.replace("\n", " ")


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    return _latex_escape(str(value))


def _iter_project_items(resume: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    for section in resume.get("sections", []) or []:
        if section.get("name") != "projects":
            continue
        for item in section.get("items", []) or []:
            if isinstance(item, dict):
                yield item


def _generate_markdown(resume: Dict[str, Any]) -> str:
    lines = []
    lines.append("# Tailored Resume\n")

    skills_set = set()
    project_context = resume.get("projectContext", {}) or {}
    for project in project_context.values():
        if not isinstance(project, dict):
            continue
        for skill in project.get("skills", []) or []:
            if isinstance(skill, dict) and skill.get("skill"):
                skills_set.add(str(skill["skill"]))
            elif isinstance(skill, str) and skill.strip():
                skills_set.add(skill.strip())

    if skills_set:
        lines.append("## Skills\n")
        lines.append(", ".join(sorted(skills_set)))
        lines.append("")

    lines.append("## Projects\n")
    for item in _iter_project_items(resume):
        title = item.get("title", "Untitled Project")
        summary = item.get("entrySummary") or item.get("entryBody") or item.get("excerpt") or ""
        lines.append(f"### {title}")
        lines.append(str(summary).strip())
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def _generate_latex(resume: Dict[str, Any]) -> str:
    lines = [
        r"\documentclass[11pt]{article}",
        r"\usepackage[margin=1in]{geometry}",
        r"\usepackage[T1]{fontenc}",
        r"\usepackage{lmodern}",
        r"\usepackage[hidelinks]{hyperref}",
        r"\setlength{\parindent}{0pt}",
        r"\setlength{\parskip}{6pt}",
        r"\begin{document}",
        r"\section*{Tailored Resume}",
    ]

    skills_set = set()
    project_context = resume.get("projectContext", {}) or {}
    for project in project_context.values():
        if not isinstance(project, dict):
            continue
        for skill in project.get("skills", []) or []:
            if isinstance(skill, dict) and skill.get("skill"):
                skills_set.add(str(skill["skill"]))
            elif isinstance(skill, str) and skill.strip():
                skills_set.add(skill.strip())

    if skills_set:
        lines.append(r"\subsection*{Skills}")
        lines.append(_safe_text(", ".join(sorted(skills_set))))

    lines.append(r"\subsection*{Projects}")
    for item in _iter_project_items(resume):
        title = _safe_text(item.get("title") or "Untitled Project")
        summary = item.get("entrySummary") or item.get("entryBody") or item.get("excerpt") or ""
        lines.append(r"\textbf{" + title + r"}\\")
        lines.append(_safe_text(summary))
        lines.append(r"\vspace{0.4em}")

    lines.append(r"\end{document}")
    return "\n".join(lines) + "\n"


def _pick_tex_engine() -> str | None:
    for engine in ("xelatex", "lualatex", "pdflatex"):
        if shutil.which(engine):
            return engine
    return None


def build_pdf_with_latex(resume: Dict[str, Any], output_path: Path) -> Path:
    """
    Render PDF by generating LaTeX directly and compiling with a local TeX engine.
    """
    output_path = Path(output_path)
    tex_source = _generate_latex(resume)
    engine = _pick_tex_engine()
    if not engine:
        raise RuntimeError("No LaTeX engine found. Install xelatex, lualatex, or pdflatex.")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        tex_path = tmp / "resume.tex"
        pdf_path = tmp / "resume.pdf"
        tex_path.write_text(tex_source, encoding="utf-8")

        proc = subprocess.run(
            [engine, "-interaction=nonstopmode", "-halt-on-error", tex_path.name],
            cwd=tmp,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0 or not pdf_path.exists():
            stderr_tail = (proc.stderr or "").strip().splitlines()[-20:]
            stdout_tail = (proc.stdout or "").strip().splitlines()[-20:]
            detail = "\n".join(stderr_tail or stdout_tail)
            raise RuntimeError(f"LaTeX compile failed using {engine}.\n{detail}".strip())

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(pdf_path.read_bytes())
        return output_path


def build_pdf_with_pandoc(resume: Dict[str, Any], output_path: Path) -> Path:
    """
    Legacy path kept for compatibility. Converts markdown to PDF with pandoc.
    """
    output_path = Path(output_path)
    markdown_text = _generate_markdown(resume)

    with tempfile.TemporaryDirectory() as tmpdir:
        md_path = Path(tmpdir) / "resume.md"
        pdf_path = Path(tmpdir) / "resume.pdf"
        md_path.write_text(markdown_text, encoding="utf-8")

        engine = _pick_tex_engine() or "pdflatex"
        try:
            subprocess.run(
                ["pandoc", md_path, "-o", pdf_path, f"--pdf-engine={engine}"],
                check=True,
            )
        except FileNotFoundError:
            raise RuntimeError("Pandoc is not installed. Install it from https://pandoc.org")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(pdf_path.read_bytes())
        return output_path
