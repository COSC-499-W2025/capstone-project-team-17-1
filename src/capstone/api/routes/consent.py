import sqlite3
from fastapi import APIRouter, Request
from pydantic import BaseModel
from capstone.activity_log import log_event
from capstone.storage import open_db
from datetime import datetime, timezone
from capstone.api.routes.auth import get_authenticated_username
import capstone.storage as storage_module

router = APIRouter(tags=["consent"])


class ConsentIn(BaseModel):
    consent: bool


def _read_row(conn):
    return conn.execute(
        """
        SELECT local_consent, external_consent
        FROM privacy_consent
        LIMIT 1
        """
    ).fetchone()


def _ensure_row(conn):
    row = _read_row(conn)
    if row:
        return row

    conn.execute(
        """
        INSERT INTO privacy_consent
        (local_consent, external_consent, updated_at)
        VALUES (?, ?, ?)
        """,
        (0, 0, datetime.now(timezone.utc).isoformat())
    )
    conn.commit()
    return _read_row(conn)


def _bind_current_user_from_session(request: Request) -> None:
    username = get_authenticated_username(request)
    storage_module.set_current_user(username)


# ------------------------------------------------
# GET FULL CONSENT STATE
# ------------------------------------------------

@router.get("/privacy-consent")
def get_consent(request: Request):
    _bind_current_user_from_session(request)
    conn = open_db()
    try:
        row = _read_row(conn)
        if not row:
            return {
                "local_consent": False,
                "external_consent": False,
            }

        return {
            "local_consent": bool(row[0]),
            "external_consent": bool(row[1]),
        }
    finally:
        conn.close()


# ------------------------------------------------
# SET LOCAL CONSENT
# ------------------------------------------------

@router.post("/privacy-consent/local")
def set_local_consent(payload: ConsentIn, request: Request):
    _bind_current_user_from_session(request)
    conn = open_db()
    try:
        _ensure_row(conn)

        conn.execute(
            """
            UPDATE privacy_consent
            SET local_consent = ?, updated_at = ?
            """,
            (int(payload.consent), datetime.now(timezone.utc).isoformat())
        )
        conn.commit()

        log_event(
            "INFO" if payload.consent else "WARNING",
            "Local consent granted" if payload.consent else "Local consent revoked"
        )

        return {"local_consent": payload.consent}
    except sqlite3.OperationalError as exc:
        if "locked" in str(exc).lower():
            return {"local_consent": payload.consent, "warning": "database_busy"}
        raise
    finally:
        conn.close()


# ------------------------------------------------
# SET EXTERNAL CONSENT
# ------------------------------------------------

@router.post("/privacy-consent/external")
def set_external_consent(payload: ConsentIn, request: Request):
    _bind_current_user_from_session(request)
    conn = open_db()
    try:
        _ensure_row(conn)

        conn.execute(
            """
            UPDATE privacy_consent
            SET external_consent = ?, updated_at = ?
            """,
            (int(payload.consent), datetime.now(timezone.utc).isoformat())
        )
        conn.commit()

        log_event(
            "INFO" if payload.consent else "WARNING",
            "External AI consent granted" if payload.consent else "External AI consent revoked"
        )

        return {"external_consent": payload.consent}
    except sqlite3.OperationalError as exc:
        if "locked" in str(exc).lower():
            return {"external_consent": payload.consent, "warning": "database_busy"}
        raise
    finally:
        conn.close()
