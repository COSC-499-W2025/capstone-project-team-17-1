"""Detect project types and render lightweight markdown summaries."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Tuple

from .logging_utils import get_logger


logger = get_logger(__name__)

_FRONTEND_KEYWORDS = {"react", "vue", "svelte", "electron"}
_BACKEND_KEYWORDS = {"express", "koa", "fastify"}


class ProjectDetectionError(RuntimeError):
    """Raised when project metadata cannot be parsed."""


def _load_package_json(path: Path) -> Dict[str, object]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        logger.error("Failed to parse package.json: %s", exc)
        raise ProjectDetectionError(f"Invalid package.json: {exc}") from exc


def detect_node_electron_project(root: Path) -> Tuple[bool, str]:
    """Return (is_project, markdown_summary)."""

    package_json = root / "package.json"
    if not package_json.exists():
        return False, ""

    data = _load_package_json(package_json)
    dependencies = data.get("dependencies", {}) or {}
    dev_dependencies = data.get("devDependencies", {}) or {}

    if not isinstance(dependencies, dict) or not isinstance(dev_dependencies, dict):
        raise ProjectDetectionError("Dependencies must be objects")

    all_deps = {**dependencies, **dev_dependencies}
    lowered = {name.lower() for name in all_deps}
    is_electron = "electron" in lowered
    is_frontend = bool(lowered & _FRONTEND_KEYWORDS)
    is_backend = bool(lowered & _BACKEND_KEYWORDS)

    summary_lines = [f"# Project: {data.get('name', 'Unnamed')}"]
    summary_lines.append("")
    summary_lines.append("## Stack Overview")

    if is_electron:
        summary_lines.append("- Electron desktop application detected")
    if is_frontend:
        summary_lines.append(f"- Frontend frameworks: {', '.join(sorted(lowered & _FRONTEND_KEYWORDS))}")
    if is_backend:
        summary_lines.append(f"- Backend frameworks: {', '.join(sorted(lowered & _BACKEND_KEYWORDS))}")
    if not (is_electron or is_frontend or is_backend):
        summary_lines.append("- General Node.js project")

    summary_lines.append("")
    summary_lines.append("## Scripts")
    scripts = data.get("scripts", {}) or {}
    if isinstance(scripts, dict) and scripts:
        for name, cmd in scripts.items():
            summary_lines.append(f"- `{name}` → `{cmd}`")
    else:
        summary_lines.append("- No npm scripts defined")

    return True, "\n".join(summary_lines)


__all__ = ["detect_node_electron_project", "ProjectDetectionError"]
