# capstone/resume_pdf_builder.py

from __future__ import annotations

import re
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


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_template_path() -> Path:
    return _repo_root() / "templates" / "resume_template.tex"


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


def build_markdown_from_resume(resume: Dict[str, Any]) -> str:
    return _generate_markdown(resume)


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


def _as_clean_text(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    return text if text else fallback


def _flatten_str_list(items: Any) -> list[str]:
    values: list[str] = []
    if not isinstance(items, list):
        return values
    for item in items:
        if isinstance(item, str):
            text = item.strip()
            if text:
                values.append(text)
        elif isinstance(item, dict):
            for key in ("name", "skill", "title"):
                v = item.get(key)
                if isinstance(v, str) and v.strip():
                    values.append(v.strip())
                    break
    return values


def _join_or_dash(items: list[str]) -> str:
    if not items:
        return "N/A"
    return ", ".join(items)


def _extract_resume_entries(resume: Dict[str, Any], section_name: str) -> list[Dict[str, Any]]:
    entries: list[Dict[str, Any]] = []
    for section in resume.get("sections", []) or []:
        if section.get("name") != section_name:
            continue
        for item in section.get("items", []) or []:
            if isinstance(item, dict):
                entries.append(item)
    return entries


def _pick_bullets(entry: Dict[str, Any], fallback: str = "") -> list[str]:
    bullets = entry.get("bullets")
    if isinstance(bullets, list):
        result = [str(x).strip() for x in bullets if str(x).strip()]
        if result:
            return result
    for key in ("highlights", "responsibilities"):
        values = entry.get(key)
        if isinstance(values, list):
            result = [str(x).strip() for x in values if str(x).strip()]
            if result:
                return result
    summary = (
        _as_clean_text(entry.get("entrySummary"))
        or _as_clean_text(entry.get("summary"))
        or _as_clean_text(entry.get("entryBody"))
        or _as_clean_text(entry.get("body"))
        or _as_clean_text(entry.get("excerpt"))
        or fallback
    )
    if not summary:
        return []
    # Preserve multi-line CLI input as multiple bullets.
    lines = [line.strip() for line in str(summary).splitlines() if line.strip()]
    if lines:
        return lines
    return [summary]


def _entry_field(entry: Dict[str, Any], *keys: str, fallback: str = "") -> str:
    for key in keys:
        value = _as_clean_text(entry.get(key))
        if value:
            return value
    return fallback


def _render_itemize_block(bullets: list[str]) -> str:
    if not bullets:
        return ""
    lines = [r"\begin{itemize}"]
    for bullet in bullets:
        lines.append(rf"  \item {_safe_text(bullet)}")
    lines.append(r"\end{itemize}")
    return "\n".join(lines)


def _render_resume_entry_block(title: str, date_text: str, subtitle: str, location: str, bullets: list[str]) -> str:
    lines = [
        rf"\ResumeEntry{{{_safe_text(title)}}}{{{_safe_text(date_text)}}}{{{_safe_text(subtitle)}}}{{{_safe_text(location)}}}"
    ]
    itemize = _render_itemize_block(bullets)
    if itemize:
        lines.append(itemize)
    return "\n".join(lines)


def _extract_template_fields(resume: Dict[str, Any]) -> Dict[str, str]:
    links = resume.get("links") if isinstance(resume.get("links"), dict) else {}
    contact = resume.get("contact") if isinstance(resume.get("contact"), dict) else {}
    candidate = resume.get("candidate") if isinstance(resume.get("candidate"), dict) else {}

    full_name = (
        _as_clean_text(resume.get("fullName"))
        or _as_clean_text(resume.get("name"))
        or _as_clean_text(candidate.get("name"))
        or "Your Name"
    )
    email = (
        _as_clean_text(resume.get("email"))
        or _as_clean_text(contact.get("email"))
        or "you@example.com"
    )
    phone = (
        _as_clean_text(resume.get("phone"))
        or _as_clean_text(contact.get("phone"))
        or "+1 (000) 000-0000"
    )
    location = (
        _as_clean_text(resume.get("location"))
        or _as_clean_text(contact.get("location"))
        or "City, State"
    )

    github_url = (
        _as_clean_text(links.get("github"))
        or _as_clean_text(resume.get("github"))
        or "https://github.com/your-handle"
    )
    portfolio_url = (
        _as_clean_text(links.get("portfolio"))
        or _as_clean_text(resume.get("portfolio"))
        or "https://your-portfolio.example.com"
    )

    summary = _as_clean_text(resume.get("professionalSummary")) or _as_clean_text(resume.get("summary"))
    summary_entries = _extract_resume_entries(resume, "summary")
    summary_lines: list[str] = []
    if summary_entries:
        for entry in summary_entries:
            text = (
                _entry_field(entry, "content", "entrySummary", "summary", "entryBody", "body", "excerpt")
                or _entry_field(entry, "title")
            )
            if text:
                summary_lines.append(r"{\small " + _safe_text(text) + r"}\par")
    if not summary_lines and summary:
        summary_lines.append(r"{\small " + _safe_text(summary) + r"}")

    all_skills = _flatten_str_list(resume.get("skills"))
    if not all_skills:
        project_context = resume.get("projectContext", {}) or {}
        for project in project_context.values():
            if not isinstance(project, dict):
                continue
            all_skills.extend(_flatten_str_list(project.get("skills")))
    all_skills = sorted(set(all_skills))
    languages = _flatten_str_list(resume.get("languages"))
    tools = _flatten_str_list(resume.get("tools"))

    core_skill_entries = _extract_resume_entries(resume, "core_skill")
    core_skill_lines: list[str] = []
    if core_skill_entries:
        for entry in core_skill_entries:
            label = _entry_field(entry, "title", fallback="Core")
            content = _entry_field(entry, "content")
            if not content:
                bullets = _pick_bullets(entry, "")
                content = ", ".join([token for token in bullets if token.strip()])
            if content:
                core_skill_lines.append(rf"\SkillRow{{{_safe_text(label)}}}{{{_safe_text(content)}}}")
    if not core_skill_lines and (all_skills or tools or languages):
        core_skill_lines = [
            rf"\SkillRow{{Core}}{{{_safe_text(_join_or_dash(all_skills))}}}",
            rf"\SkillRow{{Tools}}{{{_safe_text(_join_or_dash(tools))}}}",
            rf"\SkillRow{{Languages}}{{{_safe_text(_join_or_dash(languages))}}}",
        ]

    experience_entries = _extract_resume_entries(resume, "experience") or _extract_resume_entries(resume, "work")
    experience_blocks: list[str] = []
    for entry in experience_entries:
        bullets = _pick_bullets(entry, "Delivered meaningful project outcomes.")[:3]
        experience_blocks.append(
            _render_resume_entry_block(
                title=_entry_field(entry, "title", fallback="Experience"),
                date_text=_entry_field(entry, "dateRange", "date", fallback="Date"),
                subtitle=_entry_field(entry, "company", "organization", "subtitle", fallback="Company"),
                location=_entry_field(entry, "location", fallback="Location"),
                bullets=bullets,
            )
        )

    project_entries = list(_iter_project_items(resume))
    if not project_entries and isinstance(resume.get("projects"), list):
        for p in resume.get("projects") or []:
            if isinstance(p, dict):
                project_entries.append(
                    {
                        "title": p.get("project_id") or p.get("title") or "Project",
                        "entrySummary": p.get("resume_bullet") or p.get("summary") or "",
                        "stack": _join_or_dash(
                            _flatten_str_list(p.get("matched_required"))
                            + _flatten_str_list(p.get("matched_preferred"))
                            + _flatten_str_list(p.get("matched_keywords"))
                        ),
                    }
                )
    project_blocks: list[str] = []
    for entry in project_entries:
        bullets = _pick_bullets(entry, "Implemented core features and improvements.")[:2]
        project_blocks.append(
            _render_resume_entry_block(
                title=_entry_field(entry, "title", fallback="Project"),
                date_text=_entry_field(entry, "dateRange", "date", fallback="Date"),
                subtitle=_entry_field(entry, "stack", "subtitle", fallback="Tech Stack"),
                location="",
                bullets=bullets,
            )
        )

    education_entries = _extract_resume_entries(resume, "education")
    education_blocks: list[str] = []
    for entry in education_entries:
        coursework = _entry_field(entry, "coursework", "content", "entrySummary", "summary", "entryBody", "body")
        lines = [
            rf"\ResumeEntry{{{_safe_text(_entry_field(entry, 'school', 'title', fallback='University Name'))}}}"
            rf"{{{_safe_text(_entry_field(entry, 'dateRange', 'date', fallback='Date'))}}}"
            rf"{{{_safe_text(_entry_field(entry, 'degree', 'summary', 'subtitle', fallback='Degree Program'))}}}"
            rf"{{{_safe_text(_entry_field(entry, 'location', fallback='Location'))}}}"
        ]
        if coursework:
            lines.append(r"{\small \textit{" + _safe_text(coursework) + r"}}\par")
        education_blocks.append("\n".join(lines))

    custom_section_blocks: list[str] = []
    for section in resume.get("sections", []) or []:
        if not isinstance(section, dict):
            continue
        section_name = str(section.get("name") or "").strip()
        if not section_name.startswith("custom::"):
            continue
        label = _as_clean_text(section.get("label")) or section_name.split("custom::", 1)[1].replace("_", " ").title()
        items = [entry for entry in (section.get("items") or []) if isinstance(entry, dict)]
        entry_blocks: list[str] = []
        for entry in items:
            entry_blocks.append(
                _render_resume_entry_block(
                    title=_entry_field(entry, "title", fallback=label),
                    date_text=_entry_field(entry, "dateRange", "date", fallback=""),
                    subtitle=_entry_field(entry, "subtitle", "stack", "company", "organization", fallback=""),
                    location=_entry_field(entry, "location", fallback=""),
                    bullets=_pick_bullets(entry, ""),
                )
            )
        if entry_blocks:
            custom_section_blocks.append(
                "\n".join(
                    [
                        rf"\section*{{{_safe_text(label)}}}",
                        "\n\n".join(entry_blocks),
                    ]
                )
            )

    cert_entries = _extract_resume_entries(resume, "certifications") or _extract_resume_entries(resume, "awards")
    cert1 = cert_entries[0] if len(cert_entries) > 0 else {}
    cert2 = cert_entries[1] if len(cert_entries) > 1 else {}
    award1 = cert_entries[2] if len(cert_entries) > 2 else {}

    summary_block = "\n".join(summary_lines)
    education_block = "\n\n".join(education_blocks)
    experience_block = "\n\n".join(experience_blocks)
    core_skill_block = "\n".join(core_skill_lines)
    project_block = "\n\n".join(project_blocks)
    custom_block = "\n\n".join(custom_section_blocks)

    def _wrap_section(title: str, body: str) -> str:
        clean_body = str(body or "").strip()
        if not clean_body:
            return ""
        return "\n".join([rf"\section*{{{_safe_text(title)}}}", clean_body])

    return {
        "FULL_NAME": _safe_text(full_name),
        "EMAIL": _safe_text(email),
        "PHONE": _safe_text(phone),
        "LOCATION": _safe_text(location),
        "GITHUB_URL": _safe_text(github_url),
        "PORTFOLIO_URL": _safe_text(portfolio_url),
        "SUMMARY_BLOCK": summary_block,
        "CORE_SKILL_BLOCK": core_skill_block,
        "EXPERIENCE_BLOCK": experience_block,
        "PROJECT_BLOCK": project_block,
        "EDUCATION_BLOCK": education_block,
        "CUSTOM_SECTION_BLOCK": custom_block,
        "SUMMARY_SECTION": _wrap_section("Summary", summary_block),
        "EDUCATION_SECTION": _wrap_section("Education", education_block),
        "EXPERIENCE_SECTION": _wrap_section("Experience", experience_block),
        "CORE_SKILL_SECTION": _wrap_section("Core Skill", core_skill_block),
        "PROJECT_SECTION": _wrap_section("Project", project_block),
        # Backward-compatible placeholders for custom templates using old tokens.
        "PROFESSIONAL_SUMMARY": _safe_text(summary),
        "SKILL_CORE": _safe_text(_join_or_dash(all_skills)),
        "SKILL_TOOLS": _safe_text(_join_or_dash(tools)),
        "SKILL_LANGUAGES": _safe_text(_join_or_dash(languages)),
        "CERT_1": _safe_text(_as_clean_text(cert1.get("title") if isinstance(cert1, dict) else cert1, "Certification Name")),
        "CERT_2": _safe_text(_as_clean_text(cert2.get("title") if isinstance(cert2, dict) else cert2, "Certification Name")),
        "AWARD_1": _safe_text(_as_clean_text(award1.get("title") if isinstance(award1, dict) else award1, "Award Name")),
    }


def render_latex_from_template(
    resume: Dict[str, Any],
    template_path: Path | None = None,
    tex_output_path: Path | None = None,
) -> str:
    template = Path(template_path) if template_path else _default_template_path()
    if not template.exists():
        tex_source = _generate_latex(resume)
    else:
        tex_source = template.read_text(encoding="utf-8")
        replacements = _extract_template_fields(resume)
        lines = tex_source.splitlines(keepends=True)
        rendered_lines: list[str] = []
        placeholder_pattern = re.compile(r"__([A-Z0-9_]+)__")

        for line in lines:
            if line.lstrip().startswith("%"):
                rendered_lines.append(line)
                continue

            def _replace(match: re.Match[str]) -> str:
                key = match.group(1)
                value = replacements.get(key)
                return value if value is not None else "N/A"

            rendered_lines.append(placeholder_pattern.sub(_replace, line))

        tex_source = "".join(rendered_lines)

    if tex_output_path:
        target = Path(tex_output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(tex_source, encoding="utf-8")
    return tex_source


def _pick_tex_engine() -> str | None:
    for engine in ("xelatex", "lualatex", "pdflatex"):
        if shutil.which(engine):
            return engine
    return None


def build_pdf_with_latex(
    resume: Dict[str, Any],
    output_path: Path,
    template_path: Path | None = None,
    tex_output_path: Path | None = None,
) -> Path:
    """
    Render PDF by generating LaTeX directly and compiling with a local TeX engine.
    """
    output_path = Path(output_path)
    tex_source = render_latex_from_template(
        resume,
        template_path=template_path,
        tex_output_path=tex_output_path,
    )
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


