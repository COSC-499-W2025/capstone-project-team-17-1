from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, List

def _latex_header() -> str:
    # Minimal resume-like styling
    return "\n".join(
        [
            r"\usepackage{geometry}",
            r"\geometry{margin=1in}",
            r"\usepackage{lmodern}",
            r"\usepackage{titlesec}",
            r"\usepackage{graphicx}",
            r"\usepackage{float}",
            r"\usepackage{hyperref}",
            r"\setlength{\parindent}{0pt}",
            r"\setlength{\parskip}{6pt}",
            r"\titleformat{\section}{\Large\bfseries}{}{0em}{}",
            r"\titleformat{\subsection}{\large\bfseries}{}{0em}{}",
            r"\titlespacing*{\section}{0pt}{1.2em}{0.6em}",
            r"\titlespacing*{\subsection}{0pt}{0.8em}{0.4em}",
            r"\setcounter{secnumdepth}{0}"
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


def _text(value: Any) -> str:
    return str(value or "").strip()


def _copy_portfolio_images(images: List[dict], assets_dir: Path) -> List[dict]:
    copied: List[dict] = []

    for index, image in enumerate(images):
        raw_path = image.get("path") or image.get("image_path") or image.get("file_path")
        if not raw_path:
            continue

        src = Path(raw_path)
        if not src.exists() or not src.is_file():
            continue

        ext = src.suffix or ".png"
        dest = assets_dir / f"portfolio_image_{index}{ext}"
        shutil.copy2(src, dest)

        copied.append(
            {
                "relative_path": f"assets/{dest.name}",
                "caption": _text(image.get("caption")),
                "is_cover": bool(image.get("is_cover", False)),
                "sort_order": int(image.get("sort_order", index)),
            }
        )

    copied.sort(key=lambda img: (img["sort_order"], img["relative_path"]))
    return copied


def _image_markdown(image: dict) -> str:
    path = image.get("relative_path", "")
    caption = _text(image.get("caption")) or "Project image"
    if not path:
        return ""
    return f"![{caption}]({path})\n"

def _render_classic_template(item: dict, images: List[dict]) -> List[str]:
    lines: List[str] = []

    name = _text(item.get("name") or item.get("project_id") or "Untitled Project")
    project_id = _text(item.get("project_id"))
    source = _text(item.get("source"))
    blurb = _text(item.get("portfolio_blurb") or item.get("blurb") or item.get("summary"))
    key_role = _text(item.get("key_role"))
    evidence = _text(item.get("evidence_of_success") or item.get("evidence"))

    lines.append(f"## {name}")
    if project_id:
        lines.append(f"**Project ID:** {project_id}")
    if source:
        lines.append(f"**Source:** {source}")
    lines.append("")

    cover = next((img for img in images if img.get("is_cover")), None)
    if cover:
        lines.append(_image_markdown(cover))

    if blurb:
        lines.append(blurb)
        lines.append("")

    if key_role:
        lines.append("### Key Role")
        lines.append(key_role)
        lines.append("")

    if evidence:
        lines.append("### Evidence of Success")
        lines.append(evidence)
        lines.append("")

    extra_images = [img for img in images if img is not cover]
    if extra_images:
        lines.append("### Project Images")
        lines.append("")
        for image in extra_images:
            lines.append(_image_markdown(image))

    return lines


def _render_case_study_template(item: dict, images: List[dict]) -> List[str]:
    lines: List[str] = []

    name = _text(item.get("name") or item.get("project_id") or "Untitled Project")
    blurb = _text(item.get("portfolio_blurb") or item.get("blurb") or item.get("summary"))
    key_role = _text(item.get("key_role"))
    evidence = _text(item.get("evidence_of_success") or item.get("evidence"))
    impact = _text(item.get("impact") or item.get("result") or item.get("outcome"))
    source = _text(item.get("source"))

    lines.append(f"## {name}")
    if source:
        lines.append(f"**Source:** {source}")
    lines.append("")

    cover = next((img for img in images if img.get("is_cover")), None)
    if cover:
        lines.append(_image_markdown(cover))

    if blurb:
        lines.append("### Overview")
        lines.append(blurb)
        lines.append("")

    if key_role:
        lines.append("### My Role")
        lines.append(key_role)
        lines.append("")

    if evidence:
        lines.append("### What I Built")
        lines.append(evidence)
        lines.append("")

    if impact:
        lines.append("### Outcome")
        lines.append(impact)
        lines.append("")

    gallery = [img for img in images if img is not cover]
    if gallery:
        lines.append("### Visuals")
        lines.append("")
        for image in gallery:
            lines.append(_image_markdown(image))

    return lines


def _render_gallery_template(item: dict, images: List[dict]) -> List[str]:
    lines: List[str] = []

    name = _text(item.get("name") or item.get("project_id") or "Untitled Project")
    blurb = _text(item.get("portfolio_blurb") or item.get("blurb") or item.get("summary"))
    key_role = _text(item.get("key_role"))

    lines.append(f"## {name}")
    lines.append("")

    if blurb:
        lines.append(blurb)
        lines.append("")

    if key_role:
        lines.append(f"**Key Role:** {key_role}")
        lines.append("")

    if images:
        lines.append("### Gallery")
        lines.append("")
        for image in images:
            lines.append(_image_markdown(image))

    evidence = _text(item.get("evidence_of_success") or item.get("evidence"))
    if evidence:
        lines.append("### Notes")
        lines.append(evidence)
        lines.append("")

    return lines


def _render_entry(item: dict, images: List[dict]) -> List[str]:
    template_id = _text(item.get("template_id") or "classic").lower()

    if template_id == "case_study":
        return _render_case_study_template(item, images)
    if template_id == "gallery":
        return _render_gallery_template(item, images)
    return _render_classic_template(item, images)


def _generate_markdown(
    entries: List[dict],
    assets_dir: Path,
    title: str = "Portfolio Showcase",
) -> str:
    """
    IMPORTANT:
    assets_dir is accepted here because this function is the one that loops
    through every portfolio entry and turns it into markdown.

    That means this is the correct place to:
    1. copy images for each entry into the temp assets folder
    2. build markdown that references those copied images
    """
    lines: List[str] = [f"# {title}", ""]

    for item in entries:
        # ADDITION INSIDE THE LOOP:
        # Copy the current project's images into the temp assets folder,
        # then render this entry using the selected template.
        images = _copy_portfolio_images(item.get("images", []), assets_dir)

        lines.extend(_render_entry(item, images))
        lines.append(r"\newpage")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def build_portfolio_pdf_with_pandoc(
    entries: List[dict],
    output_path: Path,
    *,
    title: str = "Portfolio Showcase",
) -> Path:
    """
    IMPORTANT:
    assets_dir is CREATED here because this is where the temp build folder exists.

    Flow:
    1. create temp folder
    2. create temp assets folder inside it
    3. pass assets_dir into _generate_markdown(...)
    4. markdown uses relative image paths like assets/portfolio_image_0.png
    5. pandoc gets --resource-path so it can find those files
    """
    output_path = Path(output_path)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # ADDITION HERE:
        # Create the assets folder that will temporarily hold copied images.
        assets_dir = tmpdir_path / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)

        # ADDITION HERE:
        # Pass assets_dir into the markdown builder.
        markdown_text = _generate_markdown(
            entries,
            assets_dir=assets_dir,
            title=title,
        )

        md_path = tmpdir_path / "portfolio.md"
        pdf_path = tmpdir_path / "portfolio.pdf"
        header_path = tmpdir_path / "header.tex"

        md_path.write_text(markdown_text, encoding="utf-8")
        header_path.write_text(_latex_header(), encoding="utf-8")

        engine = _pick_pdf_engine()

        try:
            subprocess.run(
                [
                    "pandoc",
                    str(md_path),
                    "-o",
                    str(pdf_path),
                    f"--pdf-engine={engine}",
                    "-V",
                    "fontsize=11pt",
                    "--include-in-header",
                    str(header_path),
                    # ADDITION HERE:
                    # Tell pandoc where to resolve relative image paths from.
                    "--resource-path",
                    str(tmpdir_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as exc:
            raise RuntimeError("Pandoc is not installed. Install it from https://pandoc.org") from exc
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(f"Pandoc PDF generation failed:\n{exc.stderr}") from exc

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(pdf_path.read_bytes())
        return output_path