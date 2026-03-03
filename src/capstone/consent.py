"""
Consent utilities for API driven architecture.
No CLI prompts. No interactive terminal input.
Frontend controls consent state.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from capstone.storage import open_db, close_db
from .config import Config, ConsentState as ConfigConsentState, update_consent, load_config


class ConsentError(RuntimeError):
    """Raised when local consent is missing."""


class ExternalPermissionDenied(RuntimeError):
    """Raised when external AI usage is not allowed."""


@dataclass
class ConsentState:
    granted: bool
    decision: str
    timestamp: str
    source: str = "cli"


# -------------------------------------------------------
# DATABASE HELPERS
# -------------------------------------------------------

def _get_consent_row(conn):
    row = conn.execute(
        """
        SELECT local_consent, external_consent
        FROM privacy_consent
        LIMIT 1
        """
    ).fetchone()

    if not row:
        return False, False

    return bool(row[0]), bool(row[1])


def _upsert_consent(conn, *, local: bool | None = None, external: bool | None = None):
    existing = conn.execute(
        "SELECT id FROM privacy_consent LIMIT 1"
    ).fetchone()

    timestamp = datetime.now(timezone.utc).isoformat()

    if existing:
        updates = []
        values = []

        if local is not None:
            updates.append("local_consent = ?")
            values.append(int(local))

        if external is not None:
            updates.append("external_consent = ?")
            values.append(int(external))

        updates.append("updated_at = ?")
        values.append(timestamp)

        conn.execute(
            f"UPDATE privacy_consent SET {', '.join(updates)}",
            values,
        )
    else:
        conn.execute(
            """
            INSERT INTO privacy_consent
            (local_consent, external_consent, updated_at)
            VALUES (?, ?, ?)
            """,
            (
                int(local or False),
                int(external or False),
                timestamp,
            ),
        )

    conn.commit()


# -------------------------------------------------------
# PUBLIC API FUNCTIONS
# -------------------------------------------------------

def set_local_consent(granted: bool) -> None:
    conn = open_db()
    try:
        _upsert_consent(conn, local=granted)
    finally:
        close_db()


def set_external_consent(granted: bool) -> None:
    conn = open_db()
    try:
        _upsert_consent(conn, external=granted)
    finally:
        close_db()


def get_consent() -> dict:
    conn = open_db()
    try:
        local, external = _get_consent_row(conn)
        return {
            "local_consent": local,
            "external_consent": external,
        }
    finally:
        close_db()


def ensure_local_consent() -> None:
    conn = open_db()
    try:
        local, _ = _get_consent_row(conn)
        if not local:
            raise ConsentError("Local consent required.")
    finally:
        close_db()


def ensure_external_permission(service: str) -> None:
    """
    Pure check only.
    No prompts.
    No CLI interaction.
    Raises if not allowed.
    """

    conn = open_db()
    try:
        _, external = _get_consent_row(conn)
        if not external:
            raise ExternalPermissionDenied(
                f"External permission denied for service '{service}'."
            )
    finally:
        close_db()


def _as_legacy_state(local: bool, external: bool) -> ConsentState:
    decision = "allow"
    if not local:
        decision = "deny"
    elif external:
        decision = "allow_external"
    return ConsentState(
        granted=local,
        decision=decision,
        timestamp=datetime.now(timezone.utc).isoformat(),
        source="api",
    )


def export_consent() -> dict[str, Any]:
    state = get_consent()
    return {
        "local_consent": state["local_consent"],
        "external_consent": state["external_consent"],
    }


def ensure_consent(*, require_granted: bool = False) -> ConsentState:
    state = get_consent()
    consent = _as_legacy_state(state["local_consent"], state["external_consent"])
    if require_granted and not consent.granted:
        raise ConsentError("Local consent required.")
    return consent


def prompt_for_consent() -> str:
    # API-first flow does not support interactive terminal prompts.
    return "declined"


def grant_consent(*, decision: str = "allow", source: str = "cli") -> Config:
    set_local_consent(True)
    return update_consent(granted=True, decision=decision, source=source)


def revoke_consent(*, decision: str = "deny", source: str = "cli") -> Config:
    set_local_consent(False)
    return update_consent(granted=False, decision=decision, source=source)


def grant_external_consent(*, decision: str = "allow") -> Config:
    set_external_consent(True)
    config = load_config()
    # Keep existing local consent metadata untouched.
    update_consent(
        granted=config.consent.granted,
        decision=(decision or "allow_external"),
        source=config.consent.source,
    )
    return load_config()


def revoke_external_consent(*, decision: str = "deny") -> Config:
    set_external_consent(False)
    config = load_config()
    update_consent(
        granted=config.consent.granted,
        decision=(decision or "deny_external"),
        source=config.consent.source,
    )
    return load_config()


def show_external_consent_status() -> None:
    state = get_consent()
    print(f"external_consent={state['external_consent']}")
