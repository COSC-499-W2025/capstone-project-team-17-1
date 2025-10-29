"""Consent utilities to guard data processing."""

from __future__ import annotations

from dataclasses import asdict

from .config import Config, ConsentState, load_config, save_config, update_consent


class ConsentError(RuntimeError):
    """Raised when consent is missing for a sensitive operation."""


def ensure_consent(require_granted: bool = True) -> ConsentState:
    config = load_config()
    consent = config.consent
    if require_granted and not consent.granted:
        raise ConsentError(
            "User consent required before processing archives. Run 'capstone consent grant' to proceed."
        )
    return consent


def grant_consent(decision: str = "allow") -> Config:
    return update_consent(granted=True, decision=decision, source="cli")


def revoke_consent(decision: str = "deny") -> Config:
    return update_consent(granted=False, decision=decision, source="cli")


def export_consent() -> dict[str, object]:
    config = load_config()
    return asdict(config.consent)
