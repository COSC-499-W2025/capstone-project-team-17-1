"""Shared logging configuration for the capstone analyzer."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path


def get_base_log_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.getenv("APPDATA", Path.home()))
    else:
        base = Path.home()

    app_dir = base / "Loom"
    app_dir.mkdir(exist_ok=True)

    log_dir = app_dir / "log"
    log_dir.mkdir(exist_ok=True)

    return log_dir


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