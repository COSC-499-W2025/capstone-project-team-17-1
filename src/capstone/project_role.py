from __future__ import annotations

from typing import Any


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def infer_project_role_from_snapshot(snapshot: dict[str, Any]) -> str:
    frameworks = {
        str(x).strip().lower()
        for x in _as_list(snapshot.get("frameworks"))
        if str(x).strip()
    }

    technologies = set()
    for value in _as_list(snapshot.get("technologies")):
        if str(value).strip():
            technologies.add(str(value).strip().lower())

    for value in _as_list(snapshot.get("tech_stack")):
        if str(value).strip():
            technologies.add(str(value).strip().lower())

    skills = snapshot.get("skills") or []
    if isinstance(skills, list):
        for item in skills:
            if isinstance(item, dict):
                raw = item.get("skill") or item.get("name") or item.get("label")
                if raw and str(raw).strip():
                    technologies.add(str(raw).strip().lower())
            elif str(item).strip():
                technologies.add(str(item).strip().lower())

    languages_raw = snapshot.get("languages") or {}
    languages = set()
    if isinstance(languages_raw, dict):
        languages = {
            str(k).strip().lower()
            for k in languages_raw.keys()
            if str(k).strip()
        }
    elif isinstance(languages_raw, list):
        languages = {
            str(x).strip().lower()
            for x in languages_raw
            if str(x).strip()
        }

    signals = frameworks | technologies | languages

    frontend_markers = {
        "react", "vue", "vue.js", "next", "next.js", "nuxt", "nuxt.js",
        "angular", "svelte", "html", "css", "javascript", "typescript"
    }
    backend_markers = {
        "fastapi", "flask", "django", "express", "node", "node.js",
        "spring", "laravel", "rails", "ruby on rails", "python",
        "java", "go", "sql", "postgresql", "mysql"
    }
    mobile_markers = {
        "android", "ios", "swift", "kotlin", "react native", "flutter"
    }
    game_markers = {
        "unity", "unreal", "unreal engine", "shaderlab", "c#"
    }

    frontend_hits = len(signals & frontend_markers)
    backend_hits = len(signals & backend_markers)
    mobile_hits = len(signals & mobile_markers)
    game_hits = len(signals & game_markers)

    if game_hits >= 2:
        return "Game Developer"
    if mobile_hits >= 2:
        return "Mobile Developer"
    if frontend_hits >= 2 and backend_hits >= 2:
        return "Full Stack Developer"
    if frontend_hits >= 2:
        return "Frontend Developer"
    if backend_hits >= 2:
        return "Backend Developer"

    if "python" in languages or "fastapi" in frameworks or "django" in frameworks or "flask" in frameworks:
        return "Backend Developer"
    if "react" in frameworks or "javascript" in languages or "typescript" in languages:
        return "Frontend Developer"

    return "Software Developer"