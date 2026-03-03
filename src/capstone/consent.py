"""
Consent utilities for API driven architecture.
No CLI prompts. No interactive terminal input.
Frontend controls consent state.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from capstone.storage import open_db, close_db


class ConsentError(RuntimeError):
    """Raised when local consent is missing."""


class ExternalPermissionDenied(RuntimeError):
    """Raised when external AI usage is not allowed."""


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