from __future__ import annotations
from dataclasses import dataclass
from .consent import ConsentState
from .logging_utils import get_logger

logger = get_logger(__name__)

@dataclass(frozen=True)
class ModeResolution:
    requested: str
    resolved: str
    reason: str
    

_VALID_MODES = {"local", "external", "auto"}
_EXTERNAL_SUPPORTED = True


def _consent_allows_external(consent: ConsentState) -> bool:
    decision = (consent.decision or "").lower()
    return consent.granted and decision.startswith("allow")


def resolve_mode(requested: str, consent: ConsentState) -> ModeResolution:
    requested_lower = requested.lower()
    if requested_lower not in _VALID_MODES:
        logger.warning("Unknown analysis mode '%s', defaulting to local", requested)
        requested_lower = "local"

    if requested_lower == "auto":
        requested_lower = "external" if _consent_allows_external(consent) else "local"

    if requested_lower == "external" and not _EXTERNAL_SUPPORTED:
        reason = "External analysis not available; using local mode"
        logger.info(reason)
        return ModeResolution(requested=requested, resolved="local", reason=reason)

    if requested_lower == "external" and not _consent_allows_external(consent):
        reason = "Consent for external services not granted; using local mode"
        logger.info(reason)
        return ModeResolution(requested=requested, resolved="local", reason=reason)

    reason = "External analysis permitted" if requested_lower == "external" else "Local analysis enforced"
    return ModeResolution(requested=requested, resolved=requested_lower, reason=reason)
