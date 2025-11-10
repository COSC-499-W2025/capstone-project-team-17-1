"""Consent utilities to guard data processing."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, Iterable, Sequence

from .config import Config, ConsentState, load_config, save_config, update_consent


class ConsentError(RuntimeError):
    """Raised when consent is missing for a sensitive operation."""


class ExternalPermissionDenied(ConsentError):
    """Raised when an external service request is rejected."""


_LOG_DIR = Path("log")
_LOG_DIR.mkdir(exist_ok=True)
_CONSENT_JOURNAL = _LOG_DIR / "consent_decisions.jsonl"

_ALLOW_DECISIONS = {"allow", "allow_once", "allow_always"}
_DENY_DECISIONS = {"deny", "deny_once", "deny_always"}


def prompt_for_consent(
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> str:
    """Prompt the user repeatedly until a valid y/n input is provided.

    Returns "accepted" for affirmative answers and "rejected" otherwise.
    """

    prompt = "Please enter 'y' for yes or 'n' for no: "
    while True:
        response = input_fn(prompt).strip().lower()
        if response in {"y", "yes"}:
            return "accepted"
        if response in {"n", "no"}:
            return "rejected"
        output_fn("Invalid input :( Please enter 'y' for yes or 'n' for no. Thanks :)")


def ensure_consent(require_granted: bool = True) -> ConsentState:
    config = load_config()
    consent = config.consent
    if require_granted and not consent.granted:
        raise ConsentError(
            "User consent required before processing archives. Run 'capstone consent grant' to proceed."
        )
    return consent


def grant_consent(decision: str = "allow") -> Config:
    return update_consent(granted=decision in _ALLOW_DECISIONS, decision=decision, source="cli")


def revoke_consent(decision: str = "deny") -> Config:
    return update_consent(granted=False, decision=decision, source="cli")


def export_consent() -> dict[str, object]:
    config = load_config()
    return asdict(config.consent)


def _log_external_decision(entry: Dict[str, object]) -> None:
    payload = dict(entry)
    payload.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
    with _CONSENT_JOURNAL.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False))
        fh.write("\n")


def _normalize_decision(decision: str) -> str:
    return (decision or "").strip().lower()


def _decision_allows(decision: str) -> bool:
    return _normalize_decision(decision) in _ALLOW_DECISIONS


def _decision_blocks(decision: str) -> bool:
    return _normalize_decision(decision) in _DENY_DECISIONS


def _should_remember(decision: str) -> bool:
    normalized = _normalize_decision(decision)
    return normalized in {"allow_always", "deny", "deny_always"}


def _load_permissions() -> Dict[str, Dict[str, object]]:
    config = load_config()
    permissions = config.preferences.external_permissions or {}
    return {key: dict(value) for key, value in permissions.items()}


def _store_permission(
    service: str,
    payload: Dict[str, object] | None,
    *,
    config: Config | None = None,
) -> Config:
    config = config or load_config()
    permissions = config.preferences.external_permissions or {}
    new_permissions = dict(permissions)
    if payload is None:
        new_permissions.pop(service, None)
    else:
        new_permissions[service] = dict(payload)
    config.preferences.external_permissions = new_permissions
    save_config(config)
    return config


def get_external_permission(service: str) -> Dict[str, object] | None:
    """Return the stored permission decision for the given service, if any."""

    permissions = _load_permissions()
    return permissions.get(service)


def clear_external_permission(service: str) -> Config:
    """Remove the stored decision for an external service."""

    return _store_permission(service, None)


def _format_transparency_message(
    service: str,
    data_types: Sequence[str] | None,
    purpose: str,
    destination: str,
    privacy: str | None,
) -> Iterable[str]:
    yield f"Permission required to contact '{service}'."
    yield "Before continuing, review how your data would be used:"
    shared_data = ", ".join(data_types) if data_types else "metadata only"
    yield f"- Data shared: {shared_data}"
    yield f"- Purpose: {purpose or 'Not specified'}"
    yield f"- Destination: {destination or 'Not provided'}"
    privacy_note = privacy or "The service states that data is handled under its published privacy policy."
    yield f"- Storage & privacy: {privacy_note}"
    yield ""
    yield "Options:"
    yield "  [1] Allow this session"
    yield "  [2] Always allow for this service"
    yield "  [3] Deny this session"
    yield "  [4] Always deny for this service"


def _prompt_for_external_decision(
    input_fn: Callable[[str], str],
    output_fn: Callable[[str], None],
) -> str:
    options = {
        "1": "allow_once",
        "2": "allow_always",
        "3": "deny_once",
        "4": "deny_always",
    }
    prompt = "Enter 1, 2, 3, or 4 to continue: "
    while True:
        choice = input_fn(prompt).strip().lower()
        decision = options.get(choice)
        if decision:
            return decision
        output_fn("Please enter valid option, choose 1, 2, 3, or 4.")


def request_external_service_permission(
    service: str,
    *,
    data_types: Sequence[str] | None = None,
    purpose: str = "",
    destination: str = "",
    privacy: str | None = None,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
    source: str = "runtime",
    auto: bool | None = None,
) -> bool:
    """Prompt for consent to use an external service, returning True if allowed."""

    config = load_config()
    user_id = config.preferences.user_id or "local-user"
    permissions = config.preferences.external_permissions or {}
    stored = permissions.get(service)

    def _log(decision: str, granted: bool, remember: bool, *, auto_usage: bool) -> None:
        _log_external_decision(
            {
                "service": service,
                "decision": decision,
                "granted": granted,
                "remember": remember,
                "auto": auto_usage,
                "user_id": user_id,
                "source": source,
                "data": list(data_types) if data_types else [],
                "purpose": purpose,
                "destination": destination,
            }
        )

    if stored and stored.get("remember"):
        decision = stored.get("decision", "")
        granted = bool(stored.get("granted", False))
        _log(decision, granted, True, auto_usage=True if auto is None else auto)
        return granted

    for line in _format_transparency_message(service, data_types, purpose, destination, privacy):
        output_fn(line)

    decision = _prompt_for_external_decision(input_fn, output_fn)
    granted = _decision_allows(decision)
    remember = _should_remember(decision)

    if remember:
        payload = {
            "decision": decision,
            "granted": granted,
            "remember": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "destination": destination,
            "purpose": purpose,
            "data": list(data_types) if data_types else [],
        }
        _store_permission(service, payload, config=config)
    else:
        # Ensure prior remembered decisions are cleared for one-time responses.
        _store_permission(service, None, config=config)

    _log(decision, granted, remember, auto_usage=False if auto is None else auto)
    return granted


def ensure_external_permission(
    service: str,
    *,
    data_types: Sequence[str] | None = None,
    purpose: str = "",
    destination: str = "",
    privacy: str | None = None,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
    source: str = "runtime",
) -> None:
    """Raise if the user does not authorise contacting an external service."""

    allowed = request_external_service_permission(
        service,
        data_types=data_types,
        purpose=purpose,
        destination=destination,
        privacy=privacy,
        input_fn=input_fn,
        output_fn=output_fn,
        source=source,
    )
    if not allowed:
        raise ExternalPermissionDenied(
            f"External request to '{service}' blocked. Update consent settings to continue."
        )
