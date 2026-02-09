from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List


def _generate_markdown(entries: List[dict], title: str = "Portfolio Showcase") -> str:
    lines: List[str] = []
    lines.append(f"# {title}\n")

    for item in entries:
        name = item.get("name") or item.get("project_id") or "Untitled Project"
        summary = (item.get("summary") or "").strip()
        project_id = item.get("project_id") or ""
        source = item.get("source") or ""

        lines.append(f"## {name}")
        if project_id:
            lines.append(f"Project ID: {project_id}")
        if source:
            lines.append(f"Source: {source}")
        if summary:
            lines.append("")
            lines.append(summary)
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def _latex_header() -> str:
    # Minimal resume-like styling
    return "\n".join(
        [
            r"\usepackage{geometry}",
            r"\geometry{margin=1in}",
            r"\usepackage{lmodern}",
            r"\usepackage{titlesec}",
            r"\titleformat{\section}{\Large\bfseries}{}{0em}{}",
            r"\titleformat{\subsection}{\large\bfseries}{}{0em}{}",
            r"\titlespacing*{\section}{0pt}{1.2em}{0.6em}",
            r"\titlespacing*{\subsection}{0pt}{0.8em}{0.4em}",
            r"\setlength{\parindent}{0pt}",
            r"\setlength{\parskip}{6pt}",
        ]
    )


def _pick_pdf_engine() -> str:
    # Prefer lightweight LaTeX
    if shutil.which("tectonic"):
        return "tectonic"
    if shutil.which("xelatex"):
        return "xelatex"
    if shutil.which("pdflatex"):
        return "pdflatex"
    return "tectonic"


def build_portfolio_pdf_with_pandoc(
    entries: List[dict],
    output_path: Path,
    *,
    title: str = "Portfolio Showcase",
) -> Path:
    """
    Render a LaTeX-based PDF using Pandoc.
    Requires pandoc + a LaTeX engine (tectonic/xelatex/pdflatex) installed system-wide.
    """

    output_path = Path(output_path)
    markdown_text = _generate_markdown(entries, title=title)

    with tempfile.TemporaryDirectory() as tmpdir:
        md_path = Path(tmpdir) / "portfolio.md"
        pdf_path = Path(tmpdir) / "portfolio.pdf"
        md_path.write_text(markdown_text, encoding="utf-8")

        engine = _pick_pdf_engine()
        # Write header
        header_path = Path(tmpdir) / "header.tex"
        header_path.write_text(_latex_header(), encoding="utf-8")
        try:
            subprocess.run(
                [
                    "pandoc",
                    md_path,
                    "-o",
                    pdf_path,
                    f"--pdf-engine={engine}",
                    "-V",
                    "fontsize=11pt",
                    "--include-in-header",
                    header_path,
                ],
                check=True,
            )
        except FileNotFoundError:
            raise RuntimeError(
                "Pandoc is not installed. Install it from https://pandoc.org"
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(pdf_path.read_bytes())
        return output_path
