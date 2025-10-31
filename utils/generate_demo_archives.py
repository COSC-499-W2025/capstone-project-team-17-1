"""Utility script to create demo archives for ranking smoke tests."""

from __future__ import annotations

import zipfile
from pathlib import Path


def _write_project(root: Path, *, extra_code: str = "") -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "README.md").write_text("# Demo\n", encoding="utf-8")
    (root / "main.py").write_text("print('hello')\n" + extra_code, encoding="utf-8")


def _zip_project(root: Path) -> None:
    archive = root.with_suffix(".zip")
    with zipfile.ZipFile(archive, "w") as zf:
        for path in root.iterdir():
            zf.write(path, arcname=path.name)


def create_demo_archives(base_dir: Path | None = None) -> None:
    """Create two small projects and zip them for CLI ranking checks."""

    base = base_dir or Path.cwd()
    project_one = base / "demo_project"
    project_two = base / "demo_project2"

    _write_project(project_one)
    _write_project(project_two, extra_code="print('bye')\n")

    _zip_project(project_one)
    _zip_project(project_two)


if __name__ == "__main__":  # pragma: no cover - manual helper
    create_demo_archives()
