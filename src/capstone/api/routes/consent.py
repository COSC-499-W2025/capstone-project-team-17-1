from fastapi import APIRouter
from pydantic import BaseModel
from capstone.activity_log import log_event
from capstone.storage import open_db
from datetime import datetime, timezone

router = APIRouter(tags=["consent"])


class ConsentIn(BaseModel):
    consent: bool


def _ensure_row(conn):
    row = conn.execute(
        "SELECT COUNT(*) FROM privacy_consent"
    ).fetchone()

    if row[0] == 0:
        conn.execute(
            """
            INSERT INTO privacy_consent
            (local_consent, external_consent, updated_at)
            VALUES (?, ?, ?)
            """,
            (0, 0, datetime.now(timezone.utc).isoformat())
        )
        conn.commit()


# ------------------------------------------------
# GET FULL CONSENT STATE
# ------------------------------------------------

@router.get("/privacy-consent")
def get_consent():
    conn = open_db()
    _ensure_row(conn)

    row = conn.execute(
        """
        SELECT local_consent, external_consent
        FROM privacy_consent
        LIMIT 1
        """
    ).fetchone()

    return {
        "local_consent": bool(row[0]),
        "external_consent": bool(row[1]),
    }


# ------------------------------------------------
# SET LOCAL CONSENT
# ------------------------------------------------

@router.post("/privacy-consent/local")
def set_local_consent(payload: ConsentIn):
    conn = open_db()
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


# ------------------------------------------------
# SET EXTERNAL CONSENT
# ------------------------------------------------

@router.post("/privacy-consent/external")
def set_external_consent(payload: ConsentIn):
    conn = open_db()
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