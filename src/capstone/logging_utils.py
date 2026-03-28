"""Shared logging configuration for the capstone analyzer."""

from __future__ import annotations

import logging
import os
import sys
import tempfile
from pathlib import Path


def _resolve_default_base_dir() -> Path:
    if sys.platform == "win32":
        return Path(os.getenv("APPDATA", Path.home()))
    return Path.home()


def _ensure_writable_dir(path: Path) -> Path | None:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return path
    except OSError:
        return None


def get_base_log_dir() -> Path:
    candidates = []

    env_dir = os.getenv("CAPSTONE_LOG_DIR")
    if env_dir:
        candidates.append(Path(env_dir))

    candidates.append(_resolve_default_base_dir() / "Loom" / "log")
    candidates.append(Path.cwd() / ".capstone-log")
    candidates.append(Path(tempfile.gettempdir()) / "capstone-log")

    for candidate in candidates:
        resolved = _ensure_writable_dir(candidate)
        if resolved is not None:
            return resolved

    raise RuntimeError("Unable to find a writable log directory")


LOG_DIR = get_base_log_dir()


def get_logger(name: str) -> logging.Logger:
    """Return a module-level logger writing to the shared log directory."""
    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(logging.INFO)

        log_path = LOG_DIR / "capstone.log"
        error_path = LOG_DIR / "analysis-errors.log"

        fmt = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )

        handler = logging.FileHandler(log_path, encoding="utf-8")
        handler.setFormatter(fmt)
        handler.setLevel(logging.INFO)
        logger.addHandler(handler)

        error_handler = logging.FileHandler(error_path, encoding="utf-8")
        error_handler.setFormatter(fmt)
        error_handler.setLevel(logging.ERROR)
        logger.addHandler(error_handler)

    return logger
