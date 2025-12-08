"""Shared logging configuration for the capstone analyzer."""

from __future__ import annotations

import logging
from pathlib import Path


LOG_DIR = Path("log")
LOG_DIR.mkdir(exist_ok=True)


def get_logger(name: str) -> logging.Logger:
    """Return a module-level logger writing to the shared log directory."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        log_path = LOG_DIR / "capstone.log"
        error_path = LOG_DIR / "analysis-errors.log"
        fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

        handler = logging.FileHandler(log_path, encoding="utf-8")
        handler.setFormatter(fmt)
        handler.setLevel(logging.INFO)
        logger.addHandler(handler)

        error_handler = logging.FileHandler(error_path, encoding="utf-8")
        error_handler.setFormatter(fmt)
        error_handler.setLevel(logging.ERROR)
        logger.addHandler(error_handler)
    return logger
