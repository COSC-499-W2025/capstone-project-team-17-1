"""Lightweight language and framework detection heuristics."""

from __future__ import annotations

import json
from pathlib import PurePosixPath
from typing import Iterable, Set


_EXTENSION_LANGUAGE = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".jsx": "JavaScript",
    ".java": "Java",
    ".rb": "Ruby",
    ".go": "Go",
    ".rs": "Rust",
    ".c": "C",
    ".cpp": "C++",
    ".h": "C",
    ".hpp": "C++",
    ".cs": "C#",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".m": "Objective-C",
    ".php": "PHP",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "CSS",
    ".md": "Markdown",
    ".json": "JSON",
    ".yml": "YAML",
    ".yaml": "YAML",
    ".sql": "SQL",
    ".sh": "Shell",
    ".bat": "Batchfile",
    ".ps1": "PowerShell",
}

_DOC_EXTENSIONS = {".md", ".rst", ".txt"}
_CODE_EXTENSIONS = set(_EXTENSION_LANGUAGE) - {".md", ".json", ".yaml", ".yml", ".html", ".css", ".scss"}
_ASSET_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".pdf", ".csv"}

_KNOWN_FRAMEWORK_DEPENDENCIES = {
    "@angular/core": "Angular",
    "react": "React",
    "vue": "Vue.js",
    "svelte": "Svelte",
    "next": "Next.js",
    "nuxt": "Nuxt.js",
    "django": "Django",
    "flask": "Flask",
    "fastapi": "FastAPI",
    "express": "Express",
    "rails": "Ruby on Rails",
    "laravel": "Laravel",
    "spring": "Spring",
}


def detect_language(path: str) -> str | None:
    extension = PurePosixPath(path).suffix.lower()
    return _EXTENSION_LANGUAGE.get(extension)


def classify_activity(path: str) -> str:
    extension = PurePosixPath(path).suffix.lower()
    if extension in _DOC_EXTENSIONS:
        return "documentation"
    if extension in _CODE_EXTENSIONS:
        return "code"
    if extension in _ASSET_EXTENSIONS:
        return "asset"
    return "other"


def detect_frameworks_from_package_json(content: str) -> Set[str]:
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return set()
    frameworks: Set[str] = set()
    for section in ("dependencies", "devDependencies", "peerDependencies"):
        deps = data.get(section, {})
        if not isinstance(deps, dict):
            continue
        for name in deps:
            framework = _KNOWN_FRAMEWORK_DEPENDENCIES.get(name.lower())
            if framework:
                frameworks.add(framework)
    return frameworks


def detect_frameworks_from_python_requirements(lines: Iterable[str]) -> Set[str]:
    frameworks: Set[str] = set()
    for raw_line in lines:
        line = raw_line.strip().lower()
        if not line or line.startswith("#"):
            continue
        package = line.split("==")[0].split(">=")[0].split("<=")[0].strip()
        framework = _KNOWN_FRAMEWORK_DEPENDENCIES.get(package)
        if framework:
            frameworks.add(framework)
    return frameworks
